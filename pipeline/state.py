from typing import List, Optional

from typing_extensions import TypedDict

from generation.answer_generator import Answer
from generation.prompt_builder import PromptMessages
from retrieval.semantic_search import RetrievedChunk


class RAGState(TypedDict):
    query: str
    retrieved_chunks: List[RetrievedChunk]
    prompt: Optional[PromptMessages]
    answer: Optional[Answer]
    error: str  # set by any node that fails; graph stops early
