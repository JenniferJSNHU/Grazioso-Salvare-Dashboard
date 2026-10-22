import unittest
from animal_service import validate_animal


class TestAnimalValidation(unittest.TestCase):

    # verify valid animal records are accepted
    def test_valid_animal(self):
        record = {
            "animal_id": "CS499-TEST-001",
            "animal_type": "Dog",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": 52,
        }

        result = validate_animal(record)

        self.assertEqual(result["animal_id"], "CS499-TEST-001")

    # verify missing required fields are rejected
    def test_missing_required_field(self):
        record = {
            "animal_id": "CS499-TEST-002",
            "animal_type": "Dog",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
        }

        with self.assertRaises(ValueError):
            validate_animal(record)

    # prevent changes to existing animal identifiers
    def test_animal_id_update(self):
        changes = {"animal_id": "NEW-ID"}

        with self.assertRaises(ValueError):
            validate_animal(changes, updating=True)


if __name__ == "__main__":
    unittest.main()
