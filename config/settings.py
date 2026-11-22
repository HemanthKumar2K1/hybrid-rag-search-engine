DOCS_PATH = "docs"
CHROMA_PATH = "chroma_data"
COLLECTION_NAME = "rag_docs"

# changing the model means deleting chroma_data/ and re-ingesting
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384

CHAR_CHUNK_SIZE = 500
CHAR_CHUNK_OVERLAP = 50
SEMANTIC_MAX_WORDS = 400  # bigger H2 sections get split at H3

TOP_K = 5
BM25_INDEX_PATH = "chroma_data/bm25_index.pkl"

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_TOP_K = 3

QDRANT_URL = "http://localhost"
QDRANT_PORT = 6333
