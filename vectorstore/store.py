from typing import List

import chromadb

from chunking.character_splitter import Chunk


def chunk_id(chunk: Chunk) -> str:
    return f"{chunk.metadata['doc_title']}_{chunk.metadata['chunk_index']}"


def get_or_create_collection(chroma_path: str, collection_name: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=chroma_path)
    return client.get_or_create_collection(name=collection_name)


def upsert_chunks(collection: chromadb.Collection, chunks: List[Chunk],
                  embeddings: List[List[float]]) -> None:
    # chroma doesn't accept None in metadata
    metadatas = [{k: ("" if v is None else v) for k, v in c.metadata.items()} for c in chunks]

    collection.upsert(
        ids=[chunk_id(c) for c in chunks],
        documents=[c.content for c in chunks],
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"Upserted {len(chunks)} chunks into '{collection.name}'")


def load_collection(chroma_path: str, collection_name: str) -> chromadb.Collection:
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        return client.get_collection(name=collection_name)
    except Exception:
        raise RuntimeError("Collection not found. Run demo/ingest.py first.")
