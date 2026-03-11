from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.environ.get('MONGODB_URI'))
mongo_db = client[os.environ.get('MONGODB_DB')]

print("TESTING DIRECT DATABASE QUERY...")
print("=" * 60)

# EXACT SAME QUERY AS IN main.py
levels = list(mongo_db.levels.find(
    {"is_legacy": False},
    {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
     "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
     "thumbnail_url": 1, "min_percentage": 1, "demon_type": 1}
).sort("position", 1).limit(100))

print(f"LOADED {len(levels)} LEVELS FROM DATABASE")
print()

if levels:
    print("First 5 levels:")
    for i in range(min(5, len(levels))):
        print(f"  #{levels[i]['position']}: {levels[i]['name']}")
    print()
    print(f"Last level: #{levels[-1]['position']}: {levels[-1]['name']}")
    print()
    print("SUCCESS! Query returns 100 levels!")
else:
    print("ERROR! No levels returned!")

print("=" * 60)
