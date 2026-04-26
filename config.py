import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from get_keys import load_valid_dhan_credentials

# 🔁 Load ENV
load_dotenv()


class Config:
    # -----------------------------------
    # 🔐 ENV VARIABLES
    # -----------------------------------
    MONGO_URI = os.getenv("MONGO_URI")

    # -----------------------------------
    # 🗄️ DATABASE CONFIG (FROM ENV)
    # -----------------------------------
    DB_NAME = os.getenv("DB_NAME")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME")    
    ORDER_COLLECTION = os.getenv("ORDER_COLLECTION", "orders")
    TESTING_FLAG = os.getenv("TESTING_FLAG", "false").lower() == "true"
    # -----------------------------------
    # ⚙️ INTERNAL CACHE
    # -----------------------------------
    _dhan_creds = None

    # -----------------------------------
    #  LOAD DHAN CREDS (FROM get_keys.py)
    # -----------------------------------
    @classmethod
    def load_dhan_creds(cls):
        if cls._dhan_creds:
            return cls._dhan_creds

        try:

            creds = load_valid_dhan_credentials()

            if not creds:
                print(" No valid Dhan token found")
                return None

            cls._dhan_creds = creds
            return creds

        except Exception as e:
            print(f" Config Load Error: {e}")
            return None

    # -----------------------------------
    # 🎯 DIRECT ACCESS (BEST USAGE)
    # -----------------------------------
    @classmethod
    def dhan(cls):
        """
        Returns full creds dict:
        {
            client_id,
            access_token,
            expiry
        }
        """
        return cls.load_dhan_creds()

    # -----------------------------------
    # 🎯 INDIVIDUAL GETTERS
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
    #  TOKEN VALID CHECK
    # -----------------------------------
    @classmethod
    def is_token_valid(cls):
        creds = cls.load_dhan_creds()

        if not creds:
            return False

        return datetime.now(timezone.utc) < creds["expiry"]