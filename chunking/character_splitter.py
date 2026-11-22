from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    content: str
    metadata: dict
    word_count: int
    has_code_block: bool
    has_table: bool


def make_chunk(content: str, metadata: dict) -> Chunk:
    return Chunk(
        content=content,
        metadata=metadata,
        word_count=len(content.split()),
        has_code_block="```" in content,
        has_table="|---|" in content,
    )


def split_by_characters(text: str, doc_title: str, chunk_size: int, overlap: int) -> List[Chunk]:
    """Fixed-size windows with overlap. Ignores sections, code blocks and tables."""
    chunks = []
    step = chunk_size - overlap

    for i, start in enumerate(range(0, len(text), step)):
        end = min(start + chunk_size, len(text))
        chunks.append(make_chunk(text[start:end], {
            "doc_title": doc_title,
            "chunk_index": i,
            "strategy": "character",
            "char_start": start,
            "char_end": end,
        }))

    return chunks
