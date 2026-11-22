"""
Convert a PDF to markdown and drop it into docs/ so the normal ingest
script picks it up.

    python ingestion/pdf_loader.py path/to/file.pdf
"""
import os
import sys


def pdf_to_markdown(pdf_path: str, output_dir: str = "docs") -> str:
    import pymupdf4llm  # optional dependency, only needed here

    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    md_text = pymupdf4llm.to_markdown(pdf_path)

    name = os.path.splitext(os.path.basename(pdf_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{name}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"Wrote {output_path} ({len(md_text):,} chars)")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingestion/pdf_loader.py <file.pdf> [output_dir]")
        sys.exit(1)
    pdf_to_markdown(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "docs")
