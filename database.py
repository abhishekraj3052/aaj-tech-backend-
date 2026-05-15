import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True)
db = client[DATABASE_NAME]

def get_db():
    return db
