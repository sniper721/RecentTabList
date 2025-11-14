#!/usr/bin/env python3
"""
Test script to verify the legacy list fix
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the functions
try:
    from main import mongo_db, mongo_client
    print("✅ Successfully imported database components")
except ImportError as e:
    print(f"❌ Failed to import database components: {e}")
    sys.exit(1)

def test_legacy_fix():
    """Test the legacy list fix"""
    try:
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ Database connected successfully")
        
        # Show current state
        main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
        legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
        print(f"📊 Current state: {main_count} main levels, {legacy_count} legacy levels")
        
        # Show a few main list levels around position 150-155
        print("\n📋 Main list levels around positions 150-155:")
        near_edge = list(mongo_db.levels.find({
            "position": {"$gte": 145, "$lte": 160},
            "is_legacy": {"$ne": True}
        }).sort("position", 1))
        
        for level in near_edge:
            print(f"  Position {level['position']}: {level['name']}")
        
        # Show first few legacy levels
        print("\n📋 First few legacy levels:")
        legacy_levels = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1).limit(5))
        for level in legacy_levels:
            print(f"  Position {level['position']}: {level['name']}")
            
        print("\n✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_legacy_fix()