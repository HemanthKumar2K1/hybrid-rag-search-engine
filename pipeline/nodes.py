import os
from functools import lru_cache

from sentence_transformers import CrossEncoder

from config.settings import (
    BM25_INDEX_PATH,
    CHROMA_PATH,
    COLLECTION_NAME,
    EMBED_MODEL,
    RERANKER_MODEL,
    RERANKER_TOP_K,
    TOP_K,
)
from generation.answer_generator import generate
from generation.prompt_builder import build_prompt
from pipeline.state import RAGState
from retrieval.hybrid_search import load_bm25_index, search
from retrieval.semantic_search import RetrievedChunk
from vectorstore.embedder import load_embedding_model
from vectorstore.store import load_collection


@lru_cache(maxsize=1)
def _reranker() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL)


# Each node returns only the keys it changes. Errors are put in state
# instead of raised so the graph can route to END.

def retrieve_node(state: RAGState) -> dict:
    try:
        collection = load_collection(CHROMA_PATH, COLLECTION_NAME)
        model = load_embedding_model(EMBED_MODEL)
        bm25_index = load_bm25_index(BM25_INDEX_PATH) if os.path.exists(BM25_INDEX_PATH) else None
        return {"retrieved_chunks": search(state["query"], collection, model, TOP_K, bm25_index)}
    except Exception as e:
        return {"error": f"Retrieval failed: {e}"}


def rerank_node(state: RAGState) -> dict:
    # The cross-encoder sees query and chunk together, so it scores relevance
    # better than the bi-encoder used for retrieval. Too slow to run on the
    # whole corpus, fine on the top-k.
    try:
        chunks = state["retrieved_chunks"]
        scores = _reranker().predict([(state["query"], c.content) for c in chunks])
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)[:RERANKER_TOP_K]

        reranked = [
            RetrievedChunk(content=c.content, metadata=c.metadata, score=float(s), rank=i + 1)
            for i, (s, c) in enumerate(ranked)
        ]

        print(f"\n{'-' * 60}\nReranked (top {RERANKER_TOP_K})\n{'-' * 60}")
        for c in reranked:
            print(f"  #{c.rank}  score={c.score:<8.4f} "
                  f"[{c.metadata.get('doc_title', '?')} | {c.metadata.get('section_title', '?')}]")

        return {"retrieved_chunks": reranked}
    except Exception as e:
        return {"error": f"Reranking failed: {e}"}


def build_prompt_node(state: RAGState) -> dict:
    try:
        return {"prompt": build_prompt(state["query"], state["retrieved_chunks"])}
    except Exception as e:
        return {"error": f"Prompt build failed: {e}"}


def generate_node(state: RAGState) -> dict:
    try:
        return {"answer": generate(state["prompt"], state["query"], len(state["retrieved_chunks"]))}
    except Exception as e:
        return {"error": f"Generation failed: {e}"}
