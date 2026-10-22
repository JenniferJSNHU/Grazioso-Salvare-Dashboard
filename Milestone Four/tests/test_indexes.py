import unittest
from unittest.mock import MagicMock

from CRUD_Python_Module import AnimalShelter
from benchmarks.benchmark_database import QUERY_CASES, capture_query_plans


class TestDatabaseIndexes(unittest.TestCase):
    # use a mock collection to avoid modifying live mongodb indexes
    def setUp(self):
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = MagicMock()
        self.shelter.collection.list_indexes.return_value = [{"key": {"_id": 1}}]

    # verify the planned index fields and stable pagination tie breakers
    def test_index_definitions(self):
        self.shelter.collection.create_indexes.return_value = ["created"]
        result = self.shelter.ensure_indexes()

        indexes = self.shelter.collection.create_indexes.call_args.args[0]
        actual = {index.document["name"]: list(index.document["key"].items()) for index in indexes}
        self.assertEqual(result, ["created"])
        self.assertEqual(actual, {
            "idx_animal_id_page": [("animal_id", 1), ("_id", 1)],
            "idx_rescue_type_sex_age": [
                ("animal_type", 1),
                ("sex_upon_outcome", 1),
                ("age_upon_outcome_in_weeks", 1),
            ],
            "idx_breed_sort": [("breed", 1), ("_id", 1)],
            "idx_name_sort": [("name", 1), ("_id", 1)],
        })

    # avoid duplicate indexes when equivalent field patterns already exist
    def test_existing_indexes_are_reused(self):
        self.shelter.collection.list_indexes.return_value = [
            {"key": {"animal_id": 1, "_id": 1}},
            {"key": {"animal_type": 1, "sex_upon_outcome": 1, "age_upon_outcome_in_weeks": 1}},
            {"key": {"breed": 1, "_id": 1}},
            {"key": {"name": 1, "_id": 1}},
        ]
        self.assertEqual(self.shelter.ensure_indexes(), [])
        self.shelter.collection.create_indexes.assert_not_called()

    # make index creation errors visible instead of hiding them
    def test_index_errors_propagate(self):
        self.shelter.collection.create_indexes.side_effect = RuntimeError("permission denied")
        with self.assertRaises(RuntimeError):
            self.shelter.ensure_indexes()

    # measure only query plans without reading individual animal values
    def test_benchmark_queries(self):
        cursor = self.shelter.collection.find.return_value
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.explain.return_value = {
            "executionStats": {
                "nReturned": 8,
                "executionTimeMillis": 1,
                "totalKeysExamined": 8,
                "totalDocsExamined": 8,
            },
            "queryPlanner": {"winningPlan": {"stage": "IXSCAN"}},
        }

        results = capture_query_plans(self.shelter.collection)
        self.assertEqual(len(results), len(QUERY_CASES))
        self.assertTrue(all(item["totalDocsExamined"] == 8 for item in results.values()))
        self.assertEqual(cursor.limit.call_count, len(QUERY_CASES))
        self.assertEqual(cursor.explain.call_count, len(QUERY_CASES))

    # record database errors without exposing credentials or crashing setup
    def test_benchmark_error_is_summarized(self):
        cursor = self.shelter.collection.find.return_value
        cursor.sort.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.explain.side_effect = RuntimeError("connection details")

        results = capture_query_plans(self.shelter.collection)
        self.assertEqual(
            results["default_animal_page"], {"error": "RuntimeError"}
        )
        self.assertNotIn("connection details", str(results))


if __name__ == "__main__":
    unittest.main()
