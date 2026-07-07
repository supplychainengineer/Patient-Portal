"""MongoDB access (pymongo, lazy connect). The client is created once but only
actually connects when a query runs, so the API boots even before Mongo is up."""
from pymongo import MongoClient

import config

_client = MongoClient(config.MONGO_URL, serverSelectionTimeoutMS=3000)
db = _client[config.DB_NAME]


def mongo_ok() -> bool:
    try:
        _client.admin.command("ping")
        return True
    except Exception:
        return False
