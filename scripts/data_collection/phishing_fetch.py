"""
Fetches phishing / scam email datasets from HuggingFace and maps them to
the project's scam categories.

Sources pulled:
  1. zefang-liu/phishing-email-dataset
  2. TrainingDataPro/phishing-email-text
  3. puyang2025/seven-phishing-email-datasets  (7 public corpora combined)
  4. redasers/difraud                          (15k manually labeled phishing)
  5. FredZhang7/all-scam-spam                 (42k multilingual scam messages)

Usage:
    python scripts/data_collection/phishing_fetch.py --out data/raw/phishing.jsonl
"""

import argparse
import json
import re
from pathlib import Path

from datasets import load_dataset


# ── Category keyword classifier ───────────────────────────────────────────────
# elder_targeted is checked FIRST so IRS/SSA/grandparent emails don't fall
# through to bank_fraud or other catch-all patterns.

_CATEGORY_PATTERNS = [
    ("elder_targeted", re.compile(
        r"\b(irs|internal revenue|tax refund|tax return|w-2|1099|taxpayer|"
        r"social security|ssa|medicare|medicaid|pension|retirement benefit|"
        r"grandson|granddaughter|grandchild|grandparent|"
        r"arrested|bail|in trouble|do not tell|"
        r"government (benefit|check|payment|grant)|"
        r"your (social|medicare|medicaid|pension|retirement) (number|benefit|card))\b",
        re.I,
    )),
    ("tech_support", re.compile(
        r"\b(microsoft|apple|google|mcafee|norton|virus|malware|tech support|"
        r"helpdesk|your (computer|device|pc) (is|has been))\b", re.I,
    )),
    ("lottery_prize", re.compile(
        r"\b(lottery|lotto|prize|winner|won|jackpot|sweepstakes|nigerian|"
        r"inheritance|million dollar)\b", re.I,
    )),
    ("bank_fraud", re.compile(
        r"\b(bank|account (suspend|verif|block)|paypal|credit card|"
        r"debit card|billing|invoice|payment (fail|declin))\b", re.I,
    )),
    ("romance_scam", re.compile(
        r"\b(lonely|soulmate|dating|match\.com|profile|attractive|"
        r"relationship|meet (you|me))\b", re.I,
    )),
    ("package_delivery", re.compile(
        r"\b(fedex|ups|usps|dhl|parcel|package|delivery|tracking|shipment|"
        r"customs fee)\b", re.I,
    )),
]


def classify_text(subject: str, body: str) -> str:
    text = f"{subject} {body[:500]}"
    for label, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return label
    return "phishing"


# ── Shared writer ─────────────────────────────────────────────────────────────

def _write(record: dict, out_f) -> None:
    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _make_record(subject: str, body: str, label: str, source: str) -> dict:
    scam_type = "not_scam" if label == "not_scam" else classify_text(subject, body)
    return {
        "subject": subject,
        "from": "",
        "body": body[:4000],
        "label": label,
        "scam_type": scam_type,
        "source": source,
    }


def _is_legit(raw_label) -> bool:
    return str(raw_label) in ("0", "ham", "legitimate", "benign", "truthful", "safe", "False", "false")


# ── Dataset loaders ───────────────────────────────────────────────────────────

def fetch_zefang(out_f, limit: int) -> int:
    print("Fetching zefang-liu/phishing-email-dataset ...")
    try:
        ds = load_dataset("zefang-liu/phishing-email-dataset", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped: {e}")
        return 0
    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("Email Text", row.get("body", row.get("text", "")))).strip()
        subject = str(row.get("subject", "")).strip()
        if len(body) < 30:
            continue
        _write(_make_record(subject, body, "phishing", "zefang_phishing"), out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_training_data_pro(out_f, limit: int) -> int:
    print("Fetching TrainingDataPro/phishing-email-text ...")
    try:
        ds = load_dataset("TrainingDataPro/phishing-email-text", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped: {e}")
        return 0
    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("text", row.get("body", row.get("email_text", "")))).strip()
        subject = str(row.get("subject", "")).strip()
        if len(body) < 30:
            continue
        _write(_make_record(subject, body, "phishing", "training_data_pro"), out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_seven_phishing(out_f, limit: int) -> int:
    """Seven public corpora combined: TREC, CEAS-08, SpamAssassin, Enron, Ling-Spam."""
    print("Fetching puyang2025/seven-phishing-email-datasets ...")
    try:
        ds = load_dataset("puyang2025/seven-phishing-email-datasets", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped: {e}")
        return 0
    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("text", row.get("body", row.get("email", "")))).strip()
        subject = str(row.get("subject", "")).strip()
        if len(body) < 30:
            continue
        raw_label = row.get("label", row.get("Label", 1))
        label = "not_scam" if _is_legit(raw_label) else "phishing"
        _write(_make_record(subject, body, label, "seven_phishing"), out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_difraud(out_f, limit: int) -> int:
    """DIFrauD benchmark — phishing/email domain only, 15k manually labeled."""
    print("Fetching redasers/difraud ...")
    try:
        ds = load_dataset("redasers/difraud", split="train", trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped: {e}")
        return 0
    count = 0
    for row in ds:
        if count >= limit:
            break
        domain = str(row.get("domain", row.get("Domain", ""))).lower()
        if domain and "phish" not in domain and "email" not in domain and domain != "":
            continue
        body = str(row.get("text", row.get("content", row.get("body", "")))).strip()
        if len(body) < 30:
            continue
        raw_label = row.get("label", row.get("Label", 1))
        label = "not_scam" if _is_legit(raw_label) else "phishing"
        _write(_make_record("", body, label, "difraud"), out_f)
        count += 1
    print(f"  {count} records")
    return count


def fetch_all_scam_spam(out_f, limit: int) -> int:
    """FredZhang7/all-scam-spam — 42k multilingual scam/spam messages."""
    print("Fetching FredZhang7/all-scam-spam ...")
    try:
        ds = load_dataset("FredZhang7/all-scam-spam", split="train",
                          trust_remote_code=False)
    except Exception as e:
        print(f"  Skipped: {e}")
        return 0
    count = 0
    for row in ds:
        if count >= limit:
            break
        body = str(row.get("text", row.get("message", row.get("body", "")))).strip()
        if len(body) < 30:
            continue
        is_spam = row.get("is_spam", row.get("label", 1))
        if _is_legit(is_spam):
            continue  # this source is scam-only; skip the rare legit rows
        _write(_make_record("", body, "spam", "all_scam_spam"), out_f)
        count += 1
    print(f"  {count} records")
    return count


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/raw/phishing.jsonl")
    parser.add_argument("--limit", type=int, default=10_000,
                        help="Max records per source dataset")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        total += fetch_zefang(f, args.limit)
        total += fetch_training_data_pro(f, args.limit)
        total += fetch_seven_phishing(f, args.limit)
        total += fetch_difraud(f, args.limit)
        total += fetch_all_scam_spam(f, args.limit)

    print(f"\nTotal records saved: {total} -> {out_path}")
