import unittest
from unittest.mock import MagicMock

from CRUD_Python_Module import AnimalShelter
from animal_service import build_table_query


class TestDatabaseAggregation(unittest.TestCase):
    # use a mock database to avoid changing production data
    def setUp(self):
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = MagicMock()
        self.shelter.collection.aggregate.return_value = [
            {"_id": "Labrador Retriever", "count": 8}
        ]

    # group and limit the most common breeds inside mongodb
    def test_top_ten_breeds_pipeline(self):
        query = build_table_query("reset", '{breed} contains "Labrador"')
        records = self.shelter.aggregate_field_counts("breed", query, limit=10)

        self.assertEqual(records, [{"_id": "Labrador Retriever", "count": 8}])
        pipeline = self.shelter.collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0], {"$match": query})
        self.assertEqual(pipeline[1]["$group"]["count"], {"$sum": 1})
        self.assertIn("$cond", pipeline[1]["$group"]["_id"])
        self.assertEqual(pipeline[2], {"$sort": {"count": -1, "_id": 1}})
        self.assertEqual(pipeline[3], {"$limit": 10})

    # count animal types without loading individual documents
    def test_animal_type_counts(self):
        self.shelter.aggregate_field_counts("animal_type")
        pipeline = self.shelter.collection.aggregate.call_args.args[0]
        self.assertEqual(pipeline[0], {"$match": {}})
        self.assertEqual(len(pipeline), 3)
        self.assertEqual(pipeline[1]["$group"]["_id"]["$cond"][2], "$animal_type")

    # validate fields, limits, and queries before aggregation
    def test_reject_invalid_aggregation_parameters(self):
        cases = [
            ("name", {}, 10),
            ("breed", "bad query", 10),
            ("breed", {}, 0),
            ("breed", {}, -1),
            ("breed", {}, 101),
            ("breed", {}, True),
        ]
        for field, query, limit in cases:
            with self.subTest(field=field, query=query, limit=limit):
                with self.assertRaises(ValueError):
                    self.shelter.aggregate_field_counts(field, query, limit)
        self.shelter.collection.aggregate.assert_not_called()

    # bucket valid ages and identify missing or invalid ages
    def test_age_ranges_pipeline(self):
        query = build_table_query("water", '{name} contains "Bo"')
        self.shelter.aggregate_age_ranges(query)
        pipeline = self.shelter.collection.aggregate.call_args.args[0]

        self.assertEqual(pipeline[0], {"$match": query})
        conversion = pipeline[1]["$set"]["_age_weeks_numeric"]["$convert"]
        self.assertEqual(conversion["input"], "$age_upon_outcome_in_weeks")
        self.assertEqual(conversion["to"], "double")
        self.assertIsNone(conversion["onError"])
        self.assertIsNone(conversion["onNull"])

        switch = pipeline[2]["$group"]["_id"]["$switch"]
        self.assertEqual(
            [branch["then"] for branch in switch["branches"]],
            ["Under 26 weeks", "26–51 weeks", "52–155 weeks", "156+ weeks"],
        )
        self.assertEqual(switch["default"], "Unknown")
        self.assertEqual(pipeline[2]["$group"]["count"], {"$sum": 1})

    # reject malformed age filters without querying the collection
    def test_reject_invalid_age_query(self):
        with self.assertRaises(ValueError):
            self.shelter.aggregate_age_ranges("invalid")
        self.shelter.collection.aggregate.assert_not_called()

    # keep database failures visible to the calling layer
    def test_aggregation_errors_propagate(self):
        self.shelter.collection.aggregate.side_effect = RuntimeError("database down")
        with self.assertRaises(RuntimeError):
            self.shelter.aggregate_field_counts("breed", {})
        with self.assertRaises(RuntimeError):
            self.shelter.aggregate_age_ranges({})


if __name__ == "__main__":
    unittest.main()
