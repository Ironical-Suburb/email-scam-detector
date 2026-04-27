"""
Loads the Enron spam dataset directly from HuggingFace — no manual download needed.
Also supports loading local maildir/SpamAssassin layouts if you have them.

HuggingFace source: SetFit/enron_spam
  ~33,000 emails, labeled spam / ham (not_scam)

Usage:
    # Stream from HuggingFace (recommended — no download required)
    python scripts/data_collection/enron_loader.py --out data/raw/enron_spam.jsonl

    # Load from local maildir + SpamAssassin dirs instead
    python scripts/data_collection/enron_loader.py --local \
        --enron-dir data/raw/enron --spam-dir data/raw/spamassassin \
        --out data/raw/enron_spam.jsonl
"""

import argparse
import email
import json
from pathlib import Path

from bs4 import BeautifulSoup


# ── HuggingFace loader ────────────────────────────────────────────────────────

def load_from_huggingface(out_f, limit: int = 20_000) -> int:
    from datasets import load_dataset

    print("Downloading SetFit/enron_spam from HuggingFace ...")
    ds = load_dataset("SetFit/enron_spam", split="train")

    count = 0
    for row in ds:
        if count >= limit:
            break

        body = str(row.get("text", "") or row.get("body", "")).strip()
        subject = str(row.get("subject", "")).strip()

        if len(body) < 30:
            continue

        # SetFit/enron_spam uses label 1 = spam, 0 = ham
        raw_label = row.get("label", row.get("label_text", ""))
        if str(raw_label) in ("1", "spam"):
            label = "spam"
        else:
            label = "not_scam"

        record = {
            "subject": subject,
            "from": str(row.get("sender", "")),
            "body": body[:4000],
            "label": label,
            "scam_type": label,
            "source": "enron_hf",
        }
        out_f.write(json.dumps(record) + "\n")
        count += 1

    return count


# ── Local maildir loader (kept for users who have the raw corpus) ─────────────

def _body_from_bytes(raw: bytes) -> str:
    msg = email.message_from_bytes(raw)
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    parts.append(
                        part.get_payload(decode=True).decode("utf-8", errors="replace")
                    )
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
        if not path.is_file() or count >= limit:
            break
        try:
            body = _body_from_bytes(path.read_bytes())
            if len(body) < 30:
                continue
            out_f.write(json.dumps({
                "subject": "",
                "from": "",
                "body": body[:4000],
                "label": label,
                "scam_type": label,
                "source": root.name,
            }) + "\n")
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
            if not path.is_file():
                continue
            try:
                body = _body_from_bytes(path.read_bytes())
                if len(body) < 30:
                    continue
                out_f.write(json.dumps({
                    "subject": "",
                    "from": "",
                    "body": body[:4000],
                    "label": label,
                    "scam_type": label,
                    "source": "spamassassin",
                }) + "\n")
                count += 1
            except Exception:
                pass
    return count


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/raw/enron_spam.jsonl")
    parser.add_argument("--limit", type=int, default=30_000,
                        help="Max emails to load from HuggingFace")
    parser.add_argument("--local", action="store_true",
                        help="Load from local dirs instead of HuggingFace")
    parser.add_argument("--enron-dir", default="data/raw/enron")
    parser.add_argument("--spam-dir", default="data/raw/spamassassin")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        if args.local:
            n = load_maildir(Path(args.enron_dir), "not_scam", f)
            print(f"Loaded {n} Enron emails from local dir")
            n2 = load_spamassassin(Path(args.spam_dir), f)
            print(f"Loaded {n2} SpamAssassin emails from local dir")
        else:
            n = load_from_huggingface(f, limit=args.limit)
            print(f"Loaded {n} Enron emails from HuggingFace")

    print(f"Saved -> {out_path}")
