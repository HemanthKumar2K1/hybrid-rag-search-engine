from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from chunking.character_splitter import Chunk


@lru_cache(maxsize=None)
def load_embedding_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_chunks(chunks: List[Chunk], model: SentenceTransformer) -> List[List[float]]:
    print(f"Embedding {len(chunks)} chunks...")
    embeddings = model.encode([c.content for c in chunks], show_progress_bar=False)
    return [e.tolist() for e in embeddings]
