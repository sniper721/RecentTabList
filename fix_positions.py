#!/usr/bin/env python3
"""
Script to fix level positions after cleanup
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    return int(250 * (0.9475 ** (position - 1)))

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

def fix_positions(db):
    """Fix positions to be sequential 1, 2, 3, etc."""
    # Get all non-legacy levels sorted by current position
    levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
    
    print(f"Found {len(levels)} non-legacy levels to reposition")
    
    updates = []
    for i, level in enumerate(levels, 1):
        new_position = i
        new_points = calculate_level_points(new_position, False)
        
        if level['position'] != new_position or level.get('points', 0) != new_points:
            updates.append({
                '_id': level['_id'],
                'old_position': level['position'],
                'new_position': new_position,
                'old_points': level.get('points', 0),
                'new_points': new_points,
                'name': level['name']
            })
            
            # Update in database
            db.levels.update_one(
                {"_id": level['_id']},
                {"$set": {"position": new_position, "points": new_points}}
            )
    
    print(f"\nUpdated {len(updates)} levels:")
    for update in updates:
        print(f"  {update['name']}: Position {update['old_position']} → {update['new_position']}, Points {update['old_points']} → {update['new_points']}")
    
    return len(updates)

def main():
    """Main function"""
    print("Connecting to database...")
    client, db = connect_to_db()
    
    try:
        print("✓ Connected to MongoDB")
        
        # Fix positions
        updated_count = fix_positions(db)
        
        print(f"\n✓ Fixed positions for {updated_count} levels")
        
        # Show final state
        levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
        print(f"\nFinal level list ({len(levels)} levels):")
        for level in levels:
            has_thumbnail = bool(level.get('thumbnail_url', '').strip())
            thumbnail_info = "📷" if has_thumbnail else "❌"
            print(f"  {level['position']:3d}. {level['name']} ({level['points']} pts) {thumbnail_info}")
        
    finally:
        client.close()

if __name__ == "__main__":
    main()