#!/usr/bin/env python3
"""
Simple test script to verify the legacy list fix
"""

import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

def test_legacy_positions():
    """Test that legacy positions are correct"""
    try:
        # Connect to database
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        client = MongoClient(mongodb_uri, tls=True)
        db = client[mongodb_db]
        
        print("✅ Database connected successfully")
        
        # Show current state
        main_count = db.levels.count_documents({"is_legacy": {"$ne": True}})
        legacy_count = db.levels.count_documents({"is_legacy": True})
        print(f"📊 Current state: {main_count} main levels, {legacy_count} legacy levels")
        
        # Check for any levels in main list with position > 150
        overflow_main = list(db.levels.find({
            "position": {"$gt": 150},
            "is_legacy": {"$ne": True}
        }))
        
        if overflow_main:
            print(f"❌ Found {len(overflow_main)} levels in main list with position > 150:")
            for level in overflow_main:
                print(f"  Position {level['position']}: {level['name']}")
        else:
            print("✅ No levels found in main list with position > 150")
        
        # Check for gaps in main list positions (1-150)
        main_positions = [level['position'] for level in db.levels.find({
            "is_legacy": {"$ne": True},
            "position": {"$lte": 150}
        })]
        
        expected_positions = set(range(1, 151))
        actual_positions = set(main_positions)
        missing_positions = expected_positions - actual_positions
        
        if missing_positions:
            print(f"❌ Found {len(missing_positions)} gaps in main list positions:")
            print(f"  Missing positions: {sorted(missing_positions)[:10]}{'...' if len(missing_positions) > 10 else ''}")
        else:
            print("✅ No gaps found in main list positions (1-150)")
            
        # Check legacy list starts at position 151
        first_legacy = db.levels.find_one({"is_legacy": True}, sort=[("position", 1)])
        if first_legacy and first_legacy['position'] < 151:
            print(f"❌ First legacy level is at position {first_legacy['position']}, expected >= 151")
        else:
            print("✅ Legacy levels start at position 151 or higher")
        
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_legacy_positions()