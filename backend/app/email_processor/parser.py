import email
import re
import urllib.parse
from email import policy
from email.message import EmailMessage

from bs4 import BeautifulSoup


_URL_RE = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
_LOOKALIKE_RE = re.compile(
    r'(paypa[l1]|amazon[-.]?support|micros0ft|app1e|g00gle|bank[-.]?of[-.]?america)',
    re.IGNORECASE,
)


def parse_email_features(raw: str) -> dict:
    msg: EmailMessage = email.message_from_string(raw, policy=policy.default)

    body = _extract_body(msg)
    subject = str(msg.get("subject", ""))
    sender = str(msg.get("from", ""))
    reply_to = str(msg.get("reply-to", ""))
    urls = _extract_urls(body)

    header_anomaly_score = _score_headers(msg, sender, reply_to)

    return {
        "body": body,
        "subject": subject,
        "sender": sender,
        "reply_to": reply_to,
        "urls": urls,
        "header_anomaly_score": header_anomaly_score,
    }


def _extract_body(msg: EmailMessage) -> str:
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                parts.append(part.get_content())
            elif ct == "text/html" and not parts:
                parts.append(_strip_html(part.get_content()))
    else:
        content = msg.get_content()
        ct = msg.get_content_type()
        parts.append(_strip_html(content) if ct == "text/html" else content)

    return " ".join(parts).strip()


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _extract_urls(text: str) -> list[str]:
    raw_urls = _URL_RE.findall(text)
    # Expand common shorteners by keeping the raw URL — actual expansion happens at runtime
    return list({urllib.parse.unquote(u) for u in raw_urls})


def _score_headers(msg: EmailMessage, sender: str, reply_to: str) -> float:
    score = 0.0

    # From/Reply-To mismatch
    if reply_to and _extract_domain(reply_to) != _extract_domain(sender):
        score += 0.4

    # SPF / DKIM fail
    auth_results = str(msg.get("authentication-results", "")).lower()
    if "spf=fail" in auth_results or "dmarc=fail" in auth_results:
        score += 0.3
    if "dkim=fail" in auth_results:
        score += 0.2

    # Lookalike sender domain
    if _LOOKALIKE_RE.search(sender):
        score += 0.3

    return round(min(score, 1.0), 4)


def _extract_domain(addr: str) -> str:
    match = re.search(r'@([\w.\-]+)', addr)
    return match.group(1).lower() if match else ""
