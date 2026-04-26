"""
Loads the Enron email corpus and SpamAssassin dataset, emits labeled JSONL.

Expected layout (download separately):
    data/raw/enron/          → maildir format from CMU
    data/raw/spamassassin/   → spam/ and ham/ subdirectories

Downloads:
  Enron:        https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz
  SpamAssassin: https://spamassassin.apache.org/old/publiccorpus/

Usage:
    python scripts/data_collection/enron_loader.py --out data/raw/enron_spam.jsonl
"""

import argparse
import email
import json
import os
from email import policy
from pathlib import Path
from bs4 import BeautifulSoup


def _body(msg) -> str:
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                try:
                    parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode("utf-8", errors="replace")
                if msg.get_content_type() == "text/html":
                    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
                parts.append(text)
        except Exception:
            pass
    return " ".join(parts).strip()


def load_maildir(root: Path, label: str, out_f, limit: int = 50_000) -> int:
    count = 0
    for path in root.rglob("*"):
        if path.is_file() and count < limit:
            try:
                raw = path.read_bytes()
                msg = email.message_from_bytes(raw)
                body = _body(msg)
                if len(body) < 30:
                    continue
                record = {
                    "subject": str(msg.get("subject", "")),
                    "from": str(msg.get("from", "")),
                    "body": body[:4000],
                    "label": label,
                    "source": str(root.name),
                }
                out_f.write(json.dumps(record) + "\n")
                count += 1
            except Exception:
                pass
    return count


def load_spamassassin(root: Path, out_f) -> int:
    count = 0
    for subdir, label in [("spam", "spam"), ("ham", "not_scam")]:
        folder = root / subdir
        if not folder.exists():
            continue
        for path in folder.iterdir():
            if path.is_file():
                try:
                    raw = path.read_bytes()
                    msg = email.message_from_bytes(raw)
                    body = _body(msg)
                    if len(body) < 30:
                        continue
                    record = {
                        "subject": str(msg.get("subject", "")),
                        "from": str(msg.get("from", "")),
                        "body": body[:4000],
                        "label": label,
                        "source": "spamassassin",
                    }
                    out_f.write(json.dumps(record) + "\n")
                    count += 1
                except Exception:
                    pass
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--enron-dir", default="data/raw/enron")
    parser.add_argument("--spam-dir", default="data/raw/spamassassin")
    parser.add_argument("--out", default="data/raw/enron_spam.jsonl")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        n = load_maildir(Path(args.enron_dir), "not_scam", f)
        print(f"Loaded {n} Enron emails")
        n2 = load_spamassassin(Path(args.spam_dir), f)
        print(f"Loaded {n2} SpamAssassin emails")

    print(f"Saved → {out_path}")
