from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api import detect, feedback, webhook
from app.ml.classifier import load_classifier
from app.ml.embeddings import load_embedder
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    load_classifier()
    load_embedder()
    yield


app = FastAPI(title="Email Scam Detector", lifespan=lifespan)

app.include_router(detect.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(webhook.router, prefix="/api/v1")
