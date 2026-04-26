import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.email_processor.parser import parse_email_features
from app.ml.embeddings import get_similarity_score
from app.ml.classifier import get_classifier_scores
from app.ml.url_checker import check_urls
from app.ml.risk_scorer import combine_risk_score
from app.db.models import FlaggedEmail
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

router = APIRouter(prefix="/detect", tags=["detect"])


class RawEmailRequest(BaseModel):
    raw_email: str
    user_id: str


class DetectionResult(BaseModel):
    risk_score: float
    risk_label: str          # "clean" | "review" | "flagged"
    scam_type: str | None
    protocol_steps: list[str]
    signals: dict


@router.post("/", response_model=DetectionResult)
async def detect_email(req: RawEmailRequest, db: AsyncSession = Depends(get_db)):
    features = parse_email_features(req.raw_email)

    similarity_task = asyncio.create_task(get_similarity_score(features["body"]))
    classifier_task = asyncio.create_task(get_classifier_scores(features["body"]))
    url_task = asyncio.create_task(check_urls(features["urls"]))

    similarity, classifier, url_rep = await asyncio.gather(
        similarity_task, classifier_task, url_task
    )

    result = combine_risk_score(
        similarity=similarity,
        classifier=classifier,
        url_reputation=url_rep,
        header_anomaly_score=features["header_anomaly_score"],
    )

    if result["risk_score"] >= 0.70:
        flagged = FlaggedEmail(
            user_id=req.user_id,
            risk_score=result["risk_score"],
            scam_type=result["scam_type"],
            raw_snippet=features["body"][:500],
        )
        db.add(flagged)
        await db.commit()

    return result
