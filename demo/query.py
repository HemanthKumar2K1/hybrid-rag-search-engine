"""
Ask a question against the ingested docs.

    python demo/query.py "How do I refresh an expired Zoho CRM access token?"
    python demo/query.py "..." --retrieval-only   # skip the LLM call
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.graph import run_query
from pipeline.nodes import rerank_node, retrieve_node


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print('Usage: python demo/query.py "<question>" [--retrieval-only]')
        sys.exit(1)
    question = args[0]

    if "--retrieval-only" in sys.argv:
        state = {"query": question}
        state.update(retrieve_node(state))
        if not state.get("error"):
            state.update(rerank_node(state))
        if state.get("error"):
            sys.exit(state["error"])
        return

    answer = run_query(question)

    print(f"\n{'=' * 60}\nAnswer\n{'=' * 60}")
    print(answer.text)
    print(f"\nCitations ({len(answer.citations)}):")
    for c in answer.citations or ["none"]:
        print(f"  {c}")


if __name__ == "__main__":
    main()
