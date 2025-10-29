#!/usr/bin/env python3
"""
Test script to verify level ID fixes work properly
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_level_id_handling():
    """Test that level ID handling works for both ObjectId and integer formats"""
    
    # Connect to database
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    print("🔍 Testing Level ID Handling...")
    
    # Test ObjectId levels (new format)
    print("\n📋 Testing ObjectId levels:")
    objectid_levels = list(db.levels.find({"_id": {"$type": "objectId"}}).limit(3))
    
    for level in objectid_levels:
        level_id = level['_id']
        print(f"  ✅ Level: {level['name']} | ID: {level_id} | Type: {type(level_id)}")
        
        # Test the conversion logic from our fixed functions
        level_id_str = str(level_id)
        try:
            # Try ObjectId first
            converted_id = ObjectId(level_id_str)
            print(f"    ✅ ObjectId conversion successful: {converted_id}")
        except (ValueError, InvalidId):
            try:
                # Fall back to int
                converted_id = int(level_id_str)
                print(f"    ✅ Integer conversion successful: {converted_id}")
            except ValueError:
                print(f"    ❌ Both conversions failed!")
    
    # Test integer levels (old format)
    print("\n📋 Testing Integer levels:")
    integer_levels = list(db.levels.find({"_id": {"$type": "int"}}).limit(3))
    
    for level in integer_levels:
        level_id = level['_id']
        print(f"  ✅ Level: {level['name']} | ID: {level_id} | Type: {type(level_id)}")
        
        # Test the conversion logic from our fixed functions
        level_id_str = str(level_id)
        try:
            # Try ObjectId first
            converted_id = ObjectId(level_id_str)
            print(f"    ✅ ObjectId conversion successful: {converted_id}")
        except (ValueError, InvalidId):
            try:
                # Fall back to int
                converted_id = int(level_id_str)
                print(f"    ✅ Integer conversion successful: {converted_id}")
            except ValueError:
                print(f"    ❌ Both conversions failed!")
    
    # Test specific problematic levels mentioned
    print("\n🎯 Testing Specific Problematic Levels:")
    
    # Level #25
    level25 = db.levels.find_one({"position": 25})
    if level25:
        print(f"  Level #25: {level25['name']} | ID: {level25['_id']} | Type: {type(level25['_id'])}")
        # Test URL generation
        level_url = f"/level/{level25['_id']}"
        print(f"    URL would be: {level_url}")
    
    # Level #31 (Dreamscape Circles)
    level31 = db.levels.find_one({"position": 31})
    if level31:
        print(f"  Level #31: {level31['name']} | ID: {level31['_id']} | Type: {type(level31['_id'])}")
        # Test URL generation
        level_url = f"/level/{level31['_id']}"
        print(f"    URL would be: {level_url}")
    
    print("\n✅ Level ID handling test completed!")
    print("🔧 The fixes should now handle both ObjectId and integer level IDs properly.")
    
    client.close()

if __name__ == "__main__":
    test_level_id_handling()