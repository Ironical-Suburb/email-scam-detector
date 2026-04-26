import base64
import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks

from app.email_processor.gmail_client import fetch_message_by_id
from app.api.detect import detect_email
from pydantic import BaseModel

router = APIRouter(prefix="/webhook", tags=["webhook"])


class PubSubMessage(BaseModel):
    message: dict
    subscription: str


@router.post("/gmail")
async def gmail_pubsub_webhook(payload: PubSubMessage, background_tasks: BackgroundTasks):
    """
    Google Pub/Sub pushes a notification here the moment a new Gmail message arrives.
    The message data is base64-encoded JSON containing historyId and emailAddress.
    """
    try:
        data = json.loads(base64.b64decode(payload.message["data"]).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Pub/Sub payload")

    history_id = data.get("historyId")
    email_address = data.get("emailAddress")

    if not history_id or not email_address:
        raise HTTPException(status_code=400, detail="Missing historyId or emailAddress")

    background_tasks.add_task(fetch_message_by_id, email_address, history_id)
    return {"status": "accepted"}
