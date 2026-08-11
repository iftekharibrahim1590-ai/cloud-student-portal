"""MongoDB connection helper (sync PyMongo — Flask is sync)."""
import os
from pymongo import MongoClient

_client = None
_db = None


def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(
            os.environ["MONGO_URL"],
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        _db = _client[os.environ["DB_NAME"]]
    return _db
