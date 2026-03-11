from pymongo import MongoClient
import json
import os
from datetime import datetime, timezone
from bson import ObjectId

# Custom JSON encoder for MongoDB ObjectId
class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("Connecting to MongoDB...")
client = MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    serverSelectionTimeoutMS=30000,
    socketTimeoutMS=30000,
    connectTimeoutMS=30000
)

db = client[mongodb_db]

print("Loading main list levels...")
# Load main list levels with only essential fields
cursor = db.levels.find(
    {"is_legacy": False},
    {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
     "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
     "thumbnail_url": 1, "min_percentage": 1}
).sort("position", 1).limit(150)

main_levels = list(cursor)

print(f"Found {len(main_levels)} main list levels")

# Save to cache file
cache_data = {
    'levels': main_levels,
    'last_updated': datetime.now(timezone.utc).isoformat()
}

with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
    json.dump(cache_data, f, ensure_ascii=False, indent=2, cls=MongoEncoder)

print(f"Saved {len(main_levels)} levels to cache_main_levels.json")
print("Cache file created successfully!")

client.close()
