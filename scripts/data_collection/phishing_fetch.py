"""
Fetches phishing / scam email datasets from HuggingFace and maps them to
the project's 7 scam categories.

Sources pulled:
  1. zefang-liu/phishing-email-dataset  — real phishing emails, multi-label
  2. ealvaradob/phishing-dataset         — phishing URLs + email text
  3. TrainingDataPro/phishing-email-text — raw phishing email bodies

All output goes to a single JSONL file in the same format as enron_loader.py
so prepare_dataset.py can merge them without changes.

Usage:
    python scripts/data_collection/phishing_fetch.py --out data/raw/phishing.jsonl
"""

import argparse
import json
import re
from pathlib import Path

from datasets import load_dataset


# ── Category keyword classifier ───────────────────────────────────────────────
# Assigns one of our 7 scam_type labels based on subject + body keywords.
# Used when the source dataset has no sub-category labels.

_CATEGORY_PATTERNS = [
    ("irs_impersonation",  re.compile(
        r"\b(irs|internal revenue|tax refund|tax return|w-2|1099|taxpayer)\b", re.I)),
    ("tech_support",       re.compile(
        r"\b(microsoft|apple|google|mcafee|norton|virus|malware|tech support|"
        r"helpdesk|your (computer|device|pc) (is|has been))\b", re.I)),
    ("lottery_prize",      re.compile(
        r"\b(lottery|lotto|prize|winner|won|jackpot|sweepstakes|nigerian|"
        r"inheritance|million dollar)\b", re.I)),
    ("bank_fraud",         re.compile(
        r"\b(bank|account (suspend|verif|block)|paypal|credit card|"
        r"debit card|billing|invoice|payment (fail|declin))\b", re.I)),
    ("romance_scam",       re.compile(
        r"\b(lonely|soulmate|dating|match|profile|attractive|love|"
        r"relationship|meet (you|me))\b", re.I)),
    ("package_delivery",   re.compile(
        r"\b(fedex|ups|usps|dhl|parcel|package|delivery|tracking|shipment|"
        r"customs fee)\b", re.I)),
    ("grandparent_scam",   re.compile(
        r"\b(grandson|granddaughter|grandchild|arrested|bail|emergency|"
        r"in trouble|do not tell)\b", re.I)),
]


def classify_text(subject: str, body: str) -> str:
    text = f"{subject} {body[:500]}"
    for label, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return label
    return "phishing"  # generic fallback — still gets embedded as a scam signal


# ── Individual dataset loaders ────────────────────────────────────────────────

def _write(record: dict, out_f) -> None:
    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")


def fetch_zefang(out_f, limit: int) -> int:
    print("Fetching zefang-liu/phishing-email-dataset ...")
    try:
        ds = load_dataset("zefang-liu/phishing-email-dataset", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped (could not load): {e}")
        return 0

    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("Email Text", row.get("body", row.get("text", "")))).strip()
        subject = str(row.get("subject", "")).strip()
        if len(body) < 30:
            continue
        scam_type = classify_text(subject, body)
        _write({
            "subject": subject,
            "from": "",
            "body": body[:4000],
            "label": "phishing",
            "scam_type": scam_type,
            "source": "zefang_phishing",
        }, out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_training_data_pro(out_f, limit: int) -> int:
    print("Fetching TrainingDataPro/phishing-email-text ...")
    try:
        ds = load_dataset("TrainingDataPro/phishing-email-text", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped (could not load): {e}")
        return 0

    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("text", row.get("body", row.get("email_text", "")))).strip()
        subject = str(row.get("subject", "")).strip()
        if len(body) < 30:
            continue
        scam_type = classify_text(subject, body)
        _write({
            "subject": subject,
            "from": "",
            "body": body[:4000],
            "label": "phishing",
            "scam_type": scam_type,
            "source": "training_data_pro",
        }, out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_generic_phishing(out_f, limit: int) -> int:
    """
    Fallback: tries several other known HuggingFace phishing datasets.
    Stops at the first one that loads successfully.
    """
    candidates = [
        ("sms_spam", "sms_spam", "sms", "label"),
        ("dima806/fraudulent-emails", None, "body", None),
        ("JohnSnowLabs/phishing-email", None, "text", None),
    ]
    for dataset_id, config, text_col, label_col in candidates:
        try:
            print(f"Trying {dataset_id} ...")
            kwargs = {"trust_remote_code": True, "split": "train"}
            if config:
                ds = load_dataset(dataset_id, config, **kwargs)
            else:
                ds = load_dataset(dataset_id, **kwargs)

            count = 0
            for row in ds:
                if count >= limit:
                    break
                body = str(row.get(text_col, "")).strip()
                if len(body) < 30:
                    continue
                raw_label = row.get(label_col, 1) if label_col else 1
                if str(raw_label) in ("0", "ham", "legitimate"):
                    continue  # skip legitimate entries from this source
                scam_type = classify_text("", body)
                _write({
                    "subject": "",
                    "from": "",
                    "body": body[:4000],
                    "label": "phishing",
                    "scam_type": scam_type,
                    "source": dataset_id.replace("/", "_"),
                }, out_f)
                count += 1
            print(f"  {count} records from {dataset_id}")
            return count
        except Exception as e:
            print(f"  Skipped {dataset_id}: {e}")

    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/raw/phishing.jsonl")
    parser.add_argument("--limit", type=int, default=5_000,
                        help="Max records per source dataset")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        total += fetch_zefang(f, args.limit)
        total += fetch_training_data_pro(f, args.limit)
        if total < 500:
            total += fetch_generic_phishing(f, args.limit)

    print(f"\nTotal phishing records saved: {total} -> {out_path}")
    if total == 0:
        print("No data was fetched. Check your internet connection or HuggingFace availability.")
