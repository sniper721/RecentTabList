#!/usr/bin/env python3
"""
Script to fix legacy level placement order after the 150-level extension.
The issue: levels were being added to the bottom of legacy list, so the order is reversed.
Solution: Reorder legacy levels so that level at position 184 goes to 121, level at 155 goes to 150, etc.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    print("🔧 Fixing legacy level placement order...")
    
    # Load environment variables
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    # Connect to MongoDB
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Get all legacy levels sorted by current position
    legacy_levels = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"Found {len(legacy_levels)} legacy levels")
    
    if not legacy_levels:
        print("No legacy levels found!")
        return
    
    print("\nCurrent legacy level order:")
    for i, level in enumerate(legacy_levels):
        print(f"  Position {level['position']}: {level['name']} (ID: {level.get('level_id', 'N/A')})")
    
    # The user wants the order reversed because levels were added to bottom for a long time
    # So the level currently at position 184 should go to position 121 (first legacy position after 120 main levels)
    # Wait, let me check the current main list size first
    
    main_count = db.levels.count_documents({'is_legacy': {'$ne': True}})
    print(f"\nMain list has {main_count} levels")
    
    # Legacy should start at position 151 (after 150 main levels)
    legacy_start_position = 151
    
    # Reverse the order of legacy levels
    reversed_legacy = list(reversed(legacy_levels))
    
    print(f"\nReordering legacy levels to start at position {legacy_start_position}...")
    print("New order will be:")
    
    # Show what the new order will look like
    for i, level in enumerate(reversed_legacy):
        new_position = legacy_start_position + i
        print(f"  Position {new_position}: {level['name']} (was at {level['position']})")
    
    # Ask for confirmation
    response = input(f"\nThis will reorder {len(legacy_levels)} legacy levels. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update positions
    updated_count = 0
    for i, level in enumerate(reversed_legacy):
        new_position = legacy_start_position + i
        old_position = level['position']
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {'position': new_position}}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {old_position} → {new_position}")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully reordered {updated_count} legacy levels!")
    
    # Verify the changes
    print("\nVerifying new order...")
    updated_legacy = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    
    print("New legacy level order:")
    for level in updated_legacy[:10]:  # Show first 10
        print(f"  Position {level['position']}: {level['name']}")
    if len(updated_legacy) > 10:
        print(f"  ... and {len(updated_legacy) - 10} more")
    
    # Check specific levels mentioned by user
    level_at_151 = db.levels.find_one({'position': 151, 'is_legacy': True})
    if level_at_151:
        print(f"\n✅ First legacy level (position 151): {level_at_151['name']}")
    
    # Find what was originally at position 184 and 155
    original_184 = None
    original_155 = None
    for level in legacy_levels:
        if level['position'] == 184:
            original_184 = level
        elif level['position'] == 155:
            original_155 = level
    
    if original_184:
        new_level = db.levels.find_one({'_id': original_184['_id']})
        print(f"✅ Level that was at 184 ({original_184['name']}) is now at position {new_level['position']}")
    
    if original_155:
        new_level = db.levels.find_one({'_id': original_155['_id']})
        print(f"✅ Level that was at 155 ({original_155['name']}) is now at position {new_level['position']}")
    
    print("\n🎯 Legacy level placement order has been fixed!")
    print("The levels that were added to the bottom of the legacy list are now properly ordered.")

if __name__ == "__main__":
    main()