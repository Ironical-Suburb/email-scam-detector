"""
Downloads verified phishing URL data from PhishTank and saves labeled records.

Usage:
    python scripts/data_collection/phishtank_fetch.py --out data/raw/phishtank.jsonl

API docs: https://phishtank.org/developer_info.php
Rate limit: 1 request/minute without an API key; register for a free key.
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path


PHISHTANK_URL = "http://data.phishtank.com/data/{api_key}/online-valid.json"


def fetch(api_key: str, out_path: Path) -> None:
    url = PHISHTANK_URL.format(api_key=api_key if api_key else "anonymous")
    print(f"Fetching PhishTank data from {url} ...")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(url, headers={"User-Agent": "email-scam-detector/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        entries = json.loads(resp.read().decode())

    print(f"  Downloaded {len(entries)} entries")

    with out_path.open("w") as f:
        for entry in entries:
            record = {
                "url": entry.get("url"),
                "phish_detail_url": entry.get("phish_detail_url"),
                "submission_time": entry.get("submission_time"),
                "verified": entry.get("verified"),
                "target": entry.get("target"),
                "label": "phishing",
                "source": "phishtank",
            }
            f.write(json.dumps(record) + "\n")

    print(f"  Saved {len(entries)} records → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="", help="PhishTank API key (optional)")
    parser.add_argument("--out", default="data/raw/phishtank.jsonl")
    args = parser.parse_args()
    fetch(args.api_key, Path(args.out))
