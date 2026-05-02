import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

from core.db import get_auth_mongo_client  # ✅ correct client

logger = logging.getLogger(__name__)

load_dotenv()

# -----------------------------------
# 🔧 DB CONFIG (can override via .env)
# -----------------------------------
DB_NAME = os.getenv("AUTH_DB_NAME", "trading")
COLLECTION_NAME = os.getenv("AUTH_COLLECTION_NAME", "auth")

# ✅ Debug flag
BASIC_LOGS = os.getenv("BASIC_LOGS", "false").lower() == "true"

# -----------------------------------
# COLLECTION (singleton style)
# -----------------------------------
_collection = None


def get_collection():
    global _collection

    if _collection is None:
        client = get_auth_mongo_client()   # ✅ FIXED

        if client is None:
            raise ValueError("❌ Auth Mongo client not initialized")

        db = client[DB_NAME]
        _collection = db[COLLECTION_NAME]

        if BASIC_LOGS:
            print(f"✅ Auth Mongo ready → DB: {DB_NAME}, Collection: {COLLECTION_NAME}")

    return _collection


# -----------------------------------
# SAVE TOKEN TO MONGO
# -----------------------------------
def save_token_to_mongo(data: dict):
    try:
        collection = get_collection()

        collection.update_one(
            {"_id": "dhan_token"},
            {"$set": data},
            upsert=True
        )

        if BASIC_LOGS:
            print("✅ Token saved to MongoDB")

    except Exception as e:
        print(f"❌ Mongo save error: {e}")


# -----------------------------------
# FETCH TOKEN FROM MONGO
# -----------------------------------
def fetch_token_from_mongo():
    try:
        collection = get_collection()

        data = collection.find_one({"_id": "dhan_token"})

        if not data:
            print("❌ No token found in MongoDB")
            return None

        data.pop("_id", None)

        if BASIC_LOGS:
            print("📥 Token fetched from MongoDB")

        return data

    except Exception as e:
        print(f"❌ Mongo fetch error: {e}")
        return None


# -----------------------------------
# DELETE TOKEN FROM MONGO
# -----------------------------------
def delete_token_from_mongo():
    try:
        collection = get_collection()

        collection.delete_one({"_id": "dhan_token"})

        if BASIC_LOGS:
            print("🗑️ Token deleted from MongoDB")

    except Exception as e:
        print(f"❌ Mongo delete error: {e}")


# -----------------------------------
# LOAD DHAN CREDENTIALS
# -----------------------------------
def load_dhan_credentials():
    data = fetch_token_from_mongo()

    if not data:
        print("❌ No token data found")
        return None

    dhan_client_id = data.get("dhanClientId")
    access_token = data.get("accessToken")
    expiry_time = data.get("expiryTime")

    if not dhan_client_id or not access_token or not expiry_time:
        print("❌ Missing required token fields")
        return None

    try:
        # ✅ Normalize timezone
        if expiry_time.endswith("Z"):
            expiry_time = expiry_time.replace("Z", "+00:00")

        expiry_dt = datetime.fromisoformat(expiry_time)

        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

    except Exception:
        print("❌ Invalid expiry format")
        return None

    # ✅ Safe debug
    if BASIC_LOGS:
        masked_client = dhan_client_id[:4] + "****"
        masked_token = access_token[:6] + "******"

        print("🔐 Credentials Loaded:")
        print(f"   Client ID: {masked_client}")
        print(f"   Access Token: {masked_token}")
        print(f"   Expiry: {expiry_dt}")

    return {
        "client_id": dhan_client_id,
        "access_token": access_token,
        "expiry": expiry_dt
    }


# -----------------------------------
# LOAD ONLY VALID TOKEN
# -----------------------------------
def load_valid_dhan_credentials():
    creds = load_dhan_credentials()

    if not creds:
        return None

    if datetime.now(timezone.utc) >= creds["expiry"]:
        logger.error("Token expired")
        return None

    if BASIC_LOGS:
        print("✅ Token is valid")

    return creds


# # -----------------------------------
# # QUICK TEST (optional)
# # -----------------------------------
# if __name__ == "__main__":

#     print("\n🔹 Fetching credentials...\n")

#     creds = load_valid_dhan_credentials()

#     if not creds:
#         print("⚠️ No valid token found. Please authenticate again.")
#     else:
#         print("✅ Credentials Loaded Successfully")
#         print(f"Client ID: {creds['client_id'][:3]}...")
#         print(f"Access Token: {creds['access_token'][:10]}...")  # partial for safety
#         print(f"Expiry: {creds['expiry']}")