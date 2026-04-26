"""
Bootstrap the GitHub Project board for email-scam-detector.

Usage:
    pip install requests
    GITHUB_TOKEN=ghp_... GITHUB_OWNER=<your-username> python scripts/setup_github_project.py

Requires:
    - A classic token or fine-grained token with:
        repo  (read/write issues)
        project  (read/write projects)
    - The GitHub repo must already exist.
"""

import os
import sys
import requests

OWNER = os.environ.get("GITHUB_OWNER", "")
REPO = os.environ.get("GITHUB_REPO", "email-scam-detector")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not OWNER or not TOKEN:
    sys.exit("Set GITHUB_OWNER and GITHUB_TOKEN environment variables first.")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
GQL_URL = "https://api.github.com/graphql"
REST_BASE = "https://api.github.com"


# ── helpers ──────────────────────────────────────────────────────────────────

def gql(query: str, variables: dict = None) -> dict:
    resp = requests.post(GQL_URL, json={"query": query, "variables": variables or {}}, headers=HEADERS)
    resp.raise_for_status()
    body = resp.json()
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def create_issue(title: str, body: str, labels: list[str]) -> int:
    resp = requests.post(
        f"{REST_BASE}/repos/{OWNER}/{REPO}/issues",
        headers=HEADERS,
        json={"title": title, "body": body, "labels": labels},
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"  Created issue #{data['number']}: {title}")
    return data["node_id"]


def ensure_label(name: str, color: str, description: str = "") -> None:
    resp = requests.post(
        f"{REST_BASE}/repos/{OWNER}/{REPO}/labels",
        headers=HEADERS,
        json={"name": name, "color": color, "description": description},
    )
    if resp.status_code not in (201, 422):  # 422 = already exists
        resp.raise_for_status()


# ── labels ───────────────────────────────────────────────────────────────────

LABELS = [
    ("phase-1-training", "0075ca", "Training data & model pipeline"),
    ("phase-2-detection", "e4e669", "Live email detection flow"),
    ("ml", "5319e7", "Machine learning"),
    ("backend", "d93f0b", "FastAPI / Python backend"),
    ("mobile", "0e8a16", "React Native mobile app"),
    ("infra", "bfd4f2", "Infrastructure / DevOps"),
    ("data", "c5def5", "Data collection or processing"),
]


# ── issues ───────────────────────────────────────────────────────────────────

ISSUES = [
    # ── Phase 1: Data collection ──────────────────────────────────────────────
    {
        "title": "[Data] PhishTank integration — fetch & store verified phishing emails",
        "body": (
            "Query the PhishTank API to download verified phishing URLs and associated email templates.\n\n"
            "**Acceptance criteria**\n"
            "- `scripts/data_collection/phishtank_fetch.py` fetches via API key stored in env\n"
            "- Saves raw JSON to `data/raw/phishtank/`\n"
            "- Deduplicates on `phish_id`\n"
            "- Target: ≥ 5,000 entries per run"
        ),
        "labels": ["phase-1-training", "data"],
    },
    {
        "title": "[Data] Enron corpus loader — parse and label 500k corporate emails",
        "body": (
            "Download and parse the Enron email dataset. Researcher-provided spam labels already exist.\n\n"
            "**Acceptance criteria**\n"
            "- `scripts/data_collection/enron_loader.py` loads `.mbox` or raw directory format\n"
            "- Outputs `data/processed/enron_labeled.parquet` with columns: `body`, `subject`, `label`\n"
            "- Ham / spam split logged to stdout"
        ),
        "labels": ["phase-1-training", "data"],
    },
    {
        "title": "[Data] Dataset preparation — GPT-4 zero-shot category labeler",
        "body": (
            "Use a GPT-4 prompt to assign each cleaned email to one of the known scam categories "
            "(IRS, tech support, lottery, bank fraud, etc.).\n\n"
            "**Acceptance criteria**\n"
            "- `scripts/data_collection/prepare_dataset.py` reads from `data/raw/` and writes `data/processed/labeled_dataset.parquet`\n"
            "- Category distribution printed as a table\n"
            "- Falls back gracefully if OPENAI_API_KEY is absent (skips labeling, keeps existing labels)"
        ),
        "labels": ["phase-1-training", "data", "ml"],
    },
    # ── Phase 1: Parsing & features ──────────────────────────────────────────
    {
        "title": "[Backend] Email MIME parser — extract body, subject, headers, URLs",
        "body": (
            "Using Python `email` std-lib + `beautifulsoup4` to turn raw MIME into structured features.\n\n"
            "**Acceptance criteria**\n"
            "- `app/email_processor/parser.py` returns a `ParsedEmail` dataclass with:\n"
            "  - `body_text` (HTML stripped)\n"
            "  - `subject`\n"
            "  - `urls` (list)\n"
            "  - `sender_domain`\n"
            "  - `reply_to_mismatch` (bool)\n"
            "  - `spf_dkim_fail` (bool)\n"
            "- Handles base64-encoded payloads and forwarded chains\n"
            "- Unit tests covering multipart MIME, HTML-only, and plain-text inputs"
        ),
        "labels": ["phase-1-training", "phase-2-detection", "backend"],
    },
    # ── Phase 1: ML training ─────────────────────────────────────────────────
    {
        "title": "[ML] Fine-tune DistilBERT multi-class scam classifier",
        "body": (
            "Fine-tune `distilbert-base-uncased` on the labeled dataset from the preparation step.\n\n"
            "**Acceptance criteria**\n"
            "- `scripts/training/train_classifier.py` accepts `--feedback-csv` and `--incremental` flags\n"
            "- Saves model to `models/classifier/`\n"
            "- Writes `models/classifier/eval_metrics.json` with F1, precision, recall\n"
            "- F1 ≥ 0.85 on held-out test split\n"
            "- Model size ≤ 70 MB"
        ),
        "labels": ["phase-1-training", "ml"],
    },
    {
        "title": "[ML] Build SBERT + ChromaDB vector store",
        "body": (
            "Embed every cleaned email body with `sentence-transformers` and store in ChromaDB, "
            "partitioned by scam category.\n\n"
            "**Acceptance criteria**\n"
            "- `scripts/training/build_vector_store.py` reads `data/processed/labeled_dataset.parquet`\n"
            "- Persists ChromaDB to `data/chroma/`\n"
            "- Each collection named after scam category\n"
            "- Similarity query returns cosine score + category label in < 200 ms locally"
        ),
        "labels": ["phase-1-training", "ml"],
    },
    # ── Phase 2: Email connection ─────────────────────────────────────────────
    {
        "title": "[Backend] Gmail OAuth2 connection + Google Pub/Sub push notifications",
        "body": (
            "Connect to Gmail via OAuth2 (read-only scope) and receive new-email events via Pub/Sub webhook.\n\n"
            "**Acceptance criteria**\n"
            "- `app/email_processor/gmail_client.py` authenticates with `google-auth-oauthlib`\n"
            "- `POST /api/v1/webhook/pubsub` receives and validates Pub/Sub push messages\n"
            "- Decodes base64 message data and enqueues for processing\n"
            "- Falls back to polling if Pub/Sub is unavailable (dev mode)"
        ),
        "labels": ["phase-2-detection", "backend"],
    },
    {
        "title": "[Backend] IMAP IDLE client for non-Gmail providers",
        "body": (
            "Use `imaplib` with IMAP IDLE to keep a persistent connection and fire an event on new mail.\n\n"
            "**Acceptance criteria**\n"
            "- `app/email_processor/imap_client.py` connects via OAuth2 or app password\n"
            "- IDLE loop reconnects automatically on connection drop\n"
            "- New-message callback is async-compatible (fires a FastAPI background task)"
        ),
        "labels": ["phase-2-detection", "backend"],
    },
    # ── Phase 2: ML inference ─────────────────────────────────────────────────
    {
        "title": "[ML] URL reputation check via Google Safe Browsing API",
        "body": (
            "For every URL extracted from an email body, query the Google Safe Browsing API.\n\n"
            "**Acceptance criteria**\n"
            "- `app/ml/url_checker.py` batches up to 500 URLs per request\n"
            "- Returns `UrlReputationResult` with `is_malicious: bool` and `threat_type: str | None`\n"
            "- Gracefully degrades (returns `is_malicious=False`) when API key is absent or quota exceeded\n"
            "- Free tier limit (10k req/day) tracked via a daily counter in Redis or a simple file"
        ),
        "labels": ["phase-2-detection", "ml", "backend"],
    },
    {
        "title": "[ML] Risk score combiner — weighted 0–100 score + scam type label",
        "body": (
            "Combine four signals into a final risk score:\n"
            "- Cosine similarity (40%)\n"
            "- Classifier confidence (30%)\n"
            "- URL reputation (20%)\n"
            "- Header anomalies (10%)\n\n"
            "**Acceptance criteria**\n"
            "- `app/ml/risk_scorer.py` accepts all four inputs and returns `RiskScore(score: float, label: str)`\n"
            "- Weights configurable via env / settings without code changes\n"
            "- Threshold constants: FLAG=0.70, REVIEW=0.50\n"
            "- Unit tests covering edge cases (all signals high, all low, URL-only signal)"
        ),
        "labels": ["phase-2-detection", "ml", "backend"],
    },
    {
        "title": "[Backend] POST /api/v1/detect — parallel async ML inference endpoint",
        "body": (
            "Expose the full detection pipeline as a FastAPI endpoint. Both ML passes must run concurrently.\n\n"
            "**Acceptance criteria**\n"
            "- `app/api/detect.py` runs SBERT similarity + DistilBERT classifier as `asyncio.gather` tasks\n"
            "- End-to-end latency < 500 ms on CPU-only server (measured in CI with `httpx` timing)\n"
            "- Returns `DetectResponse(risk_score, scam_type, flagged, protocol_steps)`\n"
            "- Flagged emails saved to PostgreSQL via `FlaggedEmail` model"
        ),
        "labels": ["phase-2-detection", "backend", "ml"],
    },
    # ── Phase 2: Feedback loop ────────────────────────────────────────────────
    {
        "title": "[Backend] POST /api/v1/feedback — record user confirmations",
        "body": (
            "Store true positive / false positive confirmations from the mobile app.\n\n"
            "**Acceptance criteria**\n"
            "- `app/api/feedback.py` accepts `{email_id, confirmed: bool}`\n"
            "- Updates `flagged_emails.user_confirmed` in PostgreSQL\n"
            "- False positives (confirmed=False) logged to a separate `false_positives` table with sender domain\n"
            "- Rate-limited to 1 feedback per email per user"
        ),
        "labels": ["phase-2-detection", "backend"],
    },
    # ── Database ──────────────────────────────────────────────────────────────
    {
        "title": "[Infra] PostgreSQL schema + Alembic migrations",
        "body": (
            "Define the SQLAlchemy models and initial Alembic migration.\n\n"
            "**Tables needed**\n"
            "- `flagged_emails` — id, user_id, email_id, body_text, risk_score, scam_type, user_confirmed, created_at\n"
            "- `false_positives` — id, sender_domain, count, last_seen\n\n"
            "**Acceptance criteria**\n"
            "- `alembic upgrade head` runs cleanly against a fresh Postgres 16 instance\n"
            "- Models are in `app/db/models.py`\n"
            "- Async session factory in `app/db/session.py`"
        ),
        "labels": ["backend", "infra"],
    },
    # ── Mobile ────────────────────────────────────────────────────────────────
    {
        "title": "[Mobile] Inbox screen — email list with risk badge",
        "body": (
            "Display emails in a scrollable list. Flagged emails show a red risk badge; "
            "review-tier emails show yellow.\n\n"
            "**Acceptance criteria**\n"
            "- `mobile/src/screens/InboxScreen.tsx` fetches from backend API on mount and on pull-to-refresh\n"
            "- Large, readable font (min 18sp) per elder-friendly design brief\n"
            "- Badge visible at a glance without opening the email"
        ),
        "labels": ["mobile", "phase-2-detection"],
    },
    {
        "title": "[Mobile] Email detail screen — scam banner + protocol card",
        "body": (
            "Show the full email with a red banner at the top for flagged emails.\n\n"
            "**Acceptance criteria**\n"
            "- `mobile/src/screens/EmailDetailScreen.tsx` renders `<ScamBanner>` when `flagged=true`\n"
            "- `<ProtocolCard>` shows numbered steps in plain language (Grade 6 reading level)\n"
            "- 'Tell a family member' button pre-fills an SMS to the stored trusted contact\n"
            "- 'Yes, scam' / 'No, real email' feedback buttons POST to `/api/v1/feedback`"
        ),
        "labels": ["mobile", "phase-2-detection"],
    },
    # ── Infra / CI ────────────────────────────────────────────────────────────
    {
        "title": "[Infra] Docker Compose local dev environment",
        "body": (
            "Ensure `docker compose up` starts backend + PostgreSQL with no manual steps.\n\n"
            "**Acceptance criteria**\n"
            "- `docker-compose.yml` starts `db` and `backend` services\n"
            "- Health check on `db` before `backend` starts\n"
            "- `.env.example` documents all required environment variables\n"
            "- `docker compose up` succeeds from a clean clone with only Docker installed"
        ),
        "labels": ["infra"],
    },
    {
        "title": "[Infra] Add ruff config + pytest setup to backend",
        "body": (
            "Add a `pyproject.toml` configuring ruff and pytest so CI has stable lint rules.\n\n"
            "**Acceptance criteria**\n"
            "- `pyproject.toml` at `backend/pyproject.toml` with `[tool.ruff]` and `[tool.pytest.ini_options]`\n"
            "- `ruff check .` and `ruff format --check .` pass on the existing codebase\n"
            "- `pytest tests/` exits 0 (even with no tests, using `--ignore-glob` if needed)"
        ),
        "labels": ["infra", "backend"],
    },
]


# ── project creation ──────────────────────────────────────────────────────────

def get_owner_node_id() -> str:
    data = gql("query($login: String!) { user(login: $login) { id } }", {"login": OWNER})
    return data["user"]["id"]


def create_project(owner_id: str, title: str) -> str:
    mutation = """
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: { ownerId: $ownerId, title: $title }) {
        projectV2 { id url }
      }
    }
    """
    data = gql(mutation, {"ownerId": owner_id, "title": title})
    project = data["createProjectV2"]["projectV2"]
    print(f"Created project: {project['url']}")
    return project["id"]


def add_issue_to_project(project_id: str, issue_node_id: str) -> None:
    mutation = """
    mutation($projectId: ID!, $contentId: ID!) {
      addProjectV2ItemById(input: { projectId: $projectId, contentId: $contentId }) {
        item { id }
      }
    }
    """
    gql(mutation, {"projectId": project_id, "contentId": issue_node_id})


def main() -> None:
    print(f"Setting up project for {OWNER}/{REPO}")

    # 1. Ensure labels exist
    print("\n[1/4] Creating labels...")
    for name, color, description in LABELS:
        ensure_label(name, color, description)
        print(f"  label: {name}")

    # 2. Create issues
    print("\n[2/4] Creating issues...")
    issue_node_ids = []
    for issue in ISSUES:
        node_id = create_issue(issue["title"], issue["body"], issue["labels"])
        issue_node_ids.append(node_id)

    # 3. Create project board
    print("\n[3/4] Creating GitHub Project...")
    owner_id = get_owner_node_id()
    project_id = create_project(owner_id, "Email Scam Detector — Roadmap")

    # 4. Add all issues to the project
    print("\n[4/4] Adding issues to project...")
    for node_id in issue_node_ids:
        add_issue_to_project(project_id, node_id)
    print(f"  Added {len(issue_node_ids)} issues to the project board.")

    print("\nDone. Open the project board to organise items into Status columns (Backlog / In Progress / Done).")
    print("Tip: GitHub Projects v2 auto-creates a Status field — just drag cards.")


if __name__ == "__main__":
    main()
