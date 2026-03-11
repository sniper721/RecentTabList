from pymongo import MongoClient
import json
import os
from datetime import datetime, timezone
from bson import ObjectId

class MongoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

from dotenv import load_dotenv
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("Connecting to MongoDB with extended timeouts...")
try:
    client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=120000,  # 2 minutes
        socketTimeoutMS=120000,
        connectTimeoutMS=120000
    )
    
    db = client[mongodb_db]
    
    print("Testing connection...")
    db.admin.command('ping')
    print("Connected successfully!")
    
    print("Loading main list levels (this may take a minute)...")
    
    # Load in smaller batches
    main_levels = []
    batch_size = 50
    skip = 0
    
    while True:
        batch = list(db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
             "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
             "thumbnail_url": 1, "min_percentage": 1}
        ).sort("position", 1).skip(skip).limit(batch_size))
        
        if not batch:
            break
        
        main_levels.extend(batch)
        skip += batch_size
        print(f"Loaded {len(main_levels)} levels so far...")
        
        if len(main_levels) >= 150:
            break
    
    print(f"Total: {len(main_levels)} main list levels")
    
    # Save to cache file
    cache_data = {
        'levels': main_levels,
        'last_updated': datetime.now(timezone.utc).isoformat()
    }
    
    with open('cache_main_levels.json', 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2, cls=MongoEncoder)
    
    print(f"Saved {len(main_levels)} levels to cache_main_levels.json")
    print("SUCCESS! Restart your Flask server now.")
    
    client.close()
    
except Exception as e:
    print(f"Error: {e}")
    print("\nIf timeout persists, the database may be slow. Try:")
    print("1. Check your internet connection")
    print("2. Restart your router")
    print("3. Try again in a few minutes")
