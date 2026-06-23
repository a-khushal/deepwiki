#!/usr/bin/env python3
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parser_service import ParserService
from app.services.chunker_service import ChunkerService
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.rag_service import RagService
from app.services.eval_service import (
    compute_hit_rate,
    compute_mrr,
    compute_precision,
    llm_judge_correctness,
    format_metrics_table,
)

DATASETS_DIR = Path(__file__).parent / "datasets"
RESULTS_DIR = Path(__file__).parent / "results"

parser_service = ParserService()
chunker_service = ChunkerService()
embedding_service = EmbeddingService()
vector_service = VectorService()
rag_service = RagService()


def load_datasets() -> list[dict]:
    datasets = []
    for f in sorted(DATASETS_DIR.glob("*.json")):
        data = json.loads(f.read_text())
        datasets.append(data)
        print(f"  Loaded: {data['repo_id']} ({len(data['questions'])} questions)")
    return datasets


def write_dataset_files(repo_id: str, files: dict[str, str]) -> str:
    tmp_dir = tempfile.mkdtemp(prefix=f"eval_{repo_id}_")
    for file_path, content in files.items():
        full_path = Path(tmp_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    return tmp_dir


def run_eval() -> dict:
    datasets = load_datasets()
    print(f"\nLoaded {len(datasets)} datasets\n")

    all_hit_rates = []
    all_mrrs = []
    all_precisions = []
    all_correctness = []

    for dataset in datasets:
        repo_id = dataset["repo_id"]
        print(f"{'='*50}")
        print(f"  Evaluating: {repo_id} ({dataset['description']})")
        print(f"{'='*50}")

        tmp_dir = write_dataset_files(repo_id, dataset["files"])
        print(f"  Wrote {len(dataset['files'])} files to {tmp_dir}")

        try:
            parsed = parser_service.parse_repo(tmp_dir)
            print(f"  Parsed: {len(parsed)} files")

            chunks = chunker_service.chunk_parsed_files(parsed, repo_id)
            print(f"  Chunked: {len(chunks)} chunks")

            texts = [c.content for c in chunks]
            embeddings = embedding_service.embed(texts)
            print(f"  Embedded: {len(embeddings)} vectors")

            vector_service.delete_collection(repo_id)
            vector_service.store_chunks(repo_id, chunks, embeddings)
            print(f"  Stored in vector DB")

            for q in dataset["questions"]:
                print(f"\n    Q: {q['question'][:80]}")

                question_emb = embedding_service.embed_query(q["question"])
                search_results = vector_service.query(repo_id, question_emb, top_k=10)

                retrieved_files = [r.chunk.file_path for r in search_results]
                expected_files = q["expected_files"]

                hit = 1.0 if any(ef in retrieved_files[:5] for ef in expected_files) else 0.0
                rank = None
                for i, f in enumerate(retrieved_files, 1):
                    if f in expected_files:
                        rank = i
                        break
                mrr_val = 1.0 / rank if rank else 0.0
                relevant_count = sum(1 for f in retrieved_files[:5] if f in expected_files)
                precision = relevant_count / 5.0

                all_hit_rates.append(hit)
                all_mrrs.append(mrr_val)
                all_precisions.append(precision)

                print(f"      Hit@5: {hit:.1f}, MRR: {mrr_val:.3f}, P@5: {precision:.3f}")
                if rank:
                    print(f"      First relevant at rank {rank}: {retrieved_files[rank-1]}")

                try:
                    rag_result = rag_service.answer(repo_id, q["question"])
                    correctness = llm_judge_correctness(
                        q["question"], rag_result.answer, q.get("expected_answer_contains", "")
                    )
                    all_correctness.append(correctness)
                    print(f"      Answer correctness: {correctness:.1f}/5.0")
                except Exception as e:
                    print(f"      Answer correctness: skipped ({str(e)[:50]})")

            vector_service.delete_collection(repo_id)

        except Exception as e:
            print(f"  ERROR: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        print()

    metrics = {
        "Hit Rate @ 5": sum(all_hit_rates) / len(all_hit_rates) if all_hit_rates else 0.0,
        "Mean Reciprocal Rank (MRR)": sum(all_mrrs) / len(all_mrrs) if all_mrrs else 0.0,
        "Precision @ 5": sum(all_precisions) / len(all_precisions) if all_precisions else 0.0,
        "Answer Correctness": sum(all_correctness) / len(all_correctness) if all_correctness else 0.0,
        "Total Questions": len(all_hit_rates),
    }

    return metrics


def main():
    print("DeepWiki RAG Evaluation Suite")
    print(f"{'='*50}")
    print(f"Datasets directory: {DATASETS_DIR}")
    print(f"Results directory: {RESULTS_DIR}")
    print()

    start = time.time()
    metrics = run_eval()
    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print(f"  RESULTS")
    print(f"{'='*50}")
    print()
    print(format_metrics_table(metrics))
    print(f"\n  Time: {elapsed:.1f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = RESULTS_DIR / f"eval_{timestamp}.json"
    result_data = {
        "timestamp": timestamp,
        "elapsed_seconds": round(elapsed, 1),
        "metrics": metrics,
    }
    result_file.write_text(json.dumps(result_data, indent=2))
    print(f"\n  Saved: {result_file}")


if __name__ == "__main__":
    main()
