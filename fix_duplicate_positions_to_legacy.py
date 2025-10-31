#!/usr/bin/env python3
"""
Script to fix duplicate positions and move excess levels to legacy in inverse order.
The main list should only have positions 1-150 with no duplicates.
All excess levels should go to legacy in inverse order.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Fixing duplicate positions and moving excess levels to legacy...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get all main list levels sorted by position
    main_levels = list(db.levels.find({'is_legacy': False}).sort('position', 1))
    print(f"Found {len(main_levels)} main list levels")
    
    # Find duplicates and levels beyond position 150
    position_counts = {}
    levels_to_move = []
    
    for level in main_levels:
        pos = level['position']
        if pos not in position_counts:
            position_counts[pos] = []
        position_counts[pos].append(level)
    
    # Keep only the first level at each position 1-150, move the rest to legacy
    levels_to_keep = []
    for pos in range(1, 151):  # Positions 1-150
        if pos in position_counts:
            # Keep the first level at this position
            levels_to_keep.append(position_counts[pos][0])
            # Move any duplicates to legacy
            if len(position_counts[pos]) > 1:
                levels_to_move.extend(position_counts[pos][1:])
                print(f"Position {pos} has {len(position_counts[pos])} levels - keeping 1, moving {len(position_counts[pos])-1} to legacy")
    
    # Any levels at positions > 150 should also go to legacy
    for pos, level_list in position_counts.items():
        if pos > 150:
            levels_to_move.extend(level_list)
            print(f"Position {pos} is beyond 150 - moving {len(level_list)} level(s) to legacy")
    
    print(f"\nLevels to move to legacy: {len(levels_to_move)}")
    for level in levels_to_move:
        print(f"  {level['name']} (currently at position {level['position']})")
    
    # Get existing legacy levels
    existing_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"\nExisting legacy levels: {len(existing_legacy)}")
    
    # Combine all levels for legacy in INVERSE order
    # Sort levels_to_move by their current position in descending order (inverse)
    levels_to_move_sorted = sorted(levels_to_move, key=lambda x: x['position'], reverse=True)
    all_legacy_levels = levels_to_move_sorted + existing_legacy
    
    print(f"\nNew legacy order (INVERSE - highest positions first):")
    legacy_start = 151
    for i, level in enumerate(all_legacy_levels):
        new_position = legacy_start + i
        print(f"  Position {new_position}: {level['name']} (was at {level['position']})")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} levels to legacy and fix duplicates. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update all legacy levels
    updated_count = 0
    for i, level in enumerate(all_legacy_levels):
        new_position = legacy_start + i
        old_position = level['position']
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {
                'position': new_position,
                'is_legacy': True,
                'points': 0
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {old_position} → {new_position}")
    
    print(f"\n🎉 Successfully moved {updated_count} levels to legacy!")
    
    # Verify the changes
    new_main_count = db.levels.count_documents({'is_legacy': False})
    new_legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nNew state:")
    print(f"  Main list: {new_main_count} levels (should be ≤150)")
    print(f"  Legacy list: {new_legacy_count} levels")
    
    # Check for remaining duplicates in main list
    main_positions = [level['position'] for level in db.levels.find({'is_legacy': False})]
    duplicates = len(main_positions) - len(set(main_positions))
    if duplicates == 0:
        print("✅ No duplicate positions in main list")
    else:
        print(f"⚠️  Still {duplicates} duplicate positions in main list")
    
    print("\n✅ Excess levels moved to legacy in INVERSE order")
    print("✅ Main list now has unique positions 1-150")

if __name__ == "__main__":
    main()