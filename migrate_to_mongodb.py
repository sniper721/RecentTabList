import sqlite3
import pymongo
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://spinerspinerreal:EfitlEyLK6Rx8jb2@rtldb.4bu6pci.mongodb.net/?retryWrites=true&w=majority&appName=RTLDB/')
DATABASE_NAME = os.environ.get('MONGODB_DB', 'rtl_database')

def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('instance/demonlist.db')
    sqlite_conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = sqlite_conn.cursor()
    
    # Connect to MongoDB
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    mongo_db = mongo_client[DATABASE_NAME]
    
    print("Starting migration from SQLite to MongoDB...")
    
    # Migrate Users
    print("Migrating users...")
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    
    users_collection = mongo_db.users
    users_collection.drop()  # Clear existing data
    
    for user in users:
        user_doc = {
            '_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'password_hash': user['password_hash'],
            'is_admin': bool(user['is_admin']),
            'points': user['points'] or 0,
            'date_joined': datetime.fromisoformat(user['date_joined'].replace('Z', '+00:00')) if user['date_joined'] else datetime.utcnow(),
            'google_id': user['google_id'] if 'google_id' in user.keys() else None
        }
        users_collection.insert_one(user_doc)
    
    print(f"Migrated {len(users)} users")
    
    # Migrate Levels
    print("Migrating levels...")
    cursor.execute("SELECT * FROM level")
    levels = cursor.fetchall()
    
    levels_collection = mongo_db.levels
    levels_collection.drop()  # Clear existing data
    
    for level in levels:
        level_doc = {
            '_id': level['id'],
            'name': level['name'],
            'creator': level['creator'],
            'verifier': level['verifier'],
            'level_id': level['level_id'],
            'video_url': level['video_url'],
            'thumbnail_url': level['thumbnail_url'] if 'thumbnail_url' in level.keys() else None,
            'description': level['description'],
            'difficulty': level['difficulty'],
            'position': level['position'],
            'is_legacy': bool(level['is_legacy']),
            'date_added': datetime.fromisoformat(level['date_added'].replace('Z', '+00:00')) if level['date_added'] else datetime.utcnow(),
            'points': level['points'] or 0,
            'min_percentage': level['min_percentage'] or 100
        }
        levels_collection.insert_one(level_doc)
    
    print(f"Migrated {len(levels)} levels")
    
    # Migrate Records
    print("Migrating records...")
    cursor.execute("SELECT * FROM record")
    records = cursor.fetchall()
    
    records_collection = mongo_db.records
    records_collection.drop()  # Clear existing data
    
    for record in records:
        record_doc = {
            '_id': record['id'],
            'user_id': record['user_id'],
            'level_id': record['level_id'],
            'progress': record['progress'],
            'video_url': record['video_url'],
            'status': record['status'],
            'date_submitted': datetime.fromisoformat(record['date_submitted'].replace('Z', '+00:00')) if record['date_submitted'] else datetime.utcnow()
        }
        records_collection.insert_one(record_doc)
    
    print(f"Migrated {len(records)} records")
    
    # Create indexes for better performance
    print("Creating indexes...")
    users_collection.create_index("username", unique=True)
    users_collection.create_index("email", unique=True)
    users_collection.create_index("google_id", unique=True, sparse=True)
    
    levels_collection.create_index("position")
    levels_collection.create_index("is_legacy")
    
    records_collection.create_index("user_id")
    records_collection.create_index("level_id")
    records_collection.create_index("status")
    
    # Close connections
    sqlite_conn.close()
    mongo_client.close()
    
    print("Migration completed successfully!")
    print(f"Data migrated to MongoDB database: {DATABASE_NAME}")

if __name__ == "__main__":
    migrate_data()