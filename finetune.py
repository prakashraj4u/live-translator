"""
Corrections se model ko fine-tune karo (LoRA). Tumhari 'Sudhaaro' wali corrections ka data use hota hai.
  pip install -r requirements-train.txt
  python finetune.py            (GPU ho to tez; CPU par bahut dheema)
Pehli baar base model (~2.4GB) internet se download hota hai.
Khatam hone par naya model apne aap models/nllb me lag jata hai (purana models/nllb-backup me).
"""
import os, shutil, sqlite3, subprocess
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer, DataCollatorForSeq2Seq,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

from langs import LANGS

ROOT = Path(__file__).parent
MODELS = ROOT / "models"
BASE = "facebook/nllb-200-distilled-600M"

rows = sqlite3.connect(ROOT / "data" / "memory.db").execute(
    "SELECT src,dst,text,translation FROM tm WHERE verified=1").fetchall()
print("Verified corrections:", len(rows))
if len(rows) < 20:
    raise SystemExit("Kam se kam 20 corrections chahiye. App me galat translations sudhaarte raho.")

tok = AutoTokenizer.from_pretrained(BASE)
feats = []
for s, d, text, tr in rows:
    tok.src_lang, tok.tgt_lang = LANGS[s]["nllb"], LANGS[d]["nllb"]
    feats.append(tok(text, text_target=tr, truncation=True, max_length=128))
ds = Dataset.from_list(feats)

model = AutoModelForSeq2SeqLM.from_pretrained(BASE)
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05,
                                         target_modules=["q_proj", "v_proj"], task_type="SEQ_2_SEQ_LM"))
args = Seq2SeqTrainingArguments(output_dir=str(ROOT / "data" / "ft-run"), per_device_train_batch_size=8,
                                num_train_epochs=3, learning_rate=1e-4, logging_steps=5,
                                save_strategy="no", report_to=[], fp16=torch.cuda.is_available())
Seq2SeqTrainer(model=model, args=args, train_dataset=ds,
               data_collator=DataCollatorForSeq2Seq(tok, model=model)).train()

merged = model.merge_and_unload()
ft_dir = MODELS / "nllb-ft"
merged.save_pretrained(ft_dir); tok.save_pretrained(ft_dir)

new_dir = MODELS / "nllb-new"
shutil.rmtree(new_dir, ignore_errors=True)
subprocess.run(["ct2-transformers-converter", "--model", str(ft_dir), "--output_dir", str(new_dir),
                "--quantization", "int8"], check=True)
shutil.rmtree(MODELS / "nllb-backup", ignore_errors=True)
os.rename(MODELS / "nllb", MODELS / "nllb-backup")
os.rename(new_dir, MODELS / "nllb")
print("Done. App restart karo, naya model use hoga. Gadbad lage to models/nllb-backup ko wapas models/nllb bana do.")
