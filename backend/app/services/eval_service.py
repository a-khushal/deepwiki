import json
from typing import Any

from openai import OpenAI
from app.config import settings


def compute_hit_rate(results: list[list[str]], expected: list[list[str]], k: int = 5) -> float:
    """Hit Rate @ K: fraction of queries where at least one expected file appears in top-K."""
    hits = 0
    for result_files, expected_files in zip(results, expected):
        top_k = result_files[:k]
        if any(ef in top_k for ef in expected_files):
            hits += 1
    return hits / len(results) if results else 0.0


def compute_mrr(results: list[list[str]], expected: list[list[str]]) -> float:
    """Mean Reciprocal Rank: average of 1/rank of first relevant result."""
    reciprocal_ranks = []
    for result_files, expected_files in zip(results, expected):
        rank = None
        for i, f in enumerate(result_files, 1):
            if f in expected_files:
                rank = i
                break
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
    return sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0


def compute_precision(results: list[list[str]], expected: list[list[str]], k: int = 5) -> float:
    """Precision @ K: fraction of retrieved top-K results that are relevant."""
    precisions = []
    for result_files, expected_files in zip(results, expected):
        top_k = result_files[:k]
        if not top_k:
            precisions.append(0.0)
            continue
        relevant = sum(1 for f in top_k if f in expected_files)
        precisions.append(relevant / len(top_k))
    return sum(precisions) / len(precisions) if precisions else 0.0


def llm_judge_correctness(question: str, answer: str, expected_answer_contains: str) -> float:
    """Use LLM-as-judge to rate answer correctness on 1-5 scale."""
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are evaluating a RAG system's answer. "
                        "Rate the answer on a scale of 1-5 for correctness.\n\n"
                        "1 = Completely wrong or irrelevant\n"
                        "2 = Partially correct but misses key information\n"
                        "3 = Correct but vague or incomplete\n"
                        "4 = Correct with good detail\n"
                        "5 = Correct, detailed, with proper citations\n\n"
                        f"The answer SHOULD mention or reference: '{expected_answer_contains}'\n\n"
                        "Return ONLY a number (1-5)."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nAnswer: {answer}",
                },
            ],
            temperature=0.1,
            max_tokens=5,
        )
        score = int(response.choices[0].message.content.strip())
        return max(1.0, min(5.0, float(score)))
    except Exception:
        if expected_answer_contains.lower() in answer.lower():
            return 4.0
        return 1.0


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """Pretty-print eval metrics as a table."""
    lines = [
        "┌──────────────────────────────────┬──────────┐",
        "│ Metric                           │   Score  │",
        "├──────────────────────────────────┼──────────┤",
    ]
    for key, val in metrics.items():
        if isinstance(val, float):
            lines.append(f"│ {key:<32s} │   {val:.3f}  │")
        else:
            lines.append(f"│ {key:<32s} │   {str(val):<6s}  │")
    lines.append("└──────────────────────────────────┴──────────┘")
    return "\n".join(lines)
