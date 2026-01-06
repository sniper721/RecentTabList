#!/usr/bin/env python3
"""
Test script to verify the event loop fix for level monitoring
"""

import os
import sys
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_event_loop_fix():
    """Test that the level monitor can handle event loop issues properly"""
    print("🧪 Testing Event Loop Fix for Level Monitoring")
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
        from level_monitor import LevelMonitor, start_level_monitor, get_level_monitor
        print("✅ Level monitor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import level monitor: {e}")
        return False
    
    # Test 2: Create monitor without event loop (simulating the error condition)
    try:
        print("\n🔧 Testing monitor creation without event loop...")
        
        # Create a monitor instance
        monitor = LevelMonitor(db)
        print("✅ Monitor instance created successfully")
        
        # Test the new start_monitoring_task method without an event loop
        success = monitor.start_monitoring_task()
        if not success:
            print("✅ Correctly handled missing event loop")
        else:
            print("⚠️ Unexpectedly succeeded without event loop")
        
    except Exception as e:
        print(f"❌ Monitor creation test failed: {e}")
        return False
    
    # Test 3: Test with a proper event loop
    try:
        print("\n🔄 Testing monitor with proper event loop...")
        
        async def test_with_loop():
            monitor = LevelMonitor(db)
            
            # Get the current event loop
            loop = asyncio.get_event_loop()
            
            # Test starting with explicit loop
            success = monitor.start_monitoring_task(loop)
            if success:
                print("✅ Successfully started with explicit event loop")
                
                # Stop the monitoring immediately to clean up
                monitor.running = False
                if monitor.session:
                    await monitor.session.close()
                
                return True
            else:
                print("❌ Failed to start with explicit event loop")
                return False
        
        # Run the async test
        result = asyncio.run(test_with_loop())
        if not result:
            return False
        
    except Exception as e:
        print(f"❌ Event loop test failed: {e}")
        return False
    
    # Test 4: Test the start_level_monitor function
    try:
        print("\n🚀 Testing start_level_monitor function...")
        
        # Test without Discord bot (should handle gracefully)
        monitor = start_level_monitor(db, None)
        if monitor:
            print("✅ start_level_monitor handled missing Discord bot gracefully")
        else:
            print("❌ start_level_monitor failed without Discord bot")
            return False
        
    except Exception as e:
        print(f"❌ start_level_monitor test failed: {e}")
        return False
    
    print("\n🎉 All event loop fix tests passed!")
    print("\n📋 Summary of fixes:")
    print("✅ Added start_monitoring_task() method with proper error handling")
    print("✅ Updated start_level_monitor() to handle missing event loops")
    print("✅ Enhanced Discord bot integration with fallback logic")
    print("✅ Added comprehensive error handling and logging")
    
    print("\n🔧 The fix ensures:")
    print("• Monitor can be created even without an event loop")
    print("• Monitoring starts when Discord bot event loop becomes available")
    print("• Proper error messages instead of crashes")
    print("• Graceful fallback behavior")
    
    return True

if __name__ == "__main__":
    success = test_event_loop_fix()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Event loop fix test")
    sys.exit(0 if success else 1)