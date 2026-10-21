import unittest
from unittest.mock import Mock
from CRUD_Python_Module import AnimalShelter


class TestAnimalUpdates(unittest.TestCase):

    def setUp(self):
        # create a database object without connecting to mongodb
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = Mock()

    # verify a matching animal can be updated
    def test_successful_update(self):
        self.shelter.collection.update_one.return_value.matched_count = 1

        result = self.shelter.update("A123", {"name": "Buddy"})

        self.assertTrue(result)
        self.shelter.collection.update_one.assert_called_once_with(
            {"animal_id": "A123"},
            {"$set": {"name": "Buddy"}},
        )

    # reject updates without a valid animal ID
    def test_missing_animal_id(self):
        with self.assertRaises(ValueError):
            self.shelter.update("", {"name": "Buddy"})

        self.shelter.collection.update_one.assert_not_called()

    # prevent changes to animal identifiers
    def test_protected_animal_id(self):
        with self.assertRaises(ValueError):
            self.shelter.update("A123", {"animal_id": "A456"})

        self.shelter.collection.update_one.assert_not_called()

    # handle records that do not exist
    def test_animal_not_found(self):
        self.shelter.collection.update_one.return_value.matched_count = 0

        result = self.shelter.update("A999", {"name": "Buddy"})

        self.assertFalse(result)

    # verify database errors are propagated
    def test_database_error(self):
        self.shelter.collection.update_one.side_effect = RuntimeError(
            "Simulated database failure"
        )

        with self.assertRaises(RuntimeError):
            self.shelter.update("A123", {"name": "Buddy"})

        self.shelter.collection.update_one.assert_called_once()


if __name__ == "__main__":
    unittest.main()
