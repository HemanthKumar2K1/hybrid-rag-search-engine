import os
import pickle
from typing import Dict, List, Optional

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from retrieval.semantic_search import RetrievedChunk

RRF_K = 60


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _build_bm25(collection: chromadb.Collection) -> Dict:
    data = collection.get(include=["documents", "metadatas"])
    return {
        "bm25": BM25Okapi([_tokenize(d) for d in data["documents"]]) if data["documents"] else None,
        "documents": data["documents"],
        "metadatas": data["metadatas"],
        "ids": data["ids"],
    }


def save_bm25_index(index_path: str, collection: chromadb.Collection) -> None:
    """Build BM25 once at ingest time so queries don't have to pull the whole corpus."""
    index = _build_bm25(collection)
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    with open(index_path, "wb") as f:
        pickle.dump(index, f)
    print(f"Saved BM25 index to {index_path} ({len(index['documents'])} docs)")


def load_bm25_index(index_path: str) -> Dict:
    with open(index_path, "rb") as f:
        return pickle.load(f)


def _print_ranking(title: str, rows: List[tuple]) -> None:
    print(f"\n{'-' * 60}\n{title}\n{'-' * 60}")
    for i, (label, score, meta, text) in enumerate(rows, 1):
        doc = meta.get("doc_title", "?")
        section = meta.get("section_title", "?")
        print(f"  #{i}  {label}={score:<10.4f} [{doc} | {section}]")
        print(f"       \"{text[:80].replace(chr(10), ' ')}...\"")


def search(query: str, collection: chromadb.Collection, model: SentenceTransformer,
           top_k: int, bm25_index: Optional[Dict] = None) -> List[RetrievedChunk]:
    """
    BM25 + vector search merged with Reciprocal Rank Fusion:
        score(doc) = sum over rankings of 1 / (rank + 60)
    """
    index = bm25_index or _build_bm25(collection)
    documents, metadatas, ids = index["documents"], index["metadatas"], index["ids"]
    if not documents:
        return []

    id_to_idx = {doc_id: i for i, doc_id in enumerate(ids)}

    # keyword side
    bm25_scores = index["bm25"].get_scores(_tokenize(query))
    bm25_ranked = sorted(range(len(documents)), key=lambda i: bm25_scores[i], reverse=True)

    # vector side
    vec = collection.query(
        query_embeddings=[model.encode([query])[0].tolist()],
        n_results=min(top_k * 2, len(documents)),
        include=["distances"],
    )
    vector_ids = [v for v in vec["ids"][0] if v in id_to_idx]
    vector_dist = dict(zip(vec["ids"][0], vec["distances"][0]))

    rrf: Dict[str, float] = {}
    for rank, idx in enumerate(bm25_ranked):
        rrf[ids[idx]] = rrf.get(ids[idx], 0.0) + 1.0 / (rank + RRF_K)
    for rank, doc_id in enumerate(vector_ids):
        rrf[doc_id] = rrf.get(doc_id, 0.0) + 1.0 / (rank + RRF_K)

    fused = sorted(rrf, key=rrf.get, reverse=True)[:top_k]

    def row(label, score, doc_id):
        i = id_to_idx[doc_id]
        return label, score, metadatas[i], documents[i]

    _print_ranking("BM25 (keyword)", [row("score", bm25_scores[i], ids[i]) for i in bm25_ranked[:top_k]])
    _print_ranking("Vector (semantic)", [row("dist", vector_dist[v], v) for v in vector_ids[:top_k]])
    _print_ranking("After RRF", [row("rrf", rrf[d], d) for d in fused])

    return [
        RetrievedChunk(
            content=documents[id_to_idx[d]],
            metadata=metadatas[id_to_idx[d]],
            score=rrf[d],
            rank=rank + 1,
        )
        for rank, d in enumerate(fused)
    ]
