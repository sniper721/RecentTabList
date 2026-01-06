#!/usr/bin/env python3
"""
Test script for persistent level monitoring system
Tests that monitoring state persists across bot restarts
"""

import os
import sys
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_persistent_monitoring():
    """Test the persistent monitoring system"""
    print("🧪 Testing Persistent Level Monitoring System")
    print("=" * 60)
    
    # Connect to MongoDB
    try:
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        print(f"📡 Connecting to MongoDB...")
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False
    
    # Test 1: Import level monitor
    try:
        print("\n🔍 Testing level monitor import...")
        from level_monitor import LevelMonitor, start_level_monitor, auto_start_level_monitor_if_enabled, get_level_monitor
        print("✅ Level monitor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import level monitor: {e}")
        return False
    
    # Test 2: Create monitor instance and test persistence
    try:
        print("\n🔧 Testing monitor persistence...")
        
        # Create a monitor instance
        monitor = LevelMonitor(db)
        print("✅ Monitor instance created")
        
        # Test loading settings (should create defaults if none exist)
        monitor._load_persistent_settings()
        print("✅ Settings loaded/created")
        
        # Test saving settings
        monitor.running = True
        monitor._save_persistent_settings()
        print("✅ Settings saved with enabled=True")
        
        # Test checking enabled status
        is_enabled = monitor.is_enabled_in_settings()
        print(f"✅ Enabled status check: {is_enabled}")
        
        # Test disabling
        monitor.running = False
        monitor._save_persistent_settings()
        print("✅ Settings saved with enabled=False")
        
        # Verify disabled status
        is_enabled = monitor.is_enabled_in_settings()
        print(f"✅ Disabled status check: {is_enabled}")
        
    except Exception as e:
        print(f"❌ Monitor persistence test failed: {e}")
        return False
    
    # Test 3: Test auto-start functionality
    try:
        print("\n🚀 Testing auto-start functionality...")
        
        # First, disable monitoring
        settings = {
            "_id": "level_monitor",
            "enabled": False,
            "check_interval": 1800,
            "last_updated": datetime.now(timezone.utc)
        }
        db.site_settings.update_one(
            {"_id": "level_monitor"},
            {"$set": settings},
            upsert=True
        )
        
        # Test auto-start when disabled
        result = auto_start_level_monitor_if_enabled(db)
        if result is None:
            print("✅ Auto-start correctly skipped when disabled")
        else:
            print("❌ Auto-start should have been skipped when disabled")
            return False
        
        # Enable monitoring
        settings["enabled"] = True
        db.site_settings.update_one(
            {"_id": "level_monitor"},
            {"$set": settings},
            upsert=True
        )
        
        # Test auto-start when enabled
        result = auto_start_level_monitor_if_enabled(db)
        if result is not None:
            print("✅ Auto-start correctly started when enabled")
            # Stop it immediately to clean up
            if result.running:
                import asyncio
                asyncio.create_task(result.stop_monitoring())
        else:
            print("❌ Auto-start should have started when enabled")
            return False
        
    except Exception as e:
        print(f"❌ Auto-start test failed: {e}")
        return False
    
    # Test 4: Test interval persistence
    try:
        print("\n⏰ Testing interval persistence...")
        
        monitor = LevelMonitor(db)
        
        # Set a custom interval
        monitor.set_check_interval(45)  # 45 minutes
        
        # Create a new monitor instance and check if it loads the interval
        new_monitor = LevelMonitor(db)
        if new_monitor.check_interval == 45 * 60:  # 45 minutes in seconds
            print("✅ Interval persistence works correctly")
        else:
            print(f"❌ Interval not persisted correctly: expected {45*60}, got {new_monitor.check_interval}")
            return False
        
    except Exception as e:
        print(f"❌ Interval persistence test failed: {e}")
        return False
    
    # Test 5: Test database settings structure
    try:
        print("\n🗄️ Testing database settings structure...")
        
        # Check if settings document exists and has correct structure
        settings = db.site_settings.find_one({"_id": "level_monitor"})
        if settings:
            required_fields = ["enabled", "check_interval", "last_updated"]
            for field in required_fields:
                if field not in settings:
                    print(f"❌ Missing required field: {field}")
                    return False
            print("✅ Database settings structure is correct")
        else:
            print("❌ Settings document not found")
            return False
        
    except Exception as e:
        print(f"❌ Database settings test failed: {e}")
        return False
    
    print("\n🎉 All persistent monitoring tests passed!")
    print("\n📋 Summary of features tested:")
    print("✅ Monitor state persistence (enabled/disabled)")
    print("✅ Check interval persistence")
    print("✅ Auto-start functionality")
    print("✅ Settings loading and saving")
    print("✅ Database structure validation")
    
    print("\n🔧 How to use:")
    print("1. Use !startchecks to enable monitoring (persists across restarts)")
    print("2. Use !stopchecks to disable monitoring (persists across restarts)")
    print("3. Use !setmonitorinterval <minutes> to change check frequency")
    print("4. Use !checkingstatus to see current state and persistence info")
    print("5. Bot will automatically resume monitoring after restart if it was enabled")
    
    return True

if __name__ == "__main__":
    success = test_persistent_monitoring()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Persistent monitoring test")
    sys.exit(0 if success else 1)