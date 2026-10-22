import unittest
from unittest.mock import MagicMock

from CRUD_Python_Module import AnimalShelter
from animal_service import REQUIRED_FIELDS
from schema_validation import (
    ANIMAL_JSON_SCHEMA,
    ANIMAL_VALIDATOR,
    SCHEMA_ACTION,
    SCHEMA_LEVEL,
    count_legacy_schema_violations,
)


class TestSchemaValidation(unittest.TestCase):
    # use mock database objects so tests never modify Atlas data
    def setUp(self):
        self.shelter = AnimalShelter.__new__(AnimalShelter)
        self.shelter.collection = MagicMock()
        self.shelter.database = MagicMock()
        self.shelter.collection.name = "animals"
        self.shelter.collection.options.return_value = {}

    # enforce the same required fields as the staff intake form
    def test_required_fields_match_staff_validation(self):
        self.assertEqual(ANIMAL_JSON_SCHEMA["required"], list(REQUIRED_FIELDS))
        self.assertEqual(ANIMAL_JSON_SCHEMA["bsonType"], "object")

    # require numeric ages and geographic coordinates within their valid ranges
    def test_numeric_field_rules(self):
        props = ANIMAL_JSON_SCHEMA["properties"]
        self.assertEqual(props["age_upon_outcome_in_weeks"]["minimum"], 0)
        self.assertEqual(props["location_lat"]["minimum"], -90)
        self.assertEqual(props["location_lat"]["maximum"], 90)
        self.assertEqual(props["location_long"]["minimum"], -180)
        self.assertEqual(props["location_long"]["maximum"], 180)
        self.assertTrue(all(
            props[name]["bsonType"] == ["int", "long", "double", "decimal"]
            for name in ("age_upon_outcome_in_weeks", "location_lat", "location_long")
        ))
        self.assertNotIn("additionalProperties", ANIMAL_JSON_SCHEMA)

    # count existing nonconforming documents with a read-only query
    def test_legacy_preflight(self):
        self.shelter.collection.count_documents.return_value = 42
        self.assertEqual(count_legacy_schema_violations(self.shelter.collection), 42)
        self.shelter.collection.count_documents.assert_called_once_with(
            {"$nor": [ANIMAL_VALIDATOR]}
        )

    # install the validator using moderate enforcement for legacy records
    def test_create_validator(self):
        self.assertTrue(self.shelter.ensure_schema_validation())
        self.shelter.database.command.assert_called_once_with({
            "collMod": "animals",
            "validator": ANIMAL_VALIDATOR,
            "validationLevel": SCHEMA_LEVEL,
            "validationAction": SCHEMA_ACTION,
        })

    # skip setup if the same schema is already active
    def test_existing_validator_reused(self):
        self.shelter.collection.options.return_value = {
            "validator": ANIMAL_VALIDATOR,
            "validationLevel": SCHEMA_LEVEL,
            "validationAction": SCHEMA_ACTION,
        }
        self.assertFalse(self.shelter.ensure_schema_validation())
        self.shelter.database.command.assert_not_called()

    # never replace an existing schema with different rules
    def test_different_validator_not_overwritten(self):
        self.shelter.collection.options.return_value = {
            "validator": {"$jsonSchema": {"required": ["other"]}}
        }
        with self.assertRaises(ValueError):
            self.shelter.ensure_schema_validation()
        self.shelter.database.command.assert_not_called()

    # avoid silently changing enforcement settings for an existing schema
    def test_mismatched_level_not_overwritten(self):
        self.shelter.collection.options.return_value = {
            "validator": ANIMAL_VALIDATOR,
            "validationLevel": "strict",
            "validationAction": "error",
        }
        with self.assertRaises(ValueError):
            self.shelter.ensure_schema_validation()
        self.shelter.database.command.assert_not_called()

    # report server errors instead of claiming schema setup succeeded
    def test_database_errors_propagate(self):
        self.shelter.database.command.side_effect = RuntimeError("not authorized")
        with self.assertRaises(RuntimeError):
            self.shelter.ensure_schema_validation()


if __name__ == "__main__":
    unittest.main()
