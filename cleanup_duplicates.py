#!/usr/bin/env python3
"""
Script to clean up duplicate levels and keep only ones with images
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def connect_to_db():
    """Connect to MongoDB"""
    client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=5000
    )
    db = client[mongodb_db]
    client.admin.command('ping')
    return client, db

def find_duplicates(db):
    """Find duplicate levels by name"""
    pipeline = [
        {
            "$group": {
                "_id": {"name": {"$toLower": "$name"}},
                "levels": {"$push": "$$ROOT"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {"count": {"$gt": 1}}
        }
    ]
    
    duplicates = list(db.levels.aggregate(pipeline))
    return duplicates

def cleanup_duplicates(db):
    """Remove duplicates, keeping levels with images"""
    duplicates = find_duplicates(db)
    
    print(f"Found {len(duplicates)} sets of duplicate levels:")
    
    removed_count = 0
    
    for duplicate_group in duplicates:
        levels = duplicate_group['levels']
        name = duplicate_group['_id']['name']
        
        print(f"\nDuplicate: '{name}' ({len(levels)} copies)")
        
        # Sort levels: prioritize ones with thumbnail_url, then by _id (newer first)
        levels.sort(key=lambda x: (
            bool(x.get('thumbnail_url', '').strip()),  # Has thumbnail
            x.get('_id', 0)  # Newer ID
        ), reverse=True)
        
        # Keep the first one (best priority), remove the rest
        keep_level = levels[0]
        remove_levels = levels[1:]
        
        print(f"  Keeping: ID {keep_level['_id']} - {keep_level['name']}")
        if keep_level.get('thumbnail_url'):
            print(f"    Has thumbnail: {keep_level['thumbnail_url'][:50]}...")
        else:
            print("    No thumbnail")
            
        for level in remove_levels:
            print(f"  Removing: ID {level['_id']} - {level['name']}")
            if level.get('thumbnail_url'):
                print(f"    Had thumbnail: {level['thumbnail_url'][:50]}...")
            else:
                print("    No thumbnail")
                
            # Remove the level
            db.levels.delete_one({"_id": level['_id']})
            removed_count += 1
    
    return removed_count

def list_all_levels(db):
    """List all levels to see what we have"""
    levels = list(db.levels.find().sort("position", 1))
    
    print(f"\nAll levels in database ({len(levels)} total):")
    for level in levels:
        has_thumbnail = bool(level.get('thumbnail_url', '').strip())
        thumbnail_info = "📷" if has_thumbnail else "❌"
        print(f"  {level.get('position', '?'):3d}. {level['name']} (ID: {level['_id']}) {thumbnail_info}")
    
    return levels

def main():
    """Main cleanup function"""
    print("Connecting to database...")
    client, db = connect_to_db()
    
    try:
        print("✓ Connected to MongoDB")
        
        # List current levels
        print("\n" + "="*60)
        print("CURRENT LEVELS")
        print("="*60)
        list_all_levels(db)
        
        # Find and show duplicates
        print("\n" + "="*60)
        print("CLEANING UP DUPLICATES")
        print("="*60)
        removed_count = cleanup_duplicates(db)
        
        print(f"\n✓ Removed {removed_count} duplicate levels")
        
        # Show final state
        print("\n" + "="*60)
        print("FINAL LEVELS")
        print("="*60)
        final_levels = list_all_levels(db)
        
        print(f"\nSummary:")
        print(f"  Total levels: {len(final_levels)}")
        print(f"  Levels with thumbnails: {sum(1 for l in final_levels if l.get('thumbnail_url', '').strip())}")
        print(f"  Levels without thumbnails: {sum(1 for l in final_levels if not l.get('thumbnail_url', '').strip())}")
        
    finally:
        client.close()

if __name__ == "__main__":
    main()