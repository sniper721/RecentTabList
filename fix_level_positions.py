#!/usr/bin/env python3
"""
Script to fix level positions - remove duplicates and make them sequential
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    # Position 1 = exponent 0, Position 2 = exponent 1, etc.
    return int(250 * (0.9475 ** (position - 1)))

def main():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✓ Connected to MongoDB")
        
        # Fix main list positions
        print("\n🔧 Fixing main list positions...")
        main_levels = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
        
        print("Current main list positions:")
        for level in main_levels:
            print(f"  Position {level['position']}: {level['name']}")
        
        # Reassign sequential positions
        print("\nReassigning sequential positions...")
        for i, level in enumerate(main_levels, 1):
            old_position = level['position']
            new_position = i
            new_points = calculate_level_points(new_position, False, level.get('level_type', 'Level'))
            
            if old_position != new_position or level.get('points') != new_points:
                print(f"  {level['name']}: Position {old_position} → {new_position}, Points {level.get('points', 0)} → {new_points}")
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"position": new_position, "points": new_points}}
                )
            else:
                print(f"  ✓ {level['name']}: Position {new_position} (no change)")
        
        # Fix legacy list positions
        print("\n🔧 Fixing legacy list positions...")
        legacy_levels = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1))
        
        if legacy_levels:
            print("Current legacy list positions:")
            for level in legacy_levels:
                print(f"  Position {level['position']}: {level['name']}")
            
            # Reassign sequential positions for legacy
            print("\nReassigning sequential positions for legacy...")
            for i, level in enumerate(legacy_levels, 1):
                old_position = level['position']
                new_position = i
                # Legacy levels have 0 points
                
                if old_position != new_position:
                    print(f"  {level['name']}: Position {old_position} → {new_position}")
                    mongo_db.levels.update_one(
                        {"_id": level['_id']},
                        {"$set": {"position": new_position, "points": 0}}
                    )
                else:
                    print(f"  ✓ {level['name']}: Position {new_position} (no change)")
        else:
            print("No legacy levels found.")
        
        # Verify the fix
        print("\n✅ Verification - Main list after fix:")
        main_levels_fixed = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
        for level in main_levels_fixed:
            print(f"  {level['position']:2d}. {level['name']} - {level['points']} points")
        
        if legacy_levels:
            print("\n✅ Verification - Legacy list after fix:")
            legacy_levels_fixed = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1))
            for level in legacy_levels_fixed:
                print(f"  {level['position']:2d}. {level['name']} - {level['points']} points")
        
        print(f"\n🎉 All done! Positions are now sequential and unique.")
        print(f"📋 Main list: {len(main_levels_fixed)} levels (positions 1-{len(main_levels_fixed)})")
        if legacy_levels:
            print(f"📋 Legacy list: {len(legacy_levels)} levels (positions 1-{len(legacy_levels)})")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()