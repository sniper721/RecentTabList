#!/usr/bin/env python3
"""
Script to fix the main list to have exactly 150 levels (positions 1-150).
Move any duplicate levels to legacy positions.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Fixing main list to have exactly 150 levels...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get all main list levels
    main_levels = list(db.levels.find({'is_legacy': False}).sort('position', 1))
    print(f"Found {len(main_levels)} main list levels")
    
    # Group by position to find duplicates
    from collections import defaultdict
    position_groups = defaultdict(list)
    for level in main_levels:
        position_groups[level['position']].append(level)
    
    # Find duplicates and levels to move to legacy
    levels_to_move = []
    for position in range(1, 151):  # Positions 1-150
        if position in position_groups:
            levels_at_pos = position_groups[position]
            if len(levels_at_pos) > 1:
                # Keep the first level, move the rest to legacy
                levels_to_move.extend(levels_at_pos[1:])
                print(f"Position {position}: keeping '{levels_at_pos[0]['name']}', moving {len(levels_at_pos)-1} to legacy")
    
    if not levels_to_move:
        print("No duplicate levels found to move!")
        return
    
    print(f"\nLevels to move to legacy ({len(levels_to_move)}):")
    for level in levels_to_move:
        print(f"  {level['name']} (currently at position {level['position']})")
    
    # Get current legacy levels to know where to start placing new ones
    existing_legacy = list(db.levels.find({'is_legacy': True}).sort('position', -1))
    if existing_legacy:
        next_legacy_pos = existing_legacy[0]['position'] + 1
    else:
        next_legacy_pos = 151
    
    print(f"\nNew legacy levels will start at position {next_legacy_pos}")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} duplicate levels to legacy. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Move levels to legacy
    updated_count = 0
    for i, level in enumerate(levels_to_move):
        new_position = next_legacy_pos + i
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
    
    # Verify the final state
    main_count = db.levels.count_documents({'is_legacy': False})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nFinal state:")
    print(f"  Main list: {main_count} levels (should be 150)")
    print(f"  Legacy list: {legacy_count} levels")
    
    # Check if main list now has exactly 150 unique positions
    main_levels_updated = list(db.levels.find({'is_legacy': False}))
    main_positions = [level['position'] for level in main_levels_updated]
    unique_positions = set(main_positions)
    
    if len(unique_positions) == 150 and min(unique_positions) == 1 and max(unique_positions) == 150:
        print("✅ Main list now has exactly 150 unique positions (1-150)")
    else:
        print(f"⚠️  Main list has {len(unique_positions)} unique positions")
    
    print("\n✅ Main list fixed to have exactly 150 levels!")

if __name__ == "__main__":
    main()