import os
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")

client = MongoClient(MONGODB_URI, tlsAllowInvalidCertificates=True)
db = client[DATABASE_NAME]

def setup_admin():
    email = "admin@aajtechtrading.com"
    password = "adminPassword123!"
    name = "Super Admin"
    
    # Check if exists
    if db.admins.find_one({"email": email}):
        print("Admin already exists")
        return

    # Hash password (using bcrypt)
    # Note: bcrypt in python and bcryptjs in node are compatible
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    db.admins.insert_one({
        "email": email.lower(),
        "password": hashed.decode('utf-8'),
        "name": name,
        "role": "admin",
        "createdAt": datetime.now()
    })
    print("Admin created successfully in Python")

if __name__ == "__main__":
    setup_admin()
