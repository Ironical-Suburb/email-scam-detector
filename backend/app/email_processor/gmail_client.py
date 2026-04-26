"""
Gmail integration via OAuth2 + Google Pub/Sub push notifications.

Setup steps:
1. Create a GCP project and enable the Gmail API.
2. Create OAuth2 credentials (Desktop or Web app type).
3. Store client_id and client_secret in .env.
4. Run the one-time OAuth flow to generate token.json.
5. Create a Pub/Sub topic and subscription pointing at /api/v1/webhook/gmail.
6. Call watch_inbox() once per user at login (Gmail watch expires every 7 days).
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_TOKEN_PATH = "token.json"
_CREDENTIALS_PATH = "credentials.json"


def _get_service():
    creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)
    return build("gmail", "v1", credentials=creds)


def watch_inbox(user_email: str, pubsub_topic: str) -> dict:
    """
    Register a Pub/Sub watch on the user's inbox.
    Must be called once at login and renewed every 7 days.
    """
    service = _get_service()
    body = {
        "labelIds": ["INBOX"],
        "topicName": pubsub_topic,
    }
    return service.users().watch(userId=user_email, body=body).execute()


async def fetch_message_by_id(user_email: str, history_id: str) -> None:
    """
    Called from the webhook background task.
    Fetches the new message(s) since history_id and routes them to the detector.
    """
    from app.api.detect import detect_email
    from pydantic import BaseModel

    service = _get_service()
    history = (
        service.users()
        .history()
        .list(userId=user_email, startHistoryId=history_id, historyTypes=["messageAdded"])
        .execute()
    )

    for record in history.get("history", []):
        for added in record.get("messagesAdded", []):
            msg_id = added["message"]["id"]
            raw_resp = (
                service.users()
                .messages()
                .get(userId=user_email, id=msg_id, format="raw")
                .execute()
            )
            raw_bytes = base64.urlsafe_b64decode(raw_resp["raw"])
            raw_str = raw_bytes.decode("utf-8", errors="replace")

            class _Req(BaseModel):
                raw_email: str
                user_id: str

            await detect_email(_Req(raw_email=raw_str, user_id=user_email))
