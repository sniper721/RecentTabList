"""
Create database indexes for ULTRA-FAST queries
"""

from pymongo import MongoClient, ASCENDING
import os
from dotenv import load_dotenv

load_dotenv()

print("Creating database indexes for ULTRA-FAST performance...")

client = MongoClient(os.environ.get('MONGODB_URI'))
db = client[os.environ.get('MONGODB_DB')]

# Create indexes
print("\n1. Creating index on (is_legacy, position)...")
result = db.levels.create_index([("is_legacy", ASCENDING), ("position", ASCENDING)])
print(f"   Created: {result}")

print("\n2. Creating index on (position)...")
result = db.levels.create_index([("position", ASCENDING)])
print(f"   Created: {result}")

print("\n3. Creating index on (name)...")
result = db.levels.create_index([("name", ASCENDING)])
print(f"   Created: {result}")

print("\n4. Creating index on records (level_id, status)...")
result = db.records.create_index([("level_id", ASCENDING), ("status", ASCENDING)])
print(f"   Created: {result}")

print("\n5. Creating index on records (user_id)...")
result = db.records.create_index([("user_id", ASCENDING)])
print(f"   Created: {result}")

print("\n6. Creating index on users (points)...")
result = db.users.create_index([("points", ASCENDING)])
print(f"   Created: {result}")

print("\nAll indexes created successfully!")
print("Database queries will now be MUCH faster!")
