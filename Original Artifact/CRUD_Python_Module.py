from pymongo import MongoClient


class AnimalShelter:
    """CRUD operations for the AAC MongoDB animals collection."""

    # initialize the MongoDB connection
    def __init__(self, username, password):
        """Connect to MongoDB using the provided credentials."""

        self.client = MongoClient(
            f"mongodb://{username}:{password}@localhost:27017/aac?authSource=aac"
        )

        self.database = self.client["aac"]
        self.collection = self.database["animals"]

    # create a new document
    def create(self, data):
        """Insert a document and return True if successful."""

        if data is not None:
            try:
                result = self.collection.insert_one(data)
                return result.acknowledged
            except Exception as e:
                print("Create error:", e)

        return False

    # read matching documents
    def read(self, query):
        """Return a list of documents matching the query."""

        if query is not None:
            try:
                results = self.collection.find(query)
                return list(results)
            except Exception as e:
                print("Read error:", e)

        return []

    # update matching documents
    def update(self, query, new_values):
        """Update documents and return the number modified."""

        if query is not None and new_values is not None:
            try:
                result = self.collection.update_many(query,{"$set": new_values})
                return result.modified_count
            except Exception as e:
                print("Update error:", e)

        return 0

    # delete matching documents
    def delete(self, query):
        """Delete documents and return the number deleted."""

        if query is not None:
            try:
                result = self.collection.delete_many(query)
                return result.deleted_count
            except Exception as e:
                print("Delete error:", e)

        return 0