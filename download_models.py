"""
Ek baar chalao (internet chahiye). Uske baad app poori tarah offline chalegi.

  python download_models.py                       -> sab languages
  python download_models.py --langs hi,en,ta,te   -> sirf chuni hui languages (kam space)
  python download_models.py --whisper base        -> tez par kam accurate sunna
  python download_models.py --whisper medium      -> dheere par zyada accurate sunna
"""
import argparse
from pathlib import Path

from langs import LANGS

ROOT = Path(__file__).parent / "models"

ap = argparse.ArgumentParser()
ap.add_argument("--langs", default="all")
ap.add_argument("--whisper", default="small", help="tiny | base | small | medium")
ap.add_argument("--nllb", default="600m", help="600m (tez) | 1.3b (zyada accurate, 2x dheema)")
args = ap.parse_args()

codes = list(LANGS) if args.langs == "all" else [c.strip() for c in args.langs.split(",")]
bad = [c for c in codes if c not in LANGS]
if bad:
    raise SystemExit(f"Ye language codes galat hai: {bad}. Sahi codes: {list(LANGS)}")

# 1) Sunne wala model (Whisper)
print(f"\n[1/3] Whisper '{args.whisper}' download ho raha hai...")
from faster_whisper.utils import download_model
download_model(args.whisper, output_dir=str(ROOT / "whisper"))

# 2) Translation model (NLLB-200, sabhi bhashaon ke liye ek hi model)
print("\n[2/3] Translation model (NLLB, ~600MB) download ho raha hai...")
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
import shutil
repo = {"600m": "JustFrederik/nllb-200-distilled-600M-ct2-int8",
        "1.3b": "JustFrederik/nllb-200-distilled-1.3B-ct2-int8"}[args.nllb]
shutil.rmtree(ROOT / "nllb", ignore_errors=True)
snapshot_download(repo, local_dir=str(ROOT / "nllb"))
AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M").save_pretrained(str(ROOT / "nllb-tokenizer"))

# 3) Bolne wali voices (MMS-TTS, har bhasha ki alag)
print("\n[3/3] Voices download ho rahi hai...")
from transformers import VitsModel
failed = []
for c in codes:
    mid = LANGS[c]["mms"]
    out = ROOT / "tts" / mid
    if (out / "config.json").exists():
        print(f"  {LANGS[c]['name']}: pehle se hai")
        continue
    try:
        print(f"  {LANGS[c]['name']} voice...")
        VitsModel.from_pretrained(f"facebook/mms-tts-{mid}").save_pretrained(str(out))
        AutoTokenizer.from_pretrained(f"facebook/mms-tts-{mid}").save_pretrained(str(out))
    except Exception as e:
        failed.append(c)
        print(f"  {LANGS[c]['name']} FAIL: {str(e)[:100]}")

print("\nDone.")
if failed:
    print("In languages ki voice download nahi hui:", failed)
print("Ab chalao: python app.py  (ab internet ki zarurat nahi)")
