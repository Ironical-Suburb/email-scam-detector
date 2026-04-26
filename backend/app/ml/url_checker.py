import asyncio
import httpx
from app.config import settings

SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"


async def check_urls(urls: list[str]) -> dict:
    if not urls:
        return {"score": 0.0, "malicious_urls": []}

    if not settings.google_safe_browsing_api_key:
        return {"score": 0.0, "malicious_urls": [], "warning": "API key not configured"}

    threat_entries = [{"url": u} for u in urls[:20]]  # cap at 20 per call
    payload = {
        "client": {"clientId": "email-scam-detector", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": threat_entries,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                SAFE_BROWSING_URL,
                params={"key": settings.google_safe_browsing_api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {"score": 0.0, "malicious_urls": [], "error": "Safe Browsing check failed"}

    matches = data.get("matches", [])
    malicious = [m["threat"]["url"] for m in matches]
    # Any malicious URL → maximum URL risk score
    score = 1.0 if malicious else 0.0

    return {"score": score, "malicious_urls": malicious}
