#!/usr/bin/env python3
"""
Script to move all levels back to legacy list in INVERSE order.
The lowest levels (like ocean wave at 184) should be at the top of the legacy list.
All legacy levels should be below every main list level.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Moving all levels back to legacy list in INVERSE order...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get current state
    main_count = db.levels.count_documents({'is_legacy': {'$ne': True}})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"Current state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    # Get all levels currently in legacy, sorted by position (ascending)
    legacy_levels = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    
    print(f"\nCurrent legacy levels:")
    for level in legacy_levels[:10]:
        print(f"  Position {level['position']}: {level['name']}")
    if len(legacy_levels) > 10:
        print(f"  ... and {len(legacy_levels) - 10} more")
    
    # Find the highest main list position to know where legacy should start
    main_levels = list(db.levels.find({'is_legacy': {'$ne': True}}).sort('position', -1).limit(1))
    if main_levels:
        highest_main_pos = main_levels[0]['position']
        legacy_start = highest_main_pos + 1
    else:
        legacy_start = 151  # Default if no main levels
    
    print(f"\nLegacy levels will start at position {legacy_start}")
    
    # Reverse the order - lowest position numbers go to top of legacy list
    # So ocean wave (currently at 184) should go to position 151 (first legacy position)
    reversed_legacy = list(reversed(legacy_levels))
    
    print(f"\nNew legacy order (INVERSE - lowest at top):")
    for i, level in enumerate(reversed_legacy[:10]):
        new_position = legacy_start + i
        print(f"  Position {new_position}: {level['name']} (was at {level['position']})")
    if len(reversed_legacy) > 10:
        print(f"  ... and {len(reversed_legacy) - 10} more")
    
    # Ask for confirmation
    response = input(f"\nThis will reorder {len(legacy_levels)} legacy levels in INVERSE order. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update positions in inverse order
    updated_count = 0
    for i, level in enumerate(reversed_legacy):
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
            print(f"  ✅ {level['name']}: {old_position} → {new_position}")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully reordered {updated_count} legacy levels in INVERSE order!")
    
    # Verify the changes
    print("\nVerifying new order...")
    updated_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    
    print("New legacy level order (lowest levels at top):")
    for level in updated_legacy[:10]:
        print(f"  Position {level['position']}: {level['name']}")
    if len(updated_legacy) > 10:
        print(f"  ... and {len(updated_legacy) - 10} more")
    
    print(f"\n✅ First legacy level: {updated_legacy[0]['name']} at position {updated_legacy[0]['position']}")
    print(f"✅ Last legacy level: {updated_legacy[-1]['name']} at position {updated_legacy[-1]['position']}")
    
    print("\n🎯 Legacy levels are now in INVERSE order with lowest levels at the top!")
    print("All legacy levels are positioned below every main list level.")

if __name__ == "__main__":
    main()