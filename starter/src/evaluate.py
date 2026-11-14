"""Run the frozen benchmark in dev-then-test order; save complete top-3 traces."""

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .store import LocalQdrantStore


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmark/questions.json"
POLICY = ROOT / "benchmark/selection_policy.json"
INGESTION = ROOT / "starter/results/ingestion_summary.json"
RESULTS = ROOT / "results"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_experiment_log(split: str, summary: dict) -> None:
    path = ROOT / "artifacts/experiment_log.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)
    if fieldnames is None:
        raise ValueError("Experiment log has no header")
    for row in rows:
        strategy = row["strategy"]
        row[f"{split}_hit1"] = f"{summary[strategy]['hit_at_1']['n']}/{summary[strategy]['hit_at_1']['N']}"
        row[f"{split}_hit3"] = f"{summary[strategy]['evidence_hit_at_3']['n']}/{summary[strategy]['evidence_hit_at_3']['N']}"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    args = parser.parse_args()
    split = args.split
    questions = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    chosen = [q for q in questions if q["split"] == split]
    if len(chosen) != (15 if split == "dev" else 5):
        raise ValueError(f"Unexpected {split} question count")
    ingestion = json.loads(INGESTION.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if not policy["locked_before_test"]:
        raise ValueError("Selection policy must be locked")
    selection_path = RESULTS / "strategy_selection.json"
    if split == "test":
        if not selection_path.exists():
            raise ValueError("Run --split dev and freeze strategy selection before test")
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        if selection["benchmark_sha256"] != digest(BENCHMARK) or selection["policy_sha256"] != digest(POLICY):
            raise ValueError("Benchmark or selection policy changed after dev selection")
        if selection["source_sha256"] != ingestion["source_sha256"]:
            raise ValueError("Ingestion corpus changed after dev selection")

    model = MyEmbedder(ingestion["model"])
    store = LocalQdrantStore(ROOT / ingestion["vector_store_path"], model.dimensions)
    try:
        counts = {name: store.count(name) for name in "ABC"}
        if counts != ingestion["chunk_counts"]:
            raise ValueError(f"Index counts changed: {counts}")
        traces = []
        started = time.perf_counter()
        for q in chosen:
            query_vector = model.embed_query(q["question"])
            for strategy in "ABC":
                filters = q.get("filter") if strategy == "C" else None
                hits = store.search(strategy, query_vector, top_k=3, filters=filters)
                if len(hits) != 3:
                    raise ValueError(f"Expected top-3 for {strategy}/{q['id']}, got {len(hits)}")
                traces.append(evaluate_query(q, hits, strategy))
        elapsed = round(time.perf_counter() - started, 2)
    finally:
        store.close()

    summary = {
        "split": split,
        "benchmark_sha256": digest(BENCHMARK),
        "source_sha256": ingestion["source_sha256"],
        "model": ingestion["model"],
        "scoring_method": "exact gold quote in one retrieved chunk on the gold source and page",
        "query_elapsed_seconds": elapsed,
        "api_cost_usd": 0,
        "strategies": summarize(traces),
    }
    if split == "test":
        summary["strategy_chosen_on_dev"] = selection["chosen_strategy"]
    write_json(RESULTS / f"{split}_traces.json", traces)
    write_json(RESULTS / f"{split}_summary.json", summary)
    if split == "dev":
        # This order is recorded in benchmark/selection_policy.json before test.
        ranked = sorted(
            "ABC",
            key=lambda s: (
                -summary["strategies"][s]["evidence_hit_at_3"]["n"],
                -summary["strategies"][s]["hit_at_1"]["n"],
                counts[s],
                s,
            ),
        )
        write_json(selection_path, {
            "chosen_strategy": ranked[0],
            "ranking": ranked,
            "basis": policy["priority"],
            "benchmark_sha256": digest(BENCHMARK),
            "policy_sha256": digest(POLICY),
            "source_sha256": ingestion["source_sha256"],
            "dev_summary_path": "results/dev_summary.json",
        })
    update_experiment_log(split, summary["strategies"])
    print(f"{split}: {len(chosen)} questions x 3 strategies; {elapsed}s")
    for strategy, data in summary["strategies"].items():
        print(f"{strategy}: Hit@1 {data['hit_at_1']['n']}/{data['hit_at_1']['N']}; Evidence Hit@3 {data['evidence_hit_at_3']['n']}/{data['evidence_hit_at_3']['N']}")
    if split == "dev":
        print(f"Selected on dev: {ranked[0]} (ranking: {', '.join(ranked)})")
    else:
        print(f"Dev-selected strategy remains: {selection['chosen_strategy']}")


if __name__ == "__main__":
    main()
