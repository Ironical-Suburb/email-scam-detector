"""
Fine-tunes DistilBERT on the scam email dataset.

Usage:
    python scripts/training/train_classifier.py \
        --train data/processed/train.jsonl \
        --val data/processed/val.jsonl \
        --out models/distilbert-scam

Requirements: transformers, torch, scikit-learn, datasets
"""

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from sklearn.metrics import classification_report
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)

SCAM_LABELS = [
    "irs_impersonation",
    "tech_support",
    "lottery_prize",
    "bank_fraud",
    "romance_scam",
    "package_delivery",
    "grandparent_scam",
    "not_scam",
]
LABEL2ID = {l: i for i, l in enumerate(SCAM_LABELS)}
ID2LABEL = {i: l for i, l in enumerate(SCAM_LABELS)}
BASE_MODEL = "distilbert-base-uncased"


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def make_dataset(records: list[dict], tokenizer) -> Dataset:
    texts = [r.get("body", "")[:512] for r in records]
    labels = [LABEL2ID.get(r.get("scam_type", "not_scam"), LABEL2ID["not_scam"]) for r in records]
    enc = tokenizer(texts, truncation=True, max_length=512)
    enc["labels"] = labels
    return Dataset.from_dict(enc)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = logits.argmax(-1)
    report = classification_report(
        labels, preds, target_names=SCAM_LABELS, output_dict=True, zero_division=0
    )
    return {
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
    }


def train(args):
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(SCAM_LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    train_records = load_jsonl(args.train)
    val_records = load_jsonl(args.val)
    train_ds = make_dataset(train_records, tokenizer)
    val_ds = make_dataset(val_records, tokenizer)

    training_args = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=4,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        warmup_steps=200,
        weight_decay=0.01,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"\nModel saved → {args.out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="data/processed/train.jsonl")
    parser.add_argument("--val", default="data/processed/val.jsonl")
    parser.add_argument("--out", default="models/distilbert-scam")
    args = parser.parse_args()
    train(args)
