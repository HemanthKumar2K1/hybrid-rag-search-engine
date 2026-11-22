"""
RAGAS scoring for the pipeline.

- faithfulness: is every claim in the answer backed by the retrieved chunks?
- answer_relevancy: does the answer address the question?
- context_precision: were the retrieved chunks the right ones? (needs ground_truth)

RAGAS uses an LLM as the judge, so OPENAI_API_KEY has to be set.
"""
from dataclasses import dataclass, field
from typing import Dict, List

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, context_precision, faithfulness

METRICS = [faithfulness, answer_relevancy, context_precision]


@dataclass
class RAGSample:
    question: str
    ground_truth: str = ""
    answer: str = ""
    contexts: List[str] = field(default_factory=list)


def evaluate_rag(samples: List[RAGSample]) -> Dict[str, float]:
    if not samples:
        raise ValueError("no samples to evaluate")

    dataset = Dataset.from_dict({
        "question": [s.question for s in samples],
        "answer": [s.answer for s in samples],
        "contexts": [s.contexts for s in samples],
        "ground_truth": [s.ground_truth for s in samples],
    })
    result = evaluate(dataset, metrics=METRICS)

    return {m.name: round(float(result[m.name]), 4) for m in METRICS}
