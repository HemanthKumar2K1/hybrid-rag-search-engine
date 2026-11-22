"""
Qdrant version of vectorstore/store.py, same function names.

QdrantCollectionWrapper mimics the .query() / .get() calls of a Chroma
collection, so the retrieval code works with either backend. To switch,
change the import in the ingest script and pipeline/nodes.py:

    from vectorstore.qdrant_store import get_or_create_collection, upsert_chunks, load_collection

Start Qdrant locally with:  docker run -p 6333:6333 qdrant/qdrant
"""
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, HnswConfigDiff, PointStruct, VectorParams

from chunking.character_splitter import Chunk
from vectorstore.store import chunk_id


def _split_payload(payload: dict):
    meta = {k: v for k, v in payload.items() if k != "_content"}
    return payload.get("_content", ""), meta


class QdrantCollectionWrapper:
    def __init__(self, client: QdrantClient, collection_name: str) -> None:
        self.client = client
        self.name = collection_name

    def query(self, query_embeddings: List[List[float]], n_results: int = 5,
              include: Optional[List[str]] = None) -> Dict[str, Any]:
        hits = self.client.search(
            collection_name=self.name,
            query_vector=query_embeddings[0],
            limit=n_results,
            with_payload=True,
        )
        docs, metas = zip(*[_split_payload(h.payload) for h in hits]) if hits else ((), ())
        return {
            "ids": [[str(h.id) for h in hits]],
            "documents": [list(docs)],
            "metadatas": [list(metas)],
            # qdrant gives cosine similarity, chroma gives distance
            "distances": [[1.0 - h.score for h in hits]],
        }

    def get(self, include: Optional[List[str]] = None) -> Dict[str, Any]:
        points, _ = self.client.scroll(collection_name=self.name, limit=100_000, with_payload=True)
        docs, metas = zip(*[_split_payload(p.payload) for p in points]) if points else ((), ())
        return {"ids": [str(p.id) for p in points], "documents": list(docs), "metadatas": list(metas)}


def _point_id(chunk: Chunk) -> str:
    # qdrant ids must be ints or UUIDs
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id(chunk)))


def get_or_create_collection(url: str, port: int, collection_name: str,
                             vector_size: int = 384) -> QdrantCollectionWrapper:
    client = QdrantClient(url=url, port=port)
    existing = {c.name for c in client.get_collections().collections}

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
        )

    return QdrantCollectionWrapper(client, collection_name)


def upsert_chunks(collection: QdrantCollectionWrapper, chunks: List[Chunk],
                  embeddings: List[List[float]]) -> None:
    points = [
        PointStruct(id=_point_id(c), vector=emb, payload={"_content": c.content, **c.metadata})
        for c, emb in zip(chunks, embeddings)
    ]
    collection.client.upsert(collection_name=collection.name, points=points)
    print(f"Upserted {len(points)} chunks into '{collection.name}'")


def load_collection(url: str, port: int, collection_name: str) -> QdrantCollectionWrapper:
    client = QdrantClient(url=url, port=port)
    if collection_name not in {c.name for c in client.get_collections().collections}:
        raise RuntimeError(f"Qdrant collection '{collection_name}' not found. Run the ingest script first.")
    return QdrantCollectionWrapper(client, collection_name)
