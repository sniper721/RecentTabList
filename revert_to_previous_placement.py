#!/usr/bin/env python3
"""
Script to revert to the previous placement before moving Donkka and others to legacy.
The user said the previous placement was good.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔄 Reverting to previous placement (before moving Donkka to legacy)...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # The levels that were just moved to legacy (positions 151-180) should go back to main list
    # at their original positions (121-150 duplicates)
    
    # Get current legacy levels that were just moved
    recently_moved_legacy = list(db.levels.find({
        'is_legacy': True,
        'position': {'$gte': 151, '$lte': 180}
    }).sort('position', 1))
    
    print(f"Found {len(recently_moved_legacy)} recently moved legacy levels:")
    for level in recently_moved_legacy:
        print(f"  Position {level['position']}: {level['name']}")
    
    # These should be moved back to main list positions 121-150 (as duplicates)
    # The order should be: position 151 → 121, 152 → 122, etc.
    
    print(f"\nMoving these levels back to main list positions 121-150:")
    
    # Ask for confirmation
    response = input(f"This will move {len(recently_moved_legacy)} levels back to main list. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    updated_count = 0
    for i, level in enumerate(recently_moved_legacy):
        # Map legacy position back to main position
        # Position 151 → 121, 152 → 122, ..., 180 → 150
        new_position = 121 + i
        old_position = level['position']
        
        # Calculate points for main list position
        points = round(250 * (0.9475 ** (new_position - 1)), 2)
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {
                'position': new_position,
                'is_legacy': False,
                'points': points
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {old_position} → {new_position} ({points} points)")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    # Keep the original 4 legacy levels at their current positions (181-184)
    original_legacy = list(db.levels.find({
        'is_legacy': True,
        'position': {'$gte': 181}
    }).sort('position', 1))
    
    print(f"\nKeeping {len(original_legacy)} original legacy levels:")
    for level in original_legacy:
        print(f"  Position {level['position']}: {level['name']}")
    
    print(f"\n🎉 Successfully reverted {updated_count} levels back to main list!")
    
    # Verify the changes
    new_main_count = db.levels.count_documents({'is_legacy': False})
    new_legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nRestored state:")
    print(f"  Main list: {new_main_count} levels (with duplicates at 121-150)")
    print(f"  Legacy list: {new_legacy_count} levels")
    
    # Show some examples of the restored duplicates
    print(f"\nExample restored duplicates:")
    for pos in [121, 150]:
        levels_at_pos = list(db.levels.find({'position': pos, 'is_legacy': False}))
        if len(levels_at_pos) > 1:
            print(f"  Position {pos}: {[level['name'] for level in levels_at_pos]}")
    
    print("\n✅ Reverted to previous placement where Donkka was on main list")
    print("✅ Restored the duplicate positions at 121-150")

if __name__ == "__main__":
    main()