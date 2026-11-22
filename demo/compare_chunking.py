"""
Compare fixed-size character chunks vs header-based chunks on one document.

    python demo/compare_chunking.py [docs/ZohoCRM_API.md]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chunking.comparison import ComparisonResult, compare_strategies, has_broken_code

WIDTH = 67
DEFAULT_DOC = "docs/ZohoCRM_API.md"


def print_stats(result: ComparisonResult) -> None:
    cs, ss = result.char_stats, result.semantic_stats
    print(f"\nDocument: {result.doc_title}")
    print("-" * WIDTH)
    print(f"{'':24}{'Character (500)':<22}{'Header-based'}")
    print("-" * WIDTH)
    for label, key in [("Total chunks", "total_chunks"),
                       ("Avg words/chunk", "avg_words"),
                       ("Broken code blocks", "broken_code_blocks"),
                       ("Broken tables", "broken_tables")]:
        print(f"{label:<24}{str(cs[key]):<22}{ss[key]}")
    print("-" * WIDTH)


def print_examples(result: ComparisonResult) -> None:
    print("\nCharacter splitter - chunks that end in the middle of code:")
    print("-" * WIDTH)
    for c in [c for c in result.char_chunks if has_broken_code(c)][:2]:
        print(f"[chunk {c.metadata['chunk_index']} | {len(c.content)} chars | BROKEN CODE BLOCK]")
        print("..." + c.content[-200:] + "  <-- cut here\n")

    print("\nHeader-based splitter - first few chunks:")
    print("-" * WIDTH)
    for c in result.semantic_chunks[:3]:
        title = c.metadata["subsection_title"] or c.metadata["section_title"]
        notes = ["code intact" if c.has_code_block else "no code"]
        if c.has_table:
            notes.append("table intact")
        print(f"[{title} | {c.word_count} words | {', '.join(notes)}]")
        print(c.content[:200] + ("..." if len(c.content) > 200 else "") + "\n")


def main() -> None:
    result = compare_strategies(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DOC)
    print_stats(result)
    print_examples(result)


if __name__ == "__main__":
    main()
