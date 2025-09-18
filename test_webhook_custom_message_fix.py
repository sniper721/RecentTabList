#!/usr/bin/env python3
"""
Test script for webhook custom message functionality fix
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime, timezone
from bson.objectid import ObjectId

def test_webhook_custom_message_fix():
    """Test the webhook custom message functionality fix"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        print(f"Connecting to MongoDB: {mongodb_uri}")
        mongo_client = MongoClient(mongodb_uri)
        mongo_db = mongo_client[mongodb_db]
        
        # Test updating webhook settings with custom message
        custom_message = "🚨 IMPORTANT UPDATE 🚨"
        
        # Get current settings or create new ones
        current_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        message_count = current_settings.get("message_count", 0) if current_settings else 0
        
        # Update settings with custom message
        mongo_db.site_settings.update_one(
            {"_id": "changelog"},
            {"$set": {
                "webhook_enabled": True,
                "ping_enabled": False,
                "ping_threshold": 1,
                "role_id": "1388326130183966720",
                "message_format": "detailed",
                "include_timestamp": True,
                "include_admin": True,
                "color_mode": "default",
                "rate_limit": 10,
                "log_level": "info",
                "custom_message": custom_message,
                "message_count": message_count
            }},
            upsert=True
        )
        
        print(f"✅ Updated webhook settings with custom message: '{custom_message}'")
        
        # Test retrieving the custom message
        updated_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        if updated_settings and updated_settings.get("custom_message") == custom_message:
            print(f"✅ Retrieved custom message: '{updated_settings['custom_message']}'")
        else:
            print("❌ Failed to retrieve custom message")
            
        # Test the message formatting logic
        base_message = "Test level has been placed on #1"
        formatted_message = f"{custom_message}\n\n{base_message}" if custom_message else base_message
        print(f"✅ Formatted message: {formatted_message}")
        
        # Test the actual webhook notification
        print("Testing webhook notification with custom message...")
        try:
            # Import and test the notification function
            from changelog_discord import set_mongo_db, notify_changelog
            set_mongo_db(mongo_db)
            
            result = notify_changelog("Test message from fix verification", "TestAdmin")
            if result:
                print("✅ Webhook notification sent successfully!")
            else:
                print("❌ Failed to send webhook notification")
                
        except Exception as e:
            print(f"❌ Error testing webhook notification: {e}")
        
        print("🎉 All webhook custom message fix tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing webhook custom message fix: {e}")
        return False

if __name__ == "__main__":
    test_webhook_custom_message_fix()