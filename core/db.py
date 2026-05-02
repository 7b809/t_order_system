from pymongo import MongoClient
from django.conf import settings
client=MongoClient(settings.MONGO_URI)
db=client[settings.MONGO_DB]
orders_collection=db[settings.MONGO_COLLECTION]

from pymongo import MongoClient
from django.conf import settings

# -----------------------------------
# 🔗 SINGLE CLIENT (BEST PRACTICE)
# -----------------------------------
_client = None


def get_mongo_client():
    global _client

    if _client is None:
        if not settings.MONGO_URI:
            raise ValueError("❌ MONGO_URI missing")

        _client = MongoClient(settings.MONGO_URI)
        print("✅ Mongo Connected")

    return _client


# -----------------------------------
# 📦 DATABASE
# -----------------------------------
def get_db():
    client = get_mongo_client()

    if not settings.MONGO_DB:
        raise ValueError("❌ MONGO_DB missing")

    return client[settings.MONGO_DB]


# -----------------------------------
# 📊 COLLECTIONS
# -----------------------------------
def get_orders_collection():
    return get_db()[settings.MONGO_COLLECTION]


def get_auth_collection():
    return get_db()["auth"]  # or settings.AUTH_COLLECTION