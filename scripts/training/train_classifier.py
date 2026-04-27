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
import re
from collections import Counter

import torch
import torch.nn as nn
from datasets import Dataset
from sklearn.metrics import classification_report, balanced_accuracy_score
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    PreTrainedTokenizerBase,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)

_URL_RE        = re.compile(r'https?://\S+|www\.\S+', re.I)
_URGENCY_RE    = re.compile(
    r'\b(urgent|immediately|action required|verify now|account suspended|'
    r'limited time|expires|deadline|act now|confirm now|respond now|'
    r'within 24|within 48|your account will)\b', re.I)
_CREDENTIAL_RE = re.compile(
    r'\b(password|social security|ssn|bank account|credit card|debit card|'
    r'pin number|verify your|confirm your|update your (account|info|details)|'
    r'login|sign in to confirm)\b', re.I)
_MONEY_RE      = re.compile(
    r'\$[\d,]+|\b\d[\d,]*\s*(dollars?|million|thousand|hundred)\b|'
    r'\b(prize|reward|lottery|inheritance|winnings)\b', re.I)


def _feature_prefix(subject: str, body: str) -> str:
    text = subject + " " + body[:1000]
    flags: list[str] = []
    url_count = len(_URL_RE.findall(text))
    if url_count:
        flags.append(f"URLS:{url_count}")
    if _URGENCY_RE.search(text):
        flags.append("URGENT")
    if _CREDENTIAL_RE.search(text):
        flags.append("CREDENTIALS")
    if _MONEY_RE.search(text):
        flags.append("MONEY")
    caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
    if caps_ratio > 0.4:
        flags.append("CAPS")
    return f"[{' '.join(flags)}] " if flags else "[CLEAN] "

SCAM_LABELS = [
    "not_scam",
    "phishing",
    "spam",
    "romance_scam",
    "package_delivery",
    "tech_support",
    "bank_fraud",
    "lottery_prize",
    "elder_targeted",   # IRS, SSA, Medicare, grandparent/family emergency
]
LABEL2ID = {l: i for i, l in enumerate(SCAM_LABELS)}
ID2LABEL = {i: l for i, l in enumerate(SCAM_LABELS)}
BASE_MODEL = "distilbert-base-uncased"


def load_jsonl(path: str) -> list[dict[str, str]]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def make_dataset(records: list[dict[str, str]], tokenizer: PreTrainedTokenizerBase) -> Dataset:
    texts = [
        _feature_prefix(r.get("subject", ""), r.get("body", ""))
        + f"{r.get('subject', '')} [SEP] {r.get('body', '')[:2048]}"
        for r in records
    ]
    labels = [LABEL2ID.get(r.get("scam_type", "not_scam"), LABEL2ID["not_scam"]) for r in records]
    enc = tokenizer(texts, truncation=True, max_length=512)
    enc["labels"] = labels
    return Dataset.from_dict(enc)


_MAX_CLASS_WEIGHT = 10.0


def compute_class_weights(records: list[dict], device) -> torch.Tensor:
    counts = Counter(
        LABEL2ID.get(r.get("scam_type", "not_scam"), LABEL2ID["not_scam"])
        for r in records
    )
    total = sum(counts.values())
    n_classes = len(SCAM_LABELS)
    weights = torch.tensor(
        [min(total / (n_classes * max(counts.get(i, 1), 1)), _MAX_CLASS_WEIGHT)
         for i in range(n_classes)],
        dtype=torch.float,
        device=device,
    )
    return weights


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = logits.argmax(-1)
    report = classification_report(
        labels, preds,
        labels=list(range(len(SCAM_LABELS))),
        target_names=SCAM_LABELS,
        output_dict=True,
        zero_division=0,
    )
    return {
        "balanced_accuracy": balanced_accuracy_score(labels, preds),
        "macro_f1": report["macro avg"]["f1-score"],
    }


class WeightedTrainer(Trainer):
    def __init__(self, class_weights, **kwargs):
        super().__init__(**kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss = nn.CrossEntropyLoss(weight=self.class_weights)(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


def train(args):
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA not available. Verify your PyTorch installation: "
            "run `python -c 'import torch; print(torch.cuda.is_available())'`"
        )
    device = torch.device("cuda")
    print(f"Training on: {torch.cuda.get_device_name(0)}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(SCAM_LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    ).to(device)

    train_records = load_jsonl(args.train)
    val_records = load_jsonl(args.val)
    train_ds = make_dataset(train_records, tokenizer)
    val_ds = make_dataset(val_records, tokenizer)

    class_weights = compute_class_weights(train_records, device)
    print("Class weights:")
    for label, w in zip(SCAM_LABELS, class_weights.tolist()):
        print(f"  {label:<20} {w:.3f}")

    training_args = TrainingArguments(
        output_dir=args.out,
        num_train_epochs=10,
        per_device_train_batch_size=20,
        per_device_eval_batch_size=64,
        warmup_steps=200,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = WeightedTrainer(
        class_weights=class_weights,
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(args.out)
    print(f"\nModel saved → {args.out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="data/processed/train.jsonl")
    parser.add_argument("--val", default="data/processed/val.jsonl")
    parser.add_argument("--out", default="models/distilbert-scam")
    args = parser.parse_args()
    train(args)
