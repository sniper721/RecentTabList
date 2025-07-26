from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Test MongoDB connection
mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print(f"Connecting to: {mongodb_uri}")
print(f"Database: {mongodb_db}")

try:
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    # Test connection
    client.admin.command('ping')
    print("✓ MongoDB connection successful!")
    
    # Check collections
    collections = db.list_collection_names()
    print(f"Collections: {collections}")
    
    # Check data
    users_count = db.users.count_documents({})
    levels_count = db.levels.count_documents({})
    records_count = db.records.count_documents({})
    
    print(f"Users: {users_count}")
    print(f"Levels: {levels_count}")
    print(f"Records: {records_count}")
    
    # Test a simple query
    level = db.levels.find_one({"is_legacy": False})
    if level:
        print(f"Sample level: {level['name']}")
    else:
        print("No levels found!")
        
except Exception as e:
    print(f"MongoDB connection failed: {e}")