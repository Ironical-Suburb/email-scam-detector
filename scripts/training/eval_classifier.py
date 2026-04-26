"""
Evaluates a fine-tuned classifier on the held-out test set.

Usage:
    python scripts/training/eval_classifier.py \
        --model models/distilbert-scam \
        --test  data/processed/test.jsonl
"""

import argparse
import json

import torch
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, DataCollatorWithPadding

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


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def make_dataset(records: list[dict], tokenizer) -> Dataset:
    texts = [
        f"{r.get('subject', '')} [SEP] {r.get('body', '')[:2048]}"
        for r in records
    ]
    labels = [LABEL2ID.get(r.get("scam_type", "not_scam"), LABEL2ID["not_scam"]) for r in records]
    enc = tokenizer(texts, truncation=True, max_length=512)
    enc["labels"] = labels
    return Dataset.from_dict(enc)


def evaluate(args):
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model)

    records = load_jsonl(args.test)
    print(f"Loaded {len(records)} test records")

    test_ds = make_dataset(records, tokenizer)

    trainer = Trainer(
        model=model,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
    )

    output = trainer.predict(test_ds)
    preds = output.predictions.argmax(-1)
    labels = output.label_ids

    print("\n── Classification Report ─────────────────────────────────────")
    print(classification_report(
        labels, preds,
        labels=list(range(len(SCAM_LABELS))),
        target_names=SCAM_LABELS,
        zero_division=0,
    ))

    print("── Confusion Matrix ──────────────────────────────────────────")
    cm = confusion_matrix(labels, preds, labels=list(range(len(SCAM_LABELS))))
    header = f"{'':20s}" + "".join(f"{l[:6]:>8}" for l in SCAM_LABELS)
    print(header)
    for i, row in enumerate(cm):
        print(f"{SCAM_LABELS[i]:20s}" + "".join(f"{v:>8}" for v in row))

    correct = (preds == labels).sum()
    print(f"\nOverall accuracy: {correct}/{len(labels)} = {correct/len(labels):.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/distilbert-scam")
    parser.add_argument("--test",  default="data/processed/test.jsonl")
    args = parser.parse_args()
    evaluate(args)
