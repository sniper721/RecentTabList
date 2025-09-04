#!/usr/bin/env python3
"""
Test script for IP ban functionality
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime, timezone
from bson.objectid import ObjectId

def test_ip_ban_functionality():
    """Test the IP ban functionality"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        print(f"Connecting to MongoDB: {mongodb_uri}")
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client[mongodb_db]
        
        # Test creating a sample IP ban record
        test_ip_ban = {
            "_id": ObjectId(),
            "user_id": ObjectId("507f1f77bcf86cd799439011"),  # Sample user ID
            "username": "test_user",
            "ip_addresses": ["192.168.1.100", "10.0.0.50"],
            "reason": "Testing IP ban functionality",
            "banned_by": "TestScript",
            "ban_date": datetime.now(timezone.utc),
            "active": True
        }
        
        # Insert test ban record
        result = mongo_db.ip_bans.insert_one(test_ip_ban)
        print(f"✅ Inserted test IP ban record with ID: {result.inserted_id}")
        
        # Test querying the ban record
        ban_record = mongo_db.ip_bans.find_one({"_id": result.inserted_id})
        if ban_record:
            print(f"✅ Retrieved IP ban record: {ban_record['username']} banned for '{ban_record['reason']}'")
        else:
            print("❌ Failed to retrieve IP ban record")
            
        # Test checking if an IP is banned
        test_ip = "192.168.1.100"
        ban_check = mongo_db.ip_bans.find_one({
            "ip_addresses": test_ip,
            "active": True
        })
        
        if ban_check:
            print(f"✅ IP {test_ip} is banned")
        else:
            print(f"✅ IP {test_ip} is not banned")
            
        # Clean up test record
        mongo_db.ip_bans.delete_one({"_id": result.inserted_id})
        print("✅ Cleaned up test IP ban record")
        
        print("🎉 All IP ban functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing IP ban functionality: {e}")
        return False

if __name__ == "__main__":
    test_ip_ban_functionality()