import asyncio
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import settings

_embedder: Optional[SentenceTransformer] = None
_chroma_collection = None


def load_embedder() -> None:
    global _embedder, _chroma_collection
    _embedder = SentenceTransformer(settings.embedder_model_name)

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _chroma_collection = client.get_or_create_collection(
        name="scam_emails",
        metadata={"hnsw:space": "cosine"},
    )


def _query_similarity(text: str) -> dict:
    if _embedder is None or _chroma_collection is None:
        raise RuntimeError("Embedder not loaded. Call load_embedder() at startup.")

    embedding = _embedder.encode(text, convert_to_list=True)
    results = _chroma_collection.query(
        query_embeddings=[embedding],
        n_results=5,
        include=["distances", "metadatas"],
    )

    if not results["distances"][0]:
        return {"score": 0.0, "cluster_label": None}

    # ChromaDB cosine distance → similarity
    top_distance = results["distances"][0][0]
    similarity = 1.0 - top_distance
    top_metadata = results["metadatas"][0][0] if results["metadatas"][0] else {}

    return {
        "score": round(max(0.0, similarity), 4),
        "cluster_label": top_metadata.get("scam_type"),
    }


async def get_similarity_score(text: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query_similarity, text)
