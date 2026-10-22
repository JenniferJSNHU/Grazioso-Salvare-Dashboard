"""Capture MongoDB query-plan statistics around index creation."""

from datetime import datetime, timezone
from pathlib import Path
import json

from animal_service import build_table_query, rescue_query


# use the same data fields that the animal table requests
TABLE_PROJECTION = {
    "_id": 0,
    "animal_id": 1,
    "name": 1,
    "animal_type": 1,
    "breed": 1,
    "sex_upon_outcome": 1,
    "age_upon_outcome_in_weeks": 1,
    "location_lat": 1,
    "location_long": 1,
}


# choose representative queries from the existing dashboard
QUERY_CASES = (
    ("default_animal_page", {}, "animal_id"),
    ("name_sorted_page", {}, "name"),
    ("breed_sorted_page", {}, "breed"),
    (
        "rescue_type_sex_age",
        {
            "animal_type": "Dog",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
        },
        "age_upon_outcome_in_weeks",
    ),
    ("water_rescue_page", rescue_query("water"), "animal_id"),
    (
        "breed_contains_page",
        build_table_query("reset", '{breed} contains "Labrador"'),
        "animal_id",
    ),
)


# measure the database's execution plan without retrieving record values
def capture_query_plans(collection):
    """Return document/key scan counts and query plans for representative reads."""
    results = {}
    for name, query, sort_field in QUERY_CASES:
        try:
            # match dashboard sorting, projection, and page size
            explanation = (
                collection.find(query, TABLE_PROJECTION)
                .sort([(sort_field, 1), ("_id", 1)])
                .limit(8)
                .explain()
            )
            stats = explanation.get("executionStats", {})
            planner = explanation.get("queryPlanner", {})
            winning_plan = planner.get("winningPlan", {})
            results[name] = {
                "nReturned": stats.get("nReturned"),
                "executionTimeMillis": stats.get("executionTimeMillis"),
                "totalKeysExamined": stats.get("totalKeysExamined"),
                "totalDocsExamined": stats.get("totalDocsExamined"),
                "winningPlan": winning_plan,
            }
        except Exception as exc:
            # report a query-plan failure without exposing database credentials
            results[name] = {"error": type(exc).__name__}
    return results


# store before and after measurements for the capstone analysis
def save_index_comparison(collection, before, after, old_indexes, new_indexes):
    """Write metadata and explain results to a local JSON report."""
    output = Path(__file__).resolve().parent / "results" / "index_comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": collection.database.name,
        "collection": collection.name,
        "document_count": collection.count_documents({}),
        "indexes_before": old_indexes,
        "indexes_after": new_indexes,
        "queries_before": before,
        "queries_after": after,
        "notes": [
            "Explain execution times vary; compare keys and documents examined too.",
            "Case-insensitive contains regex searches may not benefit from B-tree indexes.",
            "Existing indexes may already be present and limit the measured difference.",
        ],
    }
    output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return output
