# Email Scam Detector

An AI-powered email scam detection system designed to protect elderly users. It connects to Gmail (or any IMAP mailbox), analyzes incoming emails in real time using a fine-tuned DistilBERT classifier and SBERT vector similarity, and surfaces scam warnings with plain-language protocol steps inside a React Native mobile app.

## Architecture

```
email-scam-detector/
├── backend/          FastAPI server — ML inference, Gmail webhook, PostgreSQL
├── mobile/           React Native app — elder-friendly UI, scam banners
├── scripts/
│   ├── data_collection/   Fetch PhishTank, Enron, SpamAssassin
│   └── training/          Fine-tune DistilBERT, build ChromaDB vector store
└── docker-compose.yml
```

### Detection pipeline

1. **Email arrives** via Gmail Pub/Sub push notification or IMAP IDLE
2. **Parser** extracts body, subject, URLs, sender headers, SPF/DKIM status
3. **Two parallel ML passes** (async FastAPI tasks):
   - SBERT embedding → ChromaDB nearest-neighbour → cosine similarity score
   - DistilBERT classifier → scam category probability
4. **URL reputation** checked via Google Safe Browsing API
5. **Risk combiner** weights four signals → single 0–100% score
6. **Flag threshold 70%** triggers a red banner + scam-specific protocol steps

### Risk score weights (tunable in `.env`)

| Signal | Default weight |
|---|---|
| Vector similarity | 40% |
| Classifier confidence | 30% |
| URL reputation | 20% |
| Header anomalies (SPF/DKIM/lookalike) | 10% |

## Quick start

```bash
# 1. Start Postgres and the FastAPI backend
cp backend/.env.example backend/.env   # fill in your API keys
docker compose up --build

# 2. (One-time) Collect training data and build the vector store
python scripts/data_collection/phishtank_fetch.py
python scripts/data_collection/enron_loader.py
python scripts/data_collection/prepare_dataset.py --label-with-gpt
python scripts/training/build_vector_store.py
python scripts/training/train_classifier.py

# 3. Run the mobile app
cd mobile && npm install && npx react-native start
```

## Tech stack

| Component | Tool |
|---|---|
| Email connection | `imaplib` + Gmail API (OAuth2, read-only) |
| Push notifications | Google Pub/Sub |
| HTML parsing | `beautifulsoup4` |
| URL reputation | Google Safe Browsing API (10k req/day free) |
| Embeddings | `sentence-transformers` (SBERT, local) |
| Vector store | ChromaDB (local dev) / Pinecone (prod) |
| Classifier | `transformers` DistilBERT, fine-tuned (~67 MB) |
| API backend | FastAPI + asyncio |
| Database | PostgreSQL (flagged emails + user feedback) |
| Mobile UI | React Native (large text, elder-friendly) |

## Gmail OAuth2 setup

1. Create a GCP project → enable Gmail API and Pub/Sub.
2. Create OAuth2 credentials → download `credentials.json` → place in `backend/`.
3. Run the one-time consent flow to generate `token.json`.
4. Create a Pub/Sub topic and push subscription pointing to `POST /api/v1/webhook/gmail`.
5. Call `watch_inbox()` once per user at login (renew every 7 days).

## Retraining

User feedback is stored in `user_feedback`. Run retraining monthly:

```bash
python scripts/data_collection/prepare_dataset.py
python scripts/training/train_classifier.py
python scripts/training/build_vector_store.py
```
