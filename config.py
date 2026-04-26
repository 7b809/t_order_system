import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from get_keys import load_valid_dhan_credentials
from pymongo import MongoClient

# 🔁 Load ENV
load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # -----------------------------------
    # 🔐 ENV VARIABLES
    # -----------------------------------
    MONGO_URI = os.getenv("MONGO_URI")

    # -----------------------------------
    # 🗄️ DATABASE CONFIG
    # -----------------------------------
    DB_NAME = os.getenv("DB_NAME")
    TOKEN_COLLECTION = os.getenv("COLLECTION_NAME", "access_tokens")
    ORDER_COLLECTION = os.getenv("ORDER_COLLECTION", "orders")

    TESTING_FLAG = os.getenv("TESTING_FLAG", "false").lower() == "true"
    BASE_LOGS = os.getenv("BASE_LOGS", "false").lower() == "true"
    # -----------------------------------
    # ⚙️ INTERNAL CACHE
    # -----------------------------------
    _dhan_creds = None
    _mongo_client = None

    # -----------------------------------
    # 🗄️ MONGO CLIENT (SINGLETON)
    # -----------------------------------
    @classmethod
    def get_db(cls):
        if cls._mongo_client is None:
            if not cls.MONGO_URI:
                raise ValueError("MONGO_URI not found")

            cls._mongo_client = MongoClient(cls.MONGO_URI)

        return cls._mongo_client[cls.DB_NAME]

    # -----------------------------------
    # 📊 ORDER COLLECTION (MAIN LOG SYSTEM)
    # -----------------------------------
    @classmethod
    def get_order_collection(cls):
        db = cls.get_db()
        return db[cls.ORDER_COLLECTION]

    # -----------------------------------
    # 🔐 LOAD DHAN CREDS
    # -----------------------------------
    @classmethod
    def load_dhan_creds(cls):
        if cls._dhan_creds:
            return cls._dhan_creds

        try:
            creds = load_valid_dhan_credentials()

            if not creds:
                print("No valid Dhan token found")
                return None

            cls._dhan_creds = creds
            return creds

        except Exception as e:
            print(f"Config Load Error: {e}")
            return None

    # -----------------------------------
    # 🎯 GETTERS
    # -----------------------------------
    @classmethod
    def get_access_token(cls):
        creds = cls.load_dhan_creds()
        return creds["access_token"] if creds else None

    @classmethod
    def get_client_id(cls):
        creds = cls.load_dhan_creds()
        return creds["client_id"] if creds else None

    @classmethod
    def get_expiry(cls):
        creds = cls.load_dhan_creds()
        return creds["expiry"] if creds else None

    # -----------------------------------
    # ✅ TOKEN VALID CHECK
    # -----------------------------------
    @classmethod
    def is_token_valid(cls):
        creds = cls.load_dhan_creds()

        if not creds:
            return False

        return datetime.now(timezone.utc) < creds["expiry"]