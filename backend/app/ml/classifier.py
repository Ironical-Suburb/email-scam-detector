import asyncio
from functools import lru_cache
from typing import Optional

import torch
from transformers import pipeline, Pipeline

from app.config import settings

_classifier: Optional[Pipeline] = None

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


def load_classifier() -> None:
    global _classifier
    try:
        _classifier = pipeline(
            "text-classification",
            model=settings.classifier_model_path,
            device=-1,  # CPU
            top_k=None,
        )
    except Exception:
        # Fall back to zero-shot if fine-tuned model isn't available yet
        _classifier = pipeline(
            "zero-shot-classification",
            model="typeform/distilbert-base-uncased-mnli",
            device=-1,
        )


def _run_classifier(text: str) -> dict:
    if _classifier is None:
        raise RuntimeError("Classifier not loaded. Call load_classifier() at startup.")

    truncated = text[:512]

    pipe_type = _classifier.task
    if pipe_type == "zero-shot-classification":
        result = _classifier(truncated, candidate_labels=SCAM_LABELS)
        scores = dict(zip(result["labels"], result["scores"]))
    else:
        result = _classifier(truncated)
        scores = {item["label"]: item["score"] for item in result}

    best_label = max(scores, key=lambda k: scores[k])
    return {"label": best_label, "confidence": scores[best_label], "all_scores": scores}


async def get_classifier_scores(text: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_classifier, text)
