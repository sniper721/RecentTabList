#!/usr/bin/env python3
"""
Script to move levels from positions 151-180 back to legacy list in INVERSE order.
The user wants the main list to have only 150 levels (1-150).
Levels 151-180 should be moved to legacy in inverse order (so 180 becomes first legacy level).
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Moving levels 151-180 to legacy list in INVERSE order...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get levels from positions 151-180 (these should become legacy)
    levels_to_move = list(db.levels.find({
        'position': {'$gte': 151, '$lte': 180},
        'is_legacy': False
    }).sort('position', 1))
    
    print(f"Found {len(levels_to_move)} levels to move to legacy (positions 151-180):")
    for level in levels_to_move:
        print(f"  Position {level['position']}: {level['name']}")
    
    # Get existing legacy levels
    existing_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"\nExisting legacy levels: {len(existing_legacy)}")
    for level in existing_legacy:
        print(f"  Position {level['position']}: {level['name']}")
    
    if not levels_to_move:
        print("No levels found to move!")
        return
    
    # Combine all levels that should be in legacy (existing + new ones)
    # Put the new ones (151-180) in INVERSE order, then existing legacy levels
    reversed_new_levels = list(reversed(levels_to_move))  # 180, 179, 178, ..., 151
    all_legacy_levels = reversed_new_levels + existing_legacy
    
    print(f"\nNew legacy order (INVERSE - highest positions first):")
    legacy_start = 151  # Legacy starts at position 151
    for i, level in enumerate(all_legacy_levels):
        new_position = legacy_start + i
        print(f"  Position {new_position}: {level['name']} (was at {level['position']})")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} levels to legacy and reorder all legacy levels. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update all legacy levels with new positions
    updated_count = 0
    for i, level in enumerate(all_legacy_levels):
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
    
    print(f"\n🎉 Successfully moved and reordered {updated_count} levels!")
    
    # Verify the changes
    print("\nVerifying changes...")
    new_main_count = db.levels.count_documents({'is_legacy': {'$ne': True}})
    new_legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"New state:")
    print(f"  Main list: {new_main_count} levels (should be 150)")
    print(f"  Legacy list: {new_legacy_count} levels")
    
    # Show first few legacy levels
    updated_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print("\nFirst 10 legacy levels (in inverse order):")
    for level in updated_legacy[:10]:
        print(f"  Position {level['position']}: {level['name']}")
    
    print(f"\n✅ Main list now has {new_main_count} levels (positions 1-150)")
    print(f"✅ Legacy list has {new_legacy_count} levels starting at position 151")
    print("✅ Legacy levels are in INVERSE order (highest original positions first)")

if __name__ == "__main__":
    main()