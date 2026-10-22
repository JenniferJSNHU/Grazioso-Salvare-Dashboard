from pymongo import MongoClient
import os


# manage database operations for animal shelter records
class AnimalShelter:
    """CRUD operations for the AAC MongoDB animals collection."""

    # initialize the mongodb connection using supplied credentials
    def __init__(self):
        """Connect to the local MongoDB database."""
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.client = MongoClient(mongo_uri)
        self.database = self.client["aac"]
        self.collection = self.database["animals"]

    # insert a new animal record into the mongodb collection
    def create(self, data):
        """Insert a document and return True if successful."""

        # check for missing input before attempting insertion
        if data is not None:
            try:
                result = self.collection.insert_one(data)
                return result.acknowledged
            # handle database errors and report unsuccessful operations
            except Exception as e:
                print("Create error:", e)

        return False

    # retrieve animal records from mongodb
    def read(self, query, projection=None):
        """Return animal records matching a MongoDB query."""

        # check for missing query
        if query is None:
            return []

        try:
            # execute query with optional projection
            cursor = self.collection.find(query, projection)

            # return matching records
            return list(cursor)

        except Exception as e:
            # handle database errors
            print("Read error:", e)
            return []

    # count animal records matching a query
    def count(self, query):
        """Return the number of matching animal records."""

        # require a valid query
        if query is None:
            raise ValueError("A query is required.")

        # count matching documents in MongoDB
        return self.collection.count_documents(query)

    # check whether an animal record exists
    def exists(self, query):
        """Return True if a matching record exists."""

        # require a nonempty query
        if not isinstance(query, dict) or not query:
            raise ValueError("A valid query is required.")

        # check for a matching document
        return self.collection.find_one(query, {"_id": 1}) is not None

    # update a single animal record by its ID
    def update(self, animal_id, new_values):
        """Update one animal record and return True if found."""

        # validate the animal ID
        if not isinstance(animal_id, str) or not animal_id.strip():
            raise ValueError("A valid Animal ID is required.")

        # validate the update data
        if not isinstance(new_values, dict) or not new_values:
            raise ValueError("Updated animal data is required.")

        # prevent changes to record identifiers and unsafe field names
        if any(
            not isinstance(field, str)
            or field.startswith("$")
            or "." in field
            or field in ("_id", "animal_id")
            for field in new_values
        ):
            raise ValueError("Invalid update fields.")

        # update only the matching animal
        result = self.collection.update_one(
            {"animal_id": animal_id.strip()},
            {"$set": new_values},
        )

        # confirm the animal was found
        return result.matched_count == 1

    # delete animal records matching the supplied query
    def delete(self, query):
        """Delete documents and return the number deleted."""

        if query is not None:
            try:
                # remove all records that match the query
                result = self.collection.delete_many(query)
                return result.deleted_count
            except Exception as e:
                print("Delete error:", e)

        return 0
