from functools import lru_cache
from typing import List, Tuple

from langgraph.graph import END, START, StateGraph

from generation.answer_generator import Answer
from pipeline.nodes import build_prompt_node, generate_node, rerank_node, retrieve_node
from pipeline.state import RAGState
from retrieval.semantic_search import RetrievedChunk


def _stop_on_error(next_node: str):
    return lambda state: END if state.get("error") else next_node


@lru_cache(maxsize=1)
def build_rag_graph():
    # retrieve -> rerank -> build_prompt -> generate
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("build_prompt", build_prompt_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", _stop_on_error("rerank"))
    graph.add_conditional_edges("rerank", _stop_on_error("build_prompt"))
    graph.add_edge("build_prompt", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


def run_query_with_chunks(query: str) -> Tuple[Answer, List[RetrievedChunk]]:
    state = build_rag_graph().invoke({
        "query": query,
        "retrieved_chunks": [],
        "prompt": None,
        "answer": None,
        "error": "",
    })
    if state.get("error"):
        raise RuntimeError(state["error"])
    return state["answer"], state["retrieved_chunks"]


def run_query(query: str) -> Answer:
    return run_query_with_chunks(query)[0]
