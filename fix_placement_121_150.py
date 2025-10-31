#!/usr/bin/env python3
"""
Script to fix placement by moving 30 levels from legacy to main list positions 121-150.
Based on user request: level 184 should be at 121, level 155 should be at 150, etc.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.9475)^(x-1) where x is the placement of the level on the list
    return round(250 * (0.9475 ** (position - 1)), 2)

def main():
    print("🔧 Fixing placement for positions 121-150...")
    
    # Load environment variables
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    # Connect to MongoDB
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Check current state
    main_count = db.levels.count_documents({'is_legacy': {'$ne': True}})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"Current state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    # Get current main list range
    main_levels = list(db.levels.find({'is_legacy': {'$ne': True}}).sort('position', 1))
    if main_levels:
        print(f"  Main list positions: {main_levels[0]['position']} to {main_levels[-1]['position']}")
    
    # Get legacy levels sorted by position (reversed order as user requested)
    legacy_levels = list(db.levels.find({'is_legacy': True}).sort('position', -1))
    
    print(f"\nLegacy levels (in reverse order):")
    for i, level in enumerate(legacy_levels[:10]):
        print(f"  {i+1}. Position {level['position']}: {level['name']}")
    
    # The user wants to add 30 levels to positions 121-150
    # Taking the first 30 legacy levels (in reverse order) and moving them to main list
    levels_to_move = legacy_levels[:30]
    
    print(f"\nWill move these {len(levels_to_move)} levels to main list positions 121-150:")
    for i, level in enumerate(levels_to_move):
        new_position = 121 + i
        print(f"  {level['name']} (currently at {level['position']}) → position {new_position}")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_move)} levels from legacy to main list. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Move levels to main list positions 121-150
    updated_count = 0
    for i, level in enumerate(levels_to_move):
        new_position = 121 + i
        new_points = calculate_level_points(new_position, False)  # Main list points
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {
                'position': new_position,
                'is_legacy': False,
                'points': new_points
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {level['position']} → {new_position} ({new_points} points)")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    # Now reorder remaining legacy levels to start at position 151
    remaining_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"\nReordering {len(remaining_legacy)} remaining legacy levels to start at position 151...")
    
    for i, level in enumerate(remaining_legacy):
        new_position = 151 + i
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {'position': new_position}}
        )
        
        if result.modified_count > 0:
            print(f"  ✅ {level['name']}: {level['position']} → {new_position}")
    
    print(f"\n🎉 Successfully updated {updated_count} levels!")
    
    # Verify the changes
    print("\nVerifying changes...")
    new_main_count = db.levels.count_documents({'is_legacy': {'$ne': True}})
    new_legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"New state:")
    print(f"  Main list: {new_main_count} levels")
    print(f"  Legacy list: {new_legacy_count} levels")
    
    # Check specific positions mentioned by user
    level_at_121 = db.levels.find_one({'position': 121})
    level_at_150 = db.levels.find_one({'position': 150})
    
    if level_at_121:
        print(f"✅ Position 121: {level_at_121['name']} ({level_at_121.get('points', 0)} points)")
    
    if level_at_150:
        print(f"✅ Position 150: {level_at_150['name']} ({level_at_150.get('points', 0)} points)")
    
    print("\n🎯 Placement has been fixed according to user requirements!")

if __name__ == "__main__":
    main()