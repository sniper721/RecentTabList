from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

try:
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[mongodb_db]
    
    # Test connection
    client.admin.command('ping')
    print('✓ MongoDB connection successful')
    
    # Check collections
    collections = db.list_collection_names()
    print(f'Collections: {collections}')
    
    # Check levels
    levels_count = db.levels.count_documents({})
    print(f'Levels count: {levels_count}')
    
    if levels_count > 0:
        sample_level = db.levels.find_one()
        print(f'Sample level: {sample_level}')
    
    # Check users
    users_count = db.users.count_documents({})
    print(f'Users count: {users_count}')
    
    if users_count > 0:
        admin_user = db.users.find_one({'is_admin': True})
        if admin_user:
            print(f'Admin user found: {admin_user["username"]}')
        else:
            print('No admin user found')
    
except Exception as e:
    print(f'MongoDB connection error: {e}')