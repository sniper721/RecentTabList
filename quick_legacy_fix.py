#!/usr/bin/env python3
"""
Quick fix for legacy positions
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import mongo_db, mongo_client
    print("✅ Imported components")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

def main():
    try:
        mongo_client.admin.command('ping')
        print("✅ DB connected")
        
        # Fix legacy positions
        legacy_levels = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1))
        print(f"Found {len(legacy_levels)} legacy levels")
        
        for i, level in enumerate(legacy_levels):
            new_position = 101 + i
            if level['position'] != new_position:
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"position": new_position}}
                )
                print(f"Updated {level['name']}: #{level['position']} → #{new_position}")
        
        # Move main list overflow to legacy
        overflow = list(mongo_db.levels.find({
            "position": {"$gt": 100},
            "is_legacy": {"$ne": True}
        }))
        
        if overflow:
            print(f"Moving {len(overflow)} overflow levels to legacy")
            highest_legacy = mongo_db.levels.find_one({"is_legacy": True}, sort=[("position", -1)])
            next_pos = (highest_legacy['position'] + 1) if highest_legacy else 101
            
            for level in overflow:
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"is_legacy": True, "position": next_pos, "points": 0}}
                )
                print(f"Moved {level['name']} to legacy #{next_pos}")
                next_pos += 1
        
        print("✅ Fixed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()