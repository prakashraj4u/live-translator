"""
Live Interpreter Agent - OFFLINE backend
Sunna  : faster-whisper   (local)
Translate: NLLB-200 + CTranslate2 (local)
Bolna  : MMS-TTS voices   (local)
Koi API key ya internet nahi chahiye (sirf pehli baar download_models.py ke liye).
"""
import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import base64
import io
import re
import sqlite3
import threading
import time
import wave
from collections import defaultdict, deque
from pathlib import Path

import ctranslate2
import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel
from transformers import AutoTokenizer, VitsModel

from langs import LANGS

ROOT = Path(__file__).parent
MODELS = ROOT / "models"
torch.set_num_threads(os.cpu_count() or 4)
# CPU default (sabse safe). NVIDIA CUDA libraries install ho to environment variable DEVICE=cuda set karo.
DEVICE = os.getenv("DEVICE", "cpu")
STT_BEAM = int(os.getenv("STT_BEAM", "1"))   # 1 = tez, 5 = zyada accurate
MT_BEAM = int(os.getenv("MT_BEAM", "2"))     # 2 = tez, 5 = zyada accurate

for need in ("whisper", "nllb", "nllb-tokenizer"):
    if not (MODELS / need).exists():
        raise SystemExit("Models nahi mile. Pehle chalao:  python download_models.py")

print("Models load ho rahe hai (pehli baar 10-20 sec lagte hai)...")
stt = WhisperModel(str(MODELS / "whisper"), device=DEVICE, compute_type="int8")
mt = ctranslate2.Translator(str(MODELS / "nllb"), device=DEVICE, compute_type="int8")
mt_tok = AutoTokenizer.from_pretrained(str(MODELS / "nllb-tokenizer"))
mt_lock = threading.Lock()

INSTALLED = {c: v for c, v in LANGS.items() if (MODELS / "tts" / v["mms"] / "config.json").exists()}
print("Available languages:", ", ".join(v["name"] for v in INSTALLED.values()) or "koi nahi")

_tts = {}          # lang -> (model, tokenizer)
_turn_audio = {}   # lang -> "Your turn" ka audio (cache)


def read_wav(data: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(data)) as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def to_wav(samples: np.ndarray, sr: int) -> bytes:
    pcm = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def transcribe(samples: np.ndarray, lang: str) -> str:
    code = LANGS[lang]["whisper"]
    if not code:
        raise HTTPException(400, f"{LANGS[lang]['name']} bolne wale ko sunna abhi supported nahi hai.")
    segs, _ = stt.transcribe(
        samples, language=code, beam_size=STT_BEAM, vad_filter=True, condition_on_previous_text=False
    )
    return " ".join(s.text.strip() for s in segs if s.no_speech_prob < 0.6).strip()


def translate(text: str, src: str, dst: str) -> str:
    with mt_lock:
        mt_tok.src_lang = LANGS[src]["nllb"]
        tokens = mt_tok.convert_ids_to_tokens(mt_tok.encode(text))
        res = mt.translate_batch(
            [tokens], target_prefix=[[LANGS[dst]["nllb"]]], beam_size=MT_BEAM, max_decoding_length=256
        )
        out = res[0].hypotheses[0]
        return mt_tok.decode(mt_tok.convert_tokens_to_ids(out), skip_special_tokens=True).strip()


def synth(text: str, lang: str):
    if lang not in _tts:
        path = MODELS / "tts" / LANGS[lang]["mms"]
        if not (path / "config.json").exists():
            raise HTTPException(503, f"{LANGS[lang]['name']} ki voice download nahi hui. download_models.py chalao.")
        _tts[lang] = (VitsModel.from_pretrained(str(path)).eval(), AutoTokenizer.from_pretrained(str(path)))
    model, tok = _tts[lang]
    inputs = tok(text, return_tensors="pt")
    if inputs["input_ids"].shape[1] == 0:
        return np.zeros(1, dtype=np.float32), model.config.sampling_rate
    with torch.no_grad():
        wav = model(**inputs).waveform[0].numpy()
    return wav, model.config.sampling_rate


def speak(text: str, lang: str) -> bytes:
    wav, sr = synth(text, lang)
    if lang not in _turn_audio:
        _turn_audio[lang] = synth(LANGS[lang]["turn"], lang)[0]
    gap = np.zeros(int(sr * 0.35), dtype=np.float32)
    return to_wav(np.concatenate([wav, gap, _turn_audio[lang]]), sr)


# ---------- Learning layer: translation memory (seekhta hai, turant yaad rakhta hai) ----------
DB_PATH = ROOT / "data" / "memory.db"
DB_PATH.parent.mkdir(exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db_lock = threading.Lock()
db.execute("""CREATE TABLE IF NOT EXISTS tm(src TEXT, dst TEXT, key TEXT, text TEXT, translation TEXT,
              verified INTEGER DEFAULT 0, uses INTEGER DEFAULT 1, PRIMARY KEY(src, dst, key))""")
db.commit()


def _key(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[.,!?;:।'\"“”‘’()\-]+", " ", t.lower())).strip()


def tm_get(src, dst, text):
    with db_lock:
        r = db.execute("SELECT translation FROM tm WHERE src=? AND dst=? AND key=?", (src, dst, _key(text))).fetchone()
        if r:
            db.execute("UPDATE tm SET uses=uses+1 WHERE src=? AND dst=? AND key=?", (src, dst, _key(text)))
            db.commit()
    return r[0] if r else None


def tm_put(src, dst, text, tr, verified):
    with db_lock:
        db.execute(
            """INSERT INTO tm(src,dst,key,text,translation,verified) VALUES(?,?,?,?,?,?)
               ON CONFLICT(src,dst,key) DO UPDATE SET translation=excluded.translation,
               text=excluded.text, verified=excluded.verified WHERE excluded.verified=1""",
            (src, dst, _key(text), text, tr, verified),
        )
        db.commit()


app = FastAPI(title="Live Interpreter (offline)")


@app.exception_handler(Exception)
async def show_errors(request, exc):
    """Asli error browser me dikhao (aur terminal me poora traceback)."""
    import traceback
    from fastapi.responses import JSONResponse
    traceback.print_exception(exc)
    last = traceback.extract_tb(exc.__traceback__)[-1]
    where = f"{os.path.basename(last.filename)}:{last.lineno}"
    return JSONResponse({"detail": f"{type(exc).__name__}: {str(exc)[:300]} [{where}]"}, status_code=500)
memory = defaultdict(lambda: deque(maxlen=6))  # session ka record


@app.get("/api/languages")
def languages():
    return [{"code": c, "name": v["name"]} for c, v in INSTALLED.items()]


@app.post("/api/turn")
def turn(
    audio: UploadFile = File(...),
    src: str = Form(...),
    dst: str = Form(...),
    session: str = Form(...),
):
    if src not in INSTALLED or dst not in INSTALLED:
        raise HTTPException(400, "Ye language install nahi hai")
    t0 = time.time()
    text = transcribe(read_wav(audio.file.read()), src)
    t1 = time.time()
    if not text:
        return {"transcript": "", "translation": "", "audio": None}
    tr = tm_get(src, dst, text)           # pehle yaad kiye hue translations me dekho (instant)
    cached = tr is not None
    if not cached:
        tr = translate(text, src, dst)
        tm_put(src, dst, text, tr, 0)
    t2 = time.time()
    wav = speak(tr, dst)
    t3 = time.time()
    memory[session].append((text, tr))
    print(f"sunna {t1-t0:.1f}s | translate {t2-t1:.1f}s | bolna {t3-t2:.1f}s | total {t3-t0:.1f}s")
    return {
        "transcript": text,
        "translation": tr,
        "audio": base64.b64encode(wav).decode(),
        "mime": "audio/wav",
        "engine": "memory" if cached else "offline",
    }


@app.post("/api/reset")
def reset(session: str = Form(...)):
    memory.pop(session, None)
    return {"ok": True}


@app.post("/api/correct")
def correct(src: str = Form(...), dst: str = Form(...), text: str = Form(...), translation: str = Form(...)):
    """User ne sahi translation bataya: ab ye hamesha yehi use hoga, aur fine-tuning ke data me jayega."""
    tm_put(src, dst, text, translation.strip(), 1)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
