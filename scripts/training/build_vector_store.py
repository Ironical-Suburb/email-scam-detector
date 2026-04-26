"""
Embeds training emails with SBERT and populates the ChromaDB vector store.

Run after prepare_dataset.py. This only needs to run once (or on retraining).

Usage:
    python scripts/training/build_vector_store.py \
        --input data/processed/train.jsonl \
        --chroma-dir data/chroma \
        --model all-MiniLM-L6-v2
"""

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def build(args):
    print(f"Loading embedder: {args.model}")
    embedder = SentenceTransformer(args.model)

    client = chromadb.PersistentClient(path=args.chroma_dir)
    collection = client.get_or_create_collection(
        name="scam_emails",
        metadata={"hnsw:space": "cosine"},
    )

    records = []
    with open(args.input) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Embedding {len(records)} records ...")

    batch_size = 64
    for i in tqdm(range(0, len(records), batch_size)):
        batch = records[i : i + batch_size]
        texts = [r.get("body", "")[:512] for r in batch]
        embeddings = embedder.encode(texts).tolist()

        ids = [f"email_{i + j}" for j in range(len(batch))]
        metadatas = [
            {
                "scam_type": r.get("scam_type", "not_scam"),
                "subject": r.get("subject", "")[:200],
                "source": r.get("source", ""),
            }
            for r in batch
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    print(f"\nVector store built -> {args.chroma_dir}")
    print(f"Total vectors: {collection.count()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/processed/train.jsonl")
    parser.add_argument("--chroma-dir", default="data/chroma")
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()
    build(args)
