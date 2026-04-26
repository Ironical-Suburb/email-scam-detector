from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import FlaggedEmail, UserFeedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    flagged_email_id: int
    is_scam: bool
    user_id: str


@router.post("/")
async def submit_feedback(req: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FlaggedEmail).where(FlaggedEmail.id == req.flagged_email_id)
    )
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Flagged email not found")

    feedback = UserFeedback(
        flagged_email_id=req.flagged_email_id,
        user_id=req.user_id,
        confirmed_scam=req.is_scam,
    )
    db.add(feedback)
    await db.commit()
    return {"status": "recorded"}
