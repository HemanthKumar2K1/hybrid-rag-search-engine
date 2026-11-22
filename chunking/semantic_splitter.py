import re
from typing import List

from chunking.character_splitter import Chunk, make_chunk


def _heading(block: str) -> str:
    first = block.split("\n", 1)[0].strip()
    return first.lstrip("#").strip() if first.startswith("#") else ""


def split_by_headers(text: str, doc_title: str, max_words: int) -> List[Chunk]:
    """
    Split markdown at ## headers. Sections longer than max_words are split
    again at ### headers, so code blocks and tables stay inside their section.
    """
    chunks: List[Chunk] = []

    for section in re.split(r"\n(?=## )", text):
        if not section.strip():
            continue

        section_title = _heading(section) or section.split("\n", 1)[0].strip()

        if len(section.split()) > max_words:
            parts = re.split(r"\n(?=### )", section)
        else:
            parts = [section]

        for part in parts:
            content = part.strip()
            if not content:
                continue
            subsection = _heading(part) if len(parts) > 1 else ""
            chunks.append(make_chunk(content, {
                "doc_title": doc_title,
                "section_title": section_title,
                "subsection_title": subsection if subsection != section_title else "",
                "chunk_index": len(chunks),
                "strategy": "semantic",
                "word_count": len(content.split()),
            }))

    return chunks
