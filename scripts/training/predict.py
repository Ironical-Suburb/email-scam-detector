"""
Quick inference with automatic feature-prefix injection.

Usage:
    python scripts/training/predict.py --subject "Security Update" --body "Hi, click here..."
    python scripts/training/predict.py --text "full email text without subject"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from transformers import pipeline
from train_classifier import _feature_prefix


def predict(model_dir: str, subject: str, body: str) -> list[dict]:
    clf = pipeline("text-classification", model=model_dir, top_k=None)
    prefix = _feature_prefix(subject, body)
    text = prefix + f"{subject} [SEP] {body}"
    results = clf(text[:512 * 4])
    return sorted(results, key=lambda x: x["score"], reverse=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",   default="models/distilbert-scam")
    parser.add_argument("--subject", default="")
    parser.add_argument("--body",    default="")
    parser.add_argument("--text",    default="", help="Full text (no subject split)")
    args = parser.parse_args()

    subject = args.subject
    body    = args.body or args.text

    results = predict(args.model, subject, body)
    print(json.dumps(results, indent=2))
