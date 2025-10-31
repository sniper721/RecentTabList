#!/usr/bin/env python3
"""
Script to restore the original legacy levels that got moved to main list.
These levels should be in legacy positions 151+.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Restoring original legacy levels...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # These were the original legacy levels that got moved to main list
    original_legacy_names = ['Wedro', 'Bauti 1', 'Bowsergd Level', 'sigma']
    
    print("Finding original legacy levels:")
    levels_to_move = []
    for name in original_legacy_names:
        level = db.levels.find_one({'name': name})
        if level:
            current_pos = level['position']
            is_legacy = level.get('is_legacy', False)
            print(f"  {name}: position {current_pos} (legacy: {is_legacy})")
            if not is_legacy:
                levels_to_move.append(level)
        else:
            print(f"  {name}: NOT FOUND")
    
    if not levels_to_move:
        print("No levels need to be moved to legacy!")
        return
    
    print(f"\nMoving {len(levels_to_move)} levels back to legacy:")
    
    # Move them to legacy positions starting at 151
    legacy_start = 151
    for i, level in enumerate(levels_to_move):
        new_position = legacy_start + i
        print(f"  {level['name']}: {level['position']} → {new_position} (legacy)")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} levels to legacy positions. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update the levels
    updated_count = 0
    for i, level in enumerate(levels_to_move):
        new_position = legacy_start + i
        old_position = level['position']
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {
                'position': new_position,
                'is_legacy': True,
                'points': 0  # Legacy levels have 0 points
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {old_position} → {new_position} (legacy)")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully moved {updated_count} levels to legacy!")
    
    # Verify the changes
    main_count = db.levels.count_documents({'is_legacy': False})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nFinal state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    # Show the legacy levels
    legacy_levels = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"\nLegacy levels:")
    for level in legacy_levels:
        print(f"  Position {level['position']}: {level['name']}")
    
    print("\n✅ Original legacy levels restored!")

if __name__ == "__main__":
    main()