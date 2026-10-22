"""Compare live index-assisted MongoDB queries with forced collection scans.

This is a read-only alternative when the historical pre-indexing report is lost.
It does not claim to reconstruct performance before index creation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys


# allow imports from the Milestone Four project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

# use the same database configuration as the working dashboard
load_dotenv(PROJECT_ROOT / ".env")

from CRUD_Python_Module import AnimalShelter
from benchmarks.benchmark_database import QUERY_CASES, TABLE_PROJECTION
from benchmarks.report_database_performance import plan_label

RESULTS_DIRECTORY = Path(__file__).resolve().parent / "results"
TRIALS_PER_CONDITION = 3


# measure one actual MongoDB query without reading animal documents into Python
def explain_query(collection, query, sort_field, force_scan=False):
    cursor = (
        collection.find(query, TABLE_PROJECTION)
        .sort([(sort_field, 1), ("_id", 1)])
        .limit(8)
    )
    if force_scan:
        # a $natural hint requests a collection scan instead of an indexed access path
        cursor = cursor.hint([("$natural", 1)])
    explanation = cursor.explain()
    statistics_data = explanation.get("executionStats", {})
    planner = explanation.get("queryPlanner", {})
    return {
        "nReturned": statistics_data.get("nReturned"),
        "executionTimeMillis": statistics_data.get("executionTimeMillis"),
        "totalDocsExamined": statistics_data.get("totalDocsExamined"),
        "totalKeysExamined": statistics_data.get("totalKeysExamined"),
        "plan": plan_label({"winningPlan": planner.get("winningPlan", {})}),
    }


# use repeated measurements to reduce the impact of single-run timing variation
def measure_condition(collection, query, sort_field, force_scan=False, trials=TRIALS_PER_CONDITION):
    readings = [
        explain_query(collection, query, sort_field, force_scan)
        for _ in range(trials)
    ]
    output = {"trials": trials, "plan": readings[-1]["plan"]}
    for key in ("nReturned", "executionTimeMillis", "totalDocsExamined", "totalKeysExamined"):
        numbers = [value[key] for value in readings if isinstance(value.get(key), (int, float))]
        output[key] = statistics.median(numbers) if numbers else None
    return output


# measure the same dashboard queries with normal planning and a forced scan
def benchmark_collection(collection, trials=TRIALS_PER_CONDITION):
    results = {}
    for name, query, sort_field in QUERY_CASES:
        try:
            # execute both variants against the same existing indexed collection
            indexed = measure_condition(collection, query, sort_field, trials=trials)
            scan = measure_condition(collection, query, sort_field, True, trials=trials)
            results[name] = {"planner_selected": indexed, "forced_collection_scan": scan}
        except Exception as exc:
            # record only the exception class to avoid exposing connection details
            results[name] = {"error": type(exc).__name__}
    return results


def display_number(value):
    if value is None:
        return "n/a"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return "n/a"


def reduction_percentage(scan_value, indexed_value):
    if not isinstance(scan_value, (int, float)) or scan_value <= 0:
        return "n/a"
    if not isinstance(indexed_value, (int, float)):
        return "n/a"
    return f"{(scan_value - indexed_value) * 100 / scan_value:+.1f}%"


# produce a report that explicitly distinguishes this comparison from a historic baseline
def build_markdown_report(report):
    lines = [
        "# MongoDB Current Index vs. Collection Scan Comparison",
        "",
        f"Captured (UTC): {report['captured_at_utc']}",
        f"Database: `{report['database']}.{report['collection']}`  ",
        f"Documents: {display_number(report['document_count'])}  ",
        f"Explain trials per condition: {report['trials_per_condition']}",
        "",
        "## Methodology",
        "",
        "The same queries were tested on the current database in two ways: (1) using MongoDB's normal query planner, which may select an index, and (2) using a `$natural` hint to force a collection scan. These measurements do **not** represent historical performance before indexes were created.",
        "",
        "## Results",
        "",
        "| Query | Normal plan | Forced scan plan | Normal time (ms) | Scan time (ms) | Normal docs examined | Scan docs examined | Docs reduction |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for name, comparison in report["results"].items():
        if "error" in comparison:
            lines.append(f"| {name} | Error: {comparison['error']} | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        normal = comparison["planner_selected"]
        scan = comparison["forced_collection_scan"]
        lines.append("| " + " | ".join((
            name,
            normal["plan"].replace("|", "/"),
            scan["plan"].replace("|", "/"),
            display_number(normal["executionTimeMillis"]),
            display_number(scan["executionTimeMillis"]),
            display_number(normal["totalDocsExamined"]),
            display_number(scan["totalDocsExamined"]),
            reduction_percentage(scan["totalDocsExamined"], normal["totalDocsExamined"]),
        )) + " |")
    lines += [
        "",
        "## Interpretation and limitations",
        "",
        "- A normal query plan is not guaranteed to use an index; inspect the plan name in the table.",
        "- A forced scan provides a controlled non-indexed comparison on the current database, **not** an original before-indexing measurement.",
        "- `executionTimeMillis` is coarse; cache effects and server activity may affect timings. Documents and keys examined can be more informative.",
        "- If `nReturned` is zero, the query did not match any records in that sample; interpret its timing cautiously.",
        "- Case-insensitive substring searches may be unable to use ordinary B-tree indexes efficiently.",
        "- Indexes add storage and incur maintenance work when documents are inserted or updated.",
        "- The original Step 3 `index_comparison.json` is still required to claim a historical before-and-after result. It is not recreated by this script.",
        "",
        "## Capstone documentation",
        "",
        "Describe these findings as a controlled comparison of current query plans against forced collection scans. Do not describe the scan times as measurements captured before the indexes were installed.",
        "",
    ]
    return "\n".join(lines)


# write benchmark results locally without modifying the MongoDB collection
def main():
    shelter = AnimalShelter()
    try:
        shelter.client.admin.command("ping")
        collection = shelter.collection
        print(f"Connected to: {collection.database.name}.{collection.name}")
        print("Benchmark mode: READ ONLY. Existing indexes and animal records will not change.")
        result = {
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "database": collection.database.name,
            "collection": collection.name,
            "document_count": collection.count_documents({}),
            "trials_per_condition": TRIALS_PER_CONDITION,
            "comparison_type": "current_planner_vs_forced_collection_scan",
            "results": benchmark_collection(collection),
        }
        RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        json_path = RESULTS_DIRECTORY / "index_vs_scan.json"
        markdown_path = RESULTS_DIRECTORY / "index_vs_scan_report.md"
        json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        markdown_path.write_text(build_markdown_report(result), encoding="utf-8")
        print("Measurements saved:", json_path)
        print("Readable report saved:", markdown_path)
        errors = {name: info['error'] for name, info in result['results'].items() if 'error' in info}
        if errors:
            print("Some query plans could not be captured:", errors)
    finally:
        shelter.client.close()


if __name__ == "__main__":
    main()
