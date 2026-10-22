import unittest
from unittest.mock import Mock, MagicMock
from CRUD_Python_Module import AnimalShelter


class TestAnimalUpdates(unittest.TestCase):

    # mock MongoDB so tests do not change real shelter records
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


class TestSafeDeletion(unittest.TestCase):

    # mock the collection to protect live animal records
    def setUp(self):
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = Mock()

    # verify only the requested animal is deleted
    def test_delete_one_animal(self):
        self.shelter.collection.delete_one.return_value.deleted_count = 1

        result = self.shelter.delete({"animal_id": " A123 "})

        self.assertEqual(result, 1)
        self.shelter.collection.delete_one.assert_called_once_with(
            {"animal_id": "A123"}
        )
        self.shelter.collection.delete_many.assert_not_called()

    # reject empty, invalid, and unrestricted deletion requests
    def test_reject_unsafe_filters(self):
        unsafe_queries = [
            None,
            {},
            {"name": "Buddy"},
            {"animal_id": {"$ne": ""}},
            {"animal_id": ""},
            {"animal_id": "A123", "name": "Buddy"},
        ]

        for query in unsafe_queries:
            with self.subTest(query=query):
                with self.assertRaises(ValueError):
                    self.shelter.delete(query)

        self.shelter.collection.delete_one.assert_not_called()

    # verify database errors are reported
    def test_delete_database_failure(self):
        self.shelter.collection.delete_one.side_effect = RuntimeError(
            "Database unavailable"
        )

        with self.assertRaises(RuntimeError):
            self.shelter.delete({"animal_id": "A123"})


class TestDatabasePagination(unittest.TestCase):

    # create a mock database without connecting to mongodb
    def setUp(self):
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = MagicMock()

        # verify mongodb pagination returns the requested records

    def test_read_page(self):
        cursor = self.shelter.collection.find.return_value

        # preserve cursor chaining for sorting and pagination
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor

        # simulate a database response
        cursor.__iter__.return_value = iter([{"animal_id": "A123"}])

        result = self.shelter.read_page({}, page=2, page_size=8)

        # verify results and pagination parameters
        self.assertEqual(result, [{"animal_id": "A123"}])
        cursor.sort.assert_called_once_with([("animal_id", 1), ("_id", 1)])
        cursor.skip.assert_called_once_with(16)
        cursor.limit.assert_called_once_with(8)

    # reject invalid page numbers and page sizes
    def test_invalid_pagination(self):
        invalid_inputs = [
            {"page": -1, "page_size": 8},
            {"page": 0, "page_size": 0},
            {"page": 0, "page_size": 101},
            {"page": "1", "page_size": 8},
        ]

        for values in invalid_inputs:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.shelter.read_page({}, **values)

        self.shelter.collection.find.assert_not_called()


if __name__ == "__main__":
    unittest.main()
