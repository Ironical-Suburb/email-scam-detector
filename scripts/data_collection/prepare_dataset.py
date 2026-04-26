"""
Merges raw JSONL sources, auto-labels scam category with zero-shot GPT-4,
and splits into train/val/test sets.

Usage:
    python scripts/data_collection/prepare_dataset.py \
        --inputs data/raw/phishtank.jsonl data/raw/enron_spam.jsonl \
        --out-dir data/processed \
        --label-with-gpt   # optional: uses GPT-4 to assign scam subcategory
"""

import argparse
import json
import random
from pathlib import Path


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


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def gpt4_label(record: dict, client) -> str:
    body = record.get("body", "")[:1000]
    subject = record.get("subject", "")
    prompt = (
        f"Classify this email into exactly one of: {', '.join(SCAM_LABELS)}.\n"
        f"Subject: {subject}\nBody: {body}\n"
        "Respond with only the label, nothing else."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0,
    )
    label = resp.choices[0].message.content.strip().lower().replace(" ", "_")
    return label if label in SCAM_LABELS else "not_scam"


def split(records: list, train=0.80, val=0.10):
    random.shuffle(records)
    n = len(records)
    t = int(n * train)
    v = int(n * val)
    return records[:t], records[t : t + v], records[t + v :]


def save_jsonl(records: list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"  {len(records):>6} records -> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", default=["data/raw/phishtank.jsonl"])
    parser.add_argument("--out-dir", default="data/processed")
    parser.add_argument("--label-with-gpt", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    all_records = []
    for p in args.inputs:
        records = load_jsonl(Path(p))
        print(f"Loaded {len(records)} records from {p}")
        all_records.extend(records)

    if args.label_with_gpt:
        try:
            from openai import OpenAI
            client = OpenAI()
            print("Auto-labeling with GPT-4o-mini ...")
            for i, r in enumerate(all_records):
                if r.get("label") in (None, "phishing", "spam"):
                    r["scam_type"] = gpt4_label(r, client)
                else:
                    r["scam_type"] = r.get("label", "not_scam")
                if i % 100 == 0:
                    print(f"  {i}/{len(all_records)}")
        except ImportError:
            print("openai package not installed — skipping GPT labeling")
    else:
        for r in all_records:
            r.setdefault("scam_type", r.get("label", "not_scam"))

    train, val, test = split(all_records)
    out = Path(args.out_dir)
    print(f"\nSplit: {len(train)} train / {len(val)} val / {len(test)} test")
    save_jsonl(train, out / "train.jsonl")
    save_jsonl(val, out / "val.jsonl")
    save_jsonl(test, out / "test.jsonl")
