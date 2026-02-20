#!/usr/bin/env python3
"""
Script to reverse legacy list placements to be completely opposite.
The last level becomes first, first level becomes last, etc.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def main():
    print("🔄 Reversing legacy list to opposite order...")
    start_time = time.time()
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # Get all legacy levels sorted by current position
    legacy_levels = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"Found {len(legacy_levels)} legacy levels")
    
    if not legacy_levels:
        print("❌ No legacy levels found!")
        return
    
    print(f"Current order:")
    print(f"  First: #{legacy_levels[0]['position']} - {legacy_levels[0]['name']}")
    print(f"  Last:  #{legacy_levels[-1]['position']} - {legacy_levels[-1]['name']}")
    
    # Create position mapping for reverse order
    # Current positions: 101, 102, 103, ..., 209
    # New positions:    209, 208, 207, ..., 101 (completely reversed)
    current_positions = [level['position'] for level in legacy_levels]
    current_positions.sort()
    
    # Create mapping: old_position -> new_position (reverse order)
    position_mapping = {}
    for i, old_pos in enumerate(current_positions):
        # Reverse the order: first becomes last, last becomes first
        new_pos = current_positions[-(i+1)]
        position_mapping[old_pos] = new_pos
    
    print(f"\nPosition mapping (opposite order):")
    print(f"  #{current_positions[0]} → #{position_mapping[current_positions[0]]}")
    print(f"  #{current_positions[-1]} → #{position_mapping[current_positions[-1]]}")
    
    # Update legacy levels with new positions
    updated_levels = 0
    for level in legacy_levels:
        old_position = level['position']
        new_position = position_mapping[old_position]
        
        # Update the level
        result = mongo_db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {'position': new_position}}
        )
        
        if result.modified_count > 0:
            updated_levels += 1
            print(f"  ✅ {level['name']}: #{old_position} → #{new_position}")
    
    print(f"\n✅ Updated {updated_levels} legacy levels")
    
    # Verify the new order
    print(f"\n🔄 Verifying new order...")
    final_legacy = list(mongo_db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f"New order:")
    print(f"  First: #{final_legacy[0]['position']} - {final_legacy[0]['name']}")
    print(f"  Last:  #{final_legacy[-1]['position']} - {final_legacy[-1]['name']}")
    
    print(f"\nFirst 5 levels in new order:")
    for i, level in enumerate(final_legacy[:5]):
        print(f"  #{i+1}: #{level['position']} - {level['name']}")
    
    print(f"\nLast 5 levels in new order:")
    for i, level in enumerate(final_legacy[-5:]):
        print(f"  #{len(final_legacy)-4+i}: #{level['position']} - {level['name']}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n🎉 COMPLETED!")
    print(f"✅ Legacy list reversed to opposite order")
    print(f"✅ {updated_levels} levels updated")
    print(f"⏱️  Total time: {duration:.2f} seconds")
    print(f"\n📋 NEW LEGACY LIST STRUCTURE:")
    print(f"  - Positions now range from #{final_legacy[0]['position']} to #{final_legacy[-1]['position']}")
    print(f"  - First level (was last): {final_legacy[0]['name']}")
    print(f"  - Last level (was first): {final_legacy[-1]['name']}")

if __name__ == "__main__":
    main()