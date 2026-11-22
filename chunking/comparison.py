import os
from dataclasses import dataclass
from typing import List

from chunking.character_splitter import Chunk, split_by_characters
from chunking.semantic_splitter import split_by_headers
from config.settings import CHAR_CHUNK_OVERLAP, CHAR_CHUNK_SIZE, SEMANTIC_MAX_WORDS


@dataclass
class ComparisonResult:
    doc_title: str
    char_chunks: List[Chunk]
    semantic_chunks: List[Chunk]
    char_stats: dict
    semantic_stats: dict


def has_broken_code(chunk: Chunk) -> bool:
    # an odd number of ``` fences means a code block was cut in half
    return chunk.content.count("```") % 2 != 0


def _has_broken_table(chunk: Chunk) -> bool:
    table_lines = [line for line in chunk.content.split("\n") if "|" in line]
    return chunk.has_table and len(table_lines) < 2


def _stats(chunks: List[Chunk]) -> dict:
    total = len(chunks)
    return {
        "total_chunks": total,
        "avg_words": round(sum(c.word_count for c in chunks) / total, 1) if total else 0.0,
        "broken_code_blocks": sum(has_broken_code(c) for c in chunks),
        "broken_tables": sum(_has_broken_table(c) for c in chunks),
    }


def compare_strategies(doc_path: str) -> ComparisonResult:
    doc_title = os.path.basename(doc_path)
    with open(doc_path, encoding="utf-8") as f:
        text = f.read()

    char_chunks = split_by_characters(text, doc_title, CHAR_CHUNK_SIZE, CHAR_CHUNK_OVERLAP)
    semantic_chunks = split_by_headers(text, doc_title, SEMANTIC_MAX_WORDS)

    return ComparisonResult(
        doc_title=doc_title,
        char_chunks=char_chunks,
        semantic_chunks=semantic_chunks,
        char_stats=_stats(char_chunks),
        semantic_stats=_stats(semantic_chunks),
    )
