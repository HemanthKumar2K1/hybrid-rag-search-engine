"""
Chunk every markdown file in docs/ by headers, embed, store in Chroma and
save the BM25 index.

    python demo/ingest.py
    python demo/ingest.py --char    # fixed-size chunks instead, for comparison
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunking.character_splitter import split_by_characters
from chunking.semantic_splitter import split_by_headers
from config.settings import (
    BM25_INDEX_PATH,
    CHAR_CHUNK_OVERLAP,
    CHAR_CHUNK_SIZE,
    CHROMA_PATH,
    COLLECTION_NAME,
    DOCS_PATH,
    EMBED_MODEL,
    SEMANTIC_MAX_WORDS,
)
from retrieval.hybrid_search import save_bm25_index
from vectorstore.embedder import embed_chunks, load_embedding_model
from vectorstore.store import get_or_create_collection, upsert_chunks


def chunk_file(path: str, use_char: bool):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    title = os.path.basename(path)
    if use_char:
        return split_by_characters(text, title, CHAR_CHUNK_SIZE, CHAR_CHUNK_OVERLAP)
    return split_by_headers(text, title, SEMANTIC_MAX_WORDS)


def main() -> None:
    use_char = "--char" in sys.argv
    files = sorted(os.path.join(DOCS_PATH, f) for f in os.listdir(DOCS_PATH) if f.endswith(".md"))

    chunks = []
    for path in files:
        file_chunks = chunk_file(path, use_char)
        print(f"{os.path.basename(path)}: {len(file_chunks)} chunks")
        chunks.extend(file_chunks)

    model = load_embedding_model(EMBED_MODEL)
    embeddings = embed_chunks(chunks, model)

    collection = get_or_create_collection(CHROMA_PATH, COLLECTION_NAME)
    upsert_chunks(collection, chunks, embeddings)
    save_bm25_index(BM25_INDEX_PATH, collection)

    print(f"\nDone: {len(files)} docs, {len(chunks)} chunks -> ./{CHROMA_PATH}")


if __name__ == "__main__":
    main()
