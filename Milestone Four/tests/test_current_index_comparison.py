"""Verify the read-only benchmark and its results formatting."""

import unittest
from unittest.mock import MagicMock, patch

from benchmarks.compare_current_indexes import (
    benchmark_collection,
    build_markdown_report,
    explain_query,
    reduction_percentage,
)


class TestCurrentIndexComparison(unittest.TestCase):
    # verify that a forced scan uses a natural hint without database writes
    def test_forced_scan_uses_hint(self):
        collection = MagicMock()
        cursor = collection.find.return_value
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.hint.return_value = cursor
        cursor.explain.return_value = {
            "executionStats": {
                "nReturned": 8, "executionTimeMillis": 4,
                "totalDocsExamined": 400, "totalKeysExamined": 0,
            },
            "queryPlanner": {"winningPlan": {"stage": "COLLSCAN"}},
        }
        result = explain_query(collection, {}, "animal_id", True)
        cursor.hint.assert_called_once_with([("$natural", 1)])
        self.assertEqual(result["plan"], "Collection scan")
        collection.create_index.assert_not_called()
        collection.delete_many.assert_not_called()

    # capture both variants for each planned dashboard query
    @patch("benchmarks.compare_current_indexes.QUERY_CASES", (("test_query", {}, "animal_id"),))
    @patch("benchmarks.compare_current_indexes.measure_condition")
    def test_benchmark_pairs_current_plans(self, measure):
        measure.side_effect = [
            {"plan": "Index scan", "nReturned": 8, "totalDocsExamined": 8},
            {"plan": "Collection scan", "nReturned": 8, "totalDocsExamined": 40},
        ]
        results = benchmark_collection(MagicMock(), trials=1)
        self.assertEqual(results["test_query"]["forced_collection_scan"]["totalDocsExamined"], 40)
        self.assertEqual(measure.call_count, 2)

    # never manufacture reductions when baseline data is missing
    def test_reduction_requires_measurements(self):
        self.assertEqual(reduction_percentage(None, 10), "n/a")
        self.assertEqual(reduction_percentage(100, 20), "+80.0%")

    # preserve transparent documentation of the benchmark limitation
    def test_report_disclaims_historical_baseline(self):
        report = build_markdown_report({
            "captured_at_utc": "2026-10-22T00:00:00+00:00", "database": "aac",
            "collection": "animals", "document_count": 10000,
            "trials_per_condition": 3,
            "results": {"sample": {
                "planner_selected": {"plan": "Index scan", "executionTimeMillis": 1, "totalDocsExamined": 8},
                "forced_collection_scan": {"plan": "Collection scan", "executionTimeMillis": 3, "totalDocsExamined": 100},
            }},
        })
        self.assertIn("not** an original before-indexing measurement", report)
        self.assertIn("sample", report)


if __name__ == "__main__":
    unittest.main()
