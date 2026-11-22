"""
Run a fixed question set through the pipeline and score it with RAGAS.
Needs the docs ingested and OPENAI_API_KEY set.

    python demo/evaluate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.ragas_eval import RAGSample, evaluate_rag
from pipeline.graph import run_query_with_chunks

EVAL_SET = [
    RAGSample(
        question="How do I refresh an expired Zoho CRM access token?",
        ground_truth="Send a POST request to https://accounts.zoho.com/oauth/v2/token with "
                     "grant_type=refresh_token, client_id, client_secret, and the refresh_token "
                     "to receive a new access token.",
    ),
    RAGSample(
        question="What COQL query fetches deals closing this quarter above 50000?",
        ground_truth="SELECT Deal_Name, Stage, Amount, Closing_Date FROM Deals "
                     "WHERE Closing_Date >= '2026-04-01' AND Amount > 50000 ORDER BY Amount DESC.",
    ),
    RAGSample(
        question="How do I identify a logged-in user to the SalesIQ chat widget?",
        ground_truth="Call $zoho.salesiq.visitor.name(), .email(), and .info() after the user "
                     "authenticates to attach their identity and custom context to the chat.",
    ),
    RAGSample(
        question="What webhook event fires when a visitor submits a CSAT rating in SalesIQ?",
        ground_truth="The chat.rated event is triggered when a visitor submits a CSAT rating.",
    ),
    RAGSample(
        question="What is the per-minute API rate limit on the Zoho CRM Enterprise plan?",
        ground_truth="The Zoho CRM Enterprise plan allows 500 requests per minute.",
    ),
    # not answerable from one chunk - checks the model doesn't make things up
    RAGSample(
        question="Does Zoho CRM support joining multiple modules in a single COQL query?",
        ground_truth="JOINs across modules are not supported in COQL. Related records must be "
                     "fetched separately using the related records API.",
    ),
]


def main() -> None:
    samples = []
    for sample in EVAL_SET:
        print(f"\nQ: {sample.question}")
        try:
            answer, chunks = run_query_with_chunks(sample.question)
        except RuntimeError as e:
            print(f"  error: {e}")
            continue
        sample.answer = answer.text
        sample.contexts = [c.content for c in chunks]
        print(f"A: {answer.text[:140].strip()}...")
        samples.append(sample)

    if not samples:
        sys.exit("No answers to score. Did you run demo/ingest.py?")

    print("\nScoring with RAGAS...")
    scores = evaluate_rag(samples)

    print(f"\n{'-' * 40}")
    for metric, score in scores.items():
        print(f"  {metric:<20} {score:.3f}  {'#' * int(score * 20)}")
    print(f"{'-' * 40}\n  {len(samples)} samples")


if __name__ == "__main__":
    main()
