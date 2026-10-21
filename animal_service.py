"""Business rules for Grazioso Salvare animal records.

This module does not connect to MongoDB or define the Dash interface.
The dashboard can use these functions before calling the CRUD module.
"""

from math import isfinite

# rescue criteria retained from the original CS 340 dashboard
RESCUE_QUERIES = {
    "water": {
        "animal_type": "Dog",
        "breed": {
            "$regex": "Labrador Retriever|Chesapeake Bay Retriever|Newfoundland",
            "$options": "i",
        },
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "mountain": {
        "animal_type": "Dog",
        "breed": {
            "$regex": "German Shepherd|Alaskan Malamute|Old English Sheepdog|Siberian Husky|Rottweiler",
            "$options": "i",
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "disaster": {
        "animal_type": "Dog",
        "breed": {
            "$regex": "Doberman Pinscher|German Shepherd|Golden Retriever|Bloodhound|Rottweiler",
            "$options": "i",
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 20, "$lte": 300},
    },
}

REQUIRED_FIELDS = (
    "animal_id",
    "animal_type",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
)

TEXT_FIELDS = {"animal_id", "name", "animal_type", "breed", "sex_upon_outcome"}
NUMBER_FIELDS = {"age_upon_outcome_in_weeks", "location_lat", "location_long"}
ALLOWED_FIELDS = TEXT_FIELDS | NUMBER_FIELDS


def rescue_query(category):
    """Return the MongoDB filter for a rescue category."""
    if category in ("reset", None):
        return {}
    if category not in RESCUE_QUERIES:
        raise ValueError("Unknown rescue category.")
    return RESCUE_QUERIES[category].copy()


def validate_animal(record, *, updating=False):
    """Validate fields supplied by a staff form.

    Returns a sanitized copy. Raises ValueError with a useful message when
    input is missing, malformed, or contains unsupported fields.
    Authentication/authorization must be enforced separately on the server.
    """
    if not isinstance(record, dict) or not record:
        raise ValueError("Provide animal record fields.")

    unsupported = set(record) - ALLOWED_FIELDS
    if unsupported:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unsupported))}.")

    if updating and "animal_id" in record:
        raise ValueError("Animal ID cannot be changed.")

    if not updating:
        missing = [key for key in REQUIRED_FIELDS if key not in record]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}.")

    cleaned = {}
    for key, value in record.items():
        if key in TEXT_FIELDS:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be text.")
            value = value.strip()
            if key != "name" and not value:
                raise ValueError(f"{key} cannot be empty.")
        elif key in NUMBER_FIELDS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be a number.")
            if not isfinite(value):
                raise ValueError(f"{key} must be finite.")
            if key == "age_upon_outcome_in_weeks" and value < 0:
                raise ValueError("Age cannot be negative.")
            if key == "location_lat" and not -90 <= value <= 90:
                raise ValueError("Latitude must be between -90 and 90.")
            if key == "location_long" and not -180 <= value <= 180:
                raise ValueError("Longitude must be between -180 and 180.")
        cleaned[key] = value

    if ("location_lat" in cleaned) != ("location_long" in cleaned):
        raise ValueError("Latitude and longitude must be provided together.")

    return cleaned
