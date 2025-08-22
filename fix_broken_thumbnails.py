#!/usr/bin/env python3
"""
Quick fix script to clean up broken thumbnail URLs
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_thumbnails():
    """Clean up broken thumbnail URLs pointing to missing files"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        print(f"🔗 Connecting to MongoDB...")
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client[mongodb_db]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
        
        # Find levels with broken thumbnail URLs
        broken_levels = list(mongo_db.levels.find({
            "thumbnail_url": {"$regex": "^/static/thumbnails/"}
        }))
        
        print(f"🔍 Found {len(broken_levels)} levels with potentially broken thumbnails")
        
        if len(broken_levels) == 0:
            print("✅ No broken thumbnails found!")
            return
        
        # Clean up broken thumbnail URLs
        result = mongo_db.levels.update_many(
            {"thumbnail_url": {"$regex": "^/static/thumbnails/"}},
            {"$set": {"thumbnail_url": ""}}
        )
        
        print(f"🧹 Cleaned up {result.modified_count} broken thumbnail URLs")
        print("✅ Now these levels will fall back to YouTube thumbnails!")
        
        # Show some examples of what was cleaned up
        print("\n📋 Cleaned up levels:")
        for level in broken_levels[:5]:  # Show first 5 examples
            name = level.get('name', 'Unknown')
            old_thumb = level.get('thumbnail_url', '')
            print(f"   • {name}: {old_thumb}")
        
        if len(broken_levels) > 5:
            print(f"   ... and {len(broken_levels) - 5} more levels")
        
        mongo_client.close()
        print("\n🎉 Fix complete! Your images should work now.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    fix_thumbnails()