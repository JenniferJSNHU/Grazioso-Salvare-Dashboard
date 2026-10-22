"""Summarize saved before-and-after MongoDB query plans without touching the database."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


# store reports beside the existing database benchmark script
RESULTS_FOLDER = Path(__file__).resolve().parent / "results"
DEFAULT_INPUT = RESULTS_FOLDER / "index_comparison.json"
DEFAULT_OUTPUT = RESULTS_FOLDER / "index_performance_report.md"


# display numeric results without implying that missing measurements are zero

def format_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "n/a"
    return f"{value:,.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else f"{value:,}"


# inspect nested query plan stages from classic and SBE explain formats

def find_plan_stages(plan):
    stages = set()
    indexes = set()

    def visit(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("stage", "nodeType") and isinstance(value, str):
                    stages.add(value.upper())
                elif key == "indexName" and isinstance(value, str):
                    indexes.add(value)
                elif key == "stages" and isinstance(value, str):
                    if "ixseek" in value.lower():
                        stages.add("IXSEEK")
                    if "scan" in value.lower():
                        stages.add("SCAN")
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(plan)
    return stages, indexes


# identify index scans and collection scans in the explain plan

def plan_label(result):
    stages, indexes = find_plan_stages(result.get("winningPlan", {}))
    if indexes:
        return "Index: " + ", ".join(sorted(indexes))
    if "IXSCAN" in stages or "IXSEEK" in stages:
        return "Index scan"
    if "COLLSCAN" in stages or "SCAN" in stages:
        return "Collection scan"
    if stages:
        return ", ".join(sorted(stages))
    return "Not available"


# calculate the relative reduction only when a valid baseline is available

def reduction(before, after):
    if (isinstance(before, bool) or isinstance(after, bool)
            or not isinstance(before, (int, float))
            or not isinstance(after, (int, float)) or before <= 0):
        return "n/a"
    percent = (before - after) * 100 / before
    return f"{percent:+.1f}% reduction" if percent >= 0 else f"{abs(percent):.1f}% increase"


# produce a reproducible report from actual database measurements

def generate_report(data):
    if not isinstance(data, dict):
        raise ValueError("The benchmark data must be a JSON object.")
    before = data.get("queries_before")
    after = data.get("queries_after")
    if not isinstance(before, dict) or not isinstance(after, dict) or not before or not after:
        raise ValueError("The JSON must include nonempty queries_before and queries_after objects.")

    database = str(data.get("database", "unknown"))
    collection = str(data.get("collection", "unknown"))
    old_indexes = data.get("indexes_before", [])
    new_indexes = data.get("indexes_after", [])
    if not isinstance(old_indexes, list) or not isinstance(new_indexes, list):
        raise ValueError("Index inventories must be arrays.")
    added = sorted(set(new_indexes) - set(old_indexes))
    warnings = []
    if not added:
        warnings.append("No new indexes appear between the before and after snapshots. This file cannot establish the effect of adding indexes; use the original setup report, not a rerun.")

    lines = [
        "# MongoDB Index Performance Comparison",
        "",
        f"Source report captured: {data.get('captured_at_utc', 'not recorded')}",
        f"Database: `{database}.{collection}`  ",
        f"Collection size at capture: {format_number(data.get('document_count'))} documents",
        "",
        "## Index inventory",
        "",
        f"Before: {', '.join('`'+x+'`' for x in old_indexes) or 'Not recorded'}  ",
        f"After: {', '.join('`'+x+'`' for x in new_indexes) or 'Not recorded'}  ",
        f"Newly added: {', '.join('`'+x+'`' for x in added) or 'None'}",
        "",
        "## Query execution statistics",
        "",
        "| Query | Time before (ms) | Time after (ms) | Docs examined before | Docs examined after | Keys examined before | Keys examined after | Plan before → after |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for name in dict.fromkeys([*before.keys(), *after.keys()]):
        old = before.get(name)
        new = after.get(name)
        if not isinstance(old, dict) or not isinstance(new, dict):
            warnings.append(f"{name}: one measurement is missing.")
            continue
        if "error" in old or "error" in new:
            warnings.append(f"{name}: at least one query failed (before: {old.get('error', 'none')}; after: {new.get('error', 'none')}).")
            continue
        old_count = old.get("nReturned")
        new_count = new.get("nReturned")
        if old_count is not None and new_count is not None and old_count != new_count:
            warnings.append(f"{name}: different result counts ({old_count} before, {new_count} after) make this comparison unreliable.")
        values = [
            name,
            format_number(old.get("executionTimeMillis")),
            format_number(new.get("executionTimeMillis")),
            format_number(old.get("totalDocsExamined")),
            format_number(new.get("totalDocsExamined")),
            format_number(old.get("totalKeysExamined")),
            format_number(new.get("totalKeysExamined")),
            f"{plan_label(old)} → {plan_label(new)}",
        ]
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in values) + " |")

    lines += [
        "",
        "## Relative changes by query",
        "",
        "Positive reductions below indicate fewer documents examined or lower reported execution time.",
        "",
        "| Query | Execution-time change | Documents-examined change |",
        "|---|---|---|",
    ]
    for name in dict.fromkeys([*before.keys(), *after.keys()]):
        old = before.get(name, {})
        new = after.get(name, {})
        if not isinstance(old, dict) or not isinstance(new, dict) or "error" in old or "error" in new:
            continue
        lines.append(
            f"| {name} | {reduction(old.get('executionTimeMillis'), new.get('executionTimeMillis'))} "
            f"| {reduction(old.get('totalDocsExamined'), new.get('totalDocsExamined'))} |"
        )

    lines += ["", "## Limitations and interpretation", ""]
    lines += [
        "- These figures come from MongoDB `explain()` execution statistics; each query was sampled once per condition.",
        "- Millisecond timings are coarse and vary with server load, cache state, and network conditions. A `0 ms` reading does not prove a query is instantaneous.",
        "- `totalDocsExamined` and `totalKeysExamined` show work performed, not proof that a particular index was helpful.",
        "- A compound index can improve sorting or narrow a query while other query shapes see no benefit.",
        "- Case-insensitive substring searches such as `contains Labrador` may not use the planned B-tree indexes efficiently.",
        "- Do not claim a before-and-after speedup if the 'before' snapshot was captured after the indexes already existed.",
    ]
    if warnings:
        lines.extend(["", "## Data quality warnings", ""])
        lines.extend("- " + warning for warning in warnings)
    lines.extend(["", "## Capstone documentation", "", "Use the measured counts and query-plan differences above in the Milestone Four narrative. Explain whether each proposed index improved, worsened, or did not measurably change the observed query, and discuss index maintenance costs.", ""])
    return "\n".join(lines), warnings


# convert the saved JSON measurements to a Markdown analysis file

def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize existing MongoDB index measurements.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to original index_comparison.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Where to write the Markdown analysis")
    args = parser.parse_args(argv)
    if not args.input.exists():
        parser.error(
            "The original index_comparison.json was not found. Look in your Step 3 project "
            "under benchmarks/results/ and copy it here if needed. Do not rerun setup_indexes.py "
            "just to create a new 'before' snapshot; the indexes may already exist."
        )
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        report, warnings = generate_report(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"Cannot analyze benchmark report: {exc}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print("Performance analysis saved:", args.output)
    print("Benchmark caveats:", len(warnings))
    for warning in warnings:
        print(" -", warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
