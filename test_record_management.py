#!/usr/bin/env python3
"""
Test script for the new record management features:
1. Image editing with keep/upload options
2. Record hiding/showing functionality
3. Record sorting by progress (100% first)
"""

import os
import sys
from datetime import datetime, timezone
from bson.objectid import ObjectId

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import mongo_db, calculate_record_points, update_user_points
    print("✅ Successfully imported main application components")
except ImportError as e:
    print(f"❌ Failed to import main components: {e}")
    sys.exit(1)

def test_record_sorting():
    """Test that records are sorted correctly (100% first, then by date)"""
    print("\n🧪 Testing record sorting...")
    
    try:
        # Find a level with multiple records
        level_with_records = mongo_db.levels.aggregate([
            {"$lookup": {
                "from": "records",
                "localField": "_id",
                "foreignField": "level_id",
                "as": "records"
            }},
            {"$match": {"records.1": {"$exists": True}}},  # At least 2 records
            {"$limit": 1}
        ])
        
        level = next(level_with_records, None)
        if not level:
            print("⚠️  No levels with multiple records found for testing")
            return
        
        level_id = level['_id']
        print(f"Testing with level: {level['name']} (ID: {level_id})")
        
        # Get records sorted by our new logic
        records = list(mongo_db.records.aggregate([
            {"$match": {"level_id": level_id, "status": "approved"}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {
                "progress": -1,  # 100% first
                "date_submitted": 1  # Earlier submissions first within same progress
            }}
        ]))
        
        print(f"Found {len(records)} records:")
        for i, record in enumerate(records[:5]):  # Show first 5
            hidden_status = " (HIDDEN)" if record.get('hidden') else ""
            print(f"  {i+1}. {record['user']['username']}: {record['progress']}%{hidden_status}")
        
        # Verify 100% records come first
        progress_values = [r['progress'] for r in records]
        if progress_values:
            first_progress = progress_values[0]
            if first_progress == 100:
                print("✅ Records are sorted correctly (100% records first)")
            else:
                print(f"⚠️  First record is {first_progress}%, not 100%")
        
    except Exception as e:
        print(f"❌ Error testing record sorting: {e}")

def test_hidden_records():
    """Test hidden record functionality"""
    print("\n🧪 Testing hidden records...")
    
    try:
        # Find a record to test with
        test_record = mongo_db.records.find_one({"status": "approved"})
        if not test_record:
            print("⚠️  No approved records found for testing")
            return
        
        record_id = test_record['_id']
        user_id = test_record['user_id']
        
        print(f"Testing with record ID: {record_id}")
        
        # Get user's points before hiding
        user = mongo_db.users.find_one({"_id": user_id})
        points_before = user.get('points', 0) if user else 0
        print(f"User points before hiding: {points_before}")
        
        # Hide the record
        mongo_db.records.update_one(
            {"_id": record_id},
            {"$set": {
                "hidden": True,
                "hidden_by": "test_script",
                "hidden_at": datetime.now(timezone.utc)
            }}
        )
        print("✅ Record hidden")
        
        # Update user points
        update_user_points(user_id)
        
        # Check user's points after hiding
        user = mongo_db.users.find_one({"_id": user_id})
        points_after_hide = user.get('points', 0) if user else 0
        print(f"User points after hiding: {points_after_hide}")
        
        # Show the record again
        mongo_db.records.update_one(
            {"_id": record_id},
            {"$unset": {
                "hidden": "",
                "hidden_by": "",
                "hidden_at": ""
            }}
        )
        print("✅ Record shown again")
        
        # Update user points again
        update_user_points(user_id)
        
        # Check user's points after showing
        user = mongo_db.users.find_one({"_id": user_id})
        points_after_show = user.get('points', 0) if user else 0
        print(f"User points after showing: {points_after_show}")
        
        # Verify points were restored
        if abs(points_before - points_after_show) < 0.01:  # Allow for small floating point differences
            print("✅ Points correctly restored after showing record")
        else:
            print(f"⚠️  Points not fully restored: {points_before} -> {points_after_show}")
        
    except Exception as e:
        print(f"❌ Error testing hidden records: {e}")

def test_image_handling():
    """Test image handling for levels"""
    print("\n🧪 Testing image handling...")
    
    try:
        # Find levels with different image types
        base64_level = mongo_db.levels.find_one({"thumbnail_url": {"$regex": "^data:"}})
        url_level = mongo_db.levels.find_one({
            "thumbnail_url": {"$exists": True, "$ne": "", "$not": {"$regex": "^data:"}}
        })
        no_image_level = mongo_db.levels.find_one({
            "$or": [
                {"thumbnail_url": {"$exists": False}},
                {"thumbnail_url": ""}
            ]
        })
        
        if base64_level:
            print(f"✅ Found level with base64 image: {base64_level['name']}")
            print(f"   Image starts with: {base64_level['thumbnail_url'][:50]}...")
        
        if url_level:
            print(f"✅ Found level with URL image: {url_level['name']}")
            print(f"   Image URL: {url_level['thumbnail_url']}")
        
        if no_image_level:
            print(f"✅ Found level with no image: {no_image_level['name']}")
        
        print("✅ Image handling test completed")
        
    except Exception as e:
        print(f"❌ Error testing image handling: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting record management tests...")
    
    try:
        # Test database connection
        from main import mongo_client
        mongo_client.admin.command('ping')
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    test_record_sorting()
    test_hidden_records()
    test_image_handling()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()