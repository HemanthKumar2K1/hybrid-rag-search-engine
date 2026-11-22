from dataclasses import dataclass
from typing import List

from retrieval.semantic_search import RetrievedChunk

SYSTEM_PROMPT = """You are a documentation assistant. Answer ONLY using the provided document chunks.

If the answer is not in the chunks, reply:
'I could not find an answer to this question in the provided documentation.'

Do not use outside knowledge. Cite every claim as:
[Source: <doc_title>, Section: <section_title>]"""


@dataclass
class PromptMessages:
    system: str
    user: str


def build_prompt(query: str, chunks: List[RetrievedChunk]) -> PromptMessages:
    parts = ["--- Retrieved Documentation ---\n"]
    for c in chunks:
        doc = c.metadata.get("doc_title", "Unknown")
        section = c.metadata.get("section_title", "Unknown")
        parts += [f"[Chunk {c.rank} - {doc} | {section}]", c.content, ""]
    parts += ["---", f"Question: {query}"]

    return PromptMessages(system=SYSTEM_PROMPT, user="\n".join(parts))
