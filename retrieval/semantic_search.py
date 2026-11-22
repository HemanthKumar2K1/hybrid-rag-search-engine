from dataclasses import dataclass
from typing import List

import chromadb
from sentence_transformers import SentenceTransformer


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float
    rank: int  # 1-based


def search(query: str, collection: chromadb.Collection,
           model: SentenceTransformer, top_k: int) -> List[RetrievedChunk]:
    """Plain vector search, kept as a baseline to compare against hybrid search."""
    results = collection.query(
        query_embeddings=[model.encode([query])[0].tolist()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    return [
        RetrievedChunk(content=doc, metadata=meta, score=dist, rank=i + 1)
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ))
    ]
