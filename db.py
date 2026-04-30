from pymongo import MongoClient
from config import Config
client=MongoClient(Config.MONGO_URI)
db=client[Config.MONGO_DB]
orders_collection=db[Config.MONGO_COLLECTION]
