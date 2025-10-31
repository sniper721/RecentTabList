#!/usr/bin/env python3
"""
Script to fix gaps in main list positions after moving levels to legacy.
The main list should have positions 1-150 with no gaps.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0.0
    return round(250 * (0.9475 ** (position - 1)), 2)

def main():
    print("🔧 Fixing gaps in main list positions...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get all main list levels sorted by position
    main_levels = list(db.levels.find({'is_legacy': False}).sort('position', 1))
    print(f"Found {len(main_levels)} main list levels")
    
    # Check for gaps in positions 1-150
    expected_positions = set(range(1, 151))  # 1-150
    actual_positions = set(level['position'] for level in main_levels)
    
    gaps = expected_positions - actual_positions
    extras = actual_positions - expected_positions
    
    print(f"Gaps in positions 1-150: {sorted(gaps) if gaps else 'None'}")
    print(f"Positions beyond 150: {sorted(extras) if extras else 'None'}")
    
    if not gaps:
        print("No gaps found in main list positions!")
        return
    
    # Find levels that need to be moved to fill gaps
    levels_beyond_150 = [level for level in main_levels if level['position'] > 150]
    
    if len(levels_beyond_150) < len(gaps):
        print(f"Warning: Not enough levels beyond 150 ({len(levels_beyond_150)}) to fill all gaps ({len(gaps)})")
    
    # Move levels from beyond 150 to fill gaps
    gaps_list = sorted(gaps)
    levels_to_move = levels_beyond_150[:len(gaps_list)]
    
    print(f"\nMoving levels to fill gaps:")
    for i, level in enumerate(levels_to_move):
        if i < len(gaps_list):
            target_pos = gaps_list[i]
            print(f"  {level['name']}: {level['position']} → {target_pos}")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} levels to fill gaps. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update positions
    updated_count = 0
    for i, level in enumerate(levels_to_move):
        if i < len(gaps_list):
            target_position = gaps_list[i]
            new_points = calculate_level_points(target_position, False)
            
            result = db.levels.update_one(
                {'_id': level['_id']},
                {'$set': {
                    'position': target_position,
                    'points': new_points
                }}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"  ✅ {level['name']}: {level['position']} → {target_position} ({new_points} points)")
            else:
                print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully filled {updated_count} gaps!")
    
    # Verify the final state
    main_count = db.levels.count_documents({'is_legacy': False})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    # Check if positions 1-150 are now complete
    main_levels_updated = list(db.levels.find({'is_legacy': False}))
    positions_1_150 = [level['position'] for level in main_levels_updated if 1 <= level['position'] <= 150]
    missing_positions = set(range(1, 151)) - set(positions_1_150)
    
    print(f"\nFinal state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    print(f"  Positions 1-150 complete: {'✅' if not missing_positions else '❌'}")
    if missing_positions:
        print(f"  Still missing positions: {sorted(missing_positions)}")
    
    print("\n✅ Main list gaps fixed!")

if __name__ == "__main__":
    main()