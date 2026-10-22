import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.report_database_performance import (
    find_plan_stages,
    format_number,
    generate_report,
    main,
    plan_label,
    reduction,
)


class TestDatabasePerformanceReport(unittest.TestCase):
    # use representative mock explain statistics without querying mongodb
    def setUp(self):
        self.data = {
            "captured_at_utc": "2026-10-22T00:00:00+00:00",
            "database": "aac",
            "collection": "animals",
            "document_count": 10000,
            "indexes_before": ["_id_"],
            "indexes_after": ["_id_", "idx_breed_sort"],
            "queries_before": {"breed_sorted_page": {
                "nReturned": 8, "executionTimeMillis": 12,
                "totalKeysExamined": 0, "totalDocsExamined": 10000,
                "winningPlan": {"stage": "COLLSCAN"},
            }},
            "queries_after": {"breed_sorted_page": {
                "nReturned": 8, "executionTimeMillis": 4,
                "totalKeysExamined": 8, "totalDocsExamined": 8,
                "winningPlan": {"stage": "FETCH", "inputStage": {
                    "stage": "IXSCAN", "indexName": "idx_breed_sort"}},
            }},
        }

    # verify explain stages and index names survive nested planner formats
    def test_plan_labels(self):
        report, warnings = generate_report(self.data)
        self.assertEqual(warnings, [])
        self.assertIn("Collection scan → Index: idx_breed_sort", report)
        self.assertIn("99.9% reduction", report)
        self.assertIn("66.7% reduction", report)
        self.assertIn("10,000", report)

    # do not imply a valid baseline if the indexes were already present
    def test_no_new_indexes_warns(self):
        self.data["indexes_before"] = list(self.data["indexes_after"])
        _, warnings = generate_report(self.data)
        self.assertTrue(any("No new indexes" in msg for msg in warnings))

    # flag before-after results that do not return the same number of rows
    def test_different_return_count_warns(self):
        self.data["queries_after"]["breed_sorted_page"]["nReturned"] = 3
        _, warnings = generate_report(self.data)
        self.assertTrue(any("different result counts" in msg for msg in warnings))

    # report query errors but never include exception details from a connection
    def test_error_case(self):
        self.data["queries_after"]["breed_sorted_page"] = {"error": "OperationFailure"}
        report, warnings = generate_report(self.data)
        self.assertIn("OperationFailure", " ".join(warnings))
        self.assertNotIn("None ms", report)

    # retain a clear not-available designation for missing and zero baselines
    def test_missing_values(self):
        self.assertEqual(format_number(None), "n/a")
        self.assertEqual(reduction(0, 0), "n/a")
        self.assertEqual(reduction(10, 15), "50.0% increase")
        self.assertEqual(reduction(10, 5), "+50.0% reduction")

    # reject malformed JSON structures instead of creating a misleading report
    def test_invalid_structure(self):
        with self.assertRaises(ValueError):
            generate_report({"queries_before": {}, "queries_after": {}})
        with self.assertRaises(ValueError):
            generate_report([])

    # save the report from existing JSON using a read-only command-line workflow
    def test_generate_from_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.json"
            target = Path(folder) / "output.md"
            source.write_text(json.dumps(self.data), encoding="utf-8")
            result = main(["--input", str(source), "--output", str(target)])
            self.assertEqual(result, 0)
            self.assertIn("idx_breed_sort", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
