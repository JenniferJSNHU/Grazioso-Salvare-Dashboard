import unittest

from animal_service import build_table_query


class TestTableFilters(unittest.TestCase):
    # search breeds without requiring an exact case-sensitive match
    def test_breed_contains(self):
        query = build_table_query("reset", '{breed} contains "Labrador"')
        self.assertEqual(
            query,
            {"$and": [{}, {"breed": {"$regex": "Labrador", "$options": "i"}}]},
        )

    # keep existing name searches working with exact matches
    def test_name_equals(self):
        query = build_table_query("reset", '{name} = "Buddy"')
        self.assertEqual(query["$and"][1]["name"]["$regex"], "^Buddy$")

    # escape user-entered punctuation before creating regex filters
    def test_special_characters_are_literal(self):
        query = build_table_query("reset", '{breed} contains "Poodle (Toy)"')
        self.assertEqual(query["$and"][1]["breed"]["$regex"], r"Poodle\ \(Toy\)")

    # apply multiple table filters together with rescue criteria
    def test_combined_filters(self):
        query = build_table_query(
            "water", '{breed} contains "Labrador" && {name} contains "Bo"'
        )
        self.assertEqual(query["$and"][0]["animal_type"], "Dog")
        self.assertEqual(len(query["$and"]), 3)

    # compare animal ages as numeric values
    def test_numeric_range(self):
        query = build_table_query("reset", '{age_upon_outcome_in_weeks} >= 30')
        self.assertEqual(query["$and"][1], {"age_upon_outcome_in_weeks": {"$gte": 30.0}})

    # reject invalid fields and operators rather than return all animals
    def test_reject_invalid_filters(self):
        for text in ('{password} contains "x"', '{breed} invalid "x"', '{age_upon_outcome_in_weeks} >= hello'):
            with self.subTest(text=text):
                self.assertEqual(
                    build_table_query("reset", text), {"_id": {"$exists": False}}
                )

    # retain unfiltered rescue searches
    def test_no_column_filter(self):
        self.assertEqual(build_table_query("reset", ""), {})
        self.assertEqual(build_table_query("mountain", None)["animal_type"], "Dog")


if __name__ == "__main__":
    unittest.main()
