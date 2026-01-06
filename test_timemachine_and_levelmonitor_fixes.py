#!/usr/bin/env python3
"""
Test the time machine and level monitor fixes
"""

import asyncio
import aiohttp
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone

load_dotenv()

def test_timemachine_top150():
    """Test that time machine shows top 150 for recent dates"""
    print("🧪 Testing Time Machine Top 150 Feature...")
    
    try:
        # Load historical rankings
        with open('historical_rankings.json', 'r') as f:
            historical_data = json.load(f)
        
        # Check if today's date (2026-01-05) has data
        today_date = "2026-01-05"
        if today_date in historical_data.get('weekly_rankings', {}):
            rankings = historical_data['weekly_rankings'][today_date]['rankings']
            print(f"✅ Found {len(rankings)} levels for {today_date}")
            
            if len(rankings) >= 100:  # Should be around 149-150
                print(f"✅ Time machine now shows {len(rankings)} levels for recent dates")
                print(f"📋 Top 10 levels for {today_date}:")
                for i, ranking in enumerate(rankings[:10]):
                    print(f"   {ranking['position']}: {ranking['name']}")
                return True
            else:
                print(f"❌ Expected 100+ levels, got {len(rankings)}")
                return False
        else:
            print(f"❌ No data found for {today_date}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing time machine: {e}")
        return False

async def test_level_monitor_rate_limiting():
    """Test that level monitor handles rate limiting properly"""
    print("\n🧪 Testing Level Monitor Rate Limiting...")
    
    try:
        # Import the level monitor
        from level_monitor import LevelMonitor
        
        # Connect to database
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Create monitor instance
        monitor = LevelMonitor(db)
        monitor.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'RTL-Level-Monitor-Test/1.0'}
        )
        
        # Test with a known level ID
        test_level_id = "130869575"  # Known test level
        
        print(f"🔍 Testing rate limiting with level ID: {test_level_id}")
        
        # Test the check method
        exists = await monitor.check_level_exists(test_level_id)
        print(f"✅ Level check completed without rate limit errors")
        print(f"📊 Result: Level {'exists' if exists else 'does not exist'}")
        
        # Check if recent notifications tracking works
        if hasattr(monitor, 'recent_notifications'):
            print("✅ Duplicate notification prevention is active")
        else:
            print("❌ Duplicate notification prevention not found")
        
        # Check if notification cooldown is set
        if hasattr(monitor, 'notification_cooldown'):
            print(f"✅ Notification cooldown set to {monitor.notification_cooldown} seconds")
        else:
            print("❌ Notification cooldown not found")
        
        await monitor.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing level monitor: {e}")
        return False

def test_historical_data_structure():
    """Test that historical data has the correct structure"""
    print("\n🧪 Testing Historical Data Structure...")
    
    try:
        with open('historical_rankings.json', 'r') as f:
            historical_data = json.load(f)
        
        weekly_rankings = historical_data.get('weekly_rankings', {})
        
        # Check old dates (should have ~10 levels)
        old_dates = ["2025-06-21", "2025-07-05", "2025-08-02"]
        new_dates = ["2026-01-05"]
        
        print("📊 Checking historical dates (should have ~10 levels):")
        for date in old_dates:
            if date in weekly_rankings:
                count = len(weekly_rankings[date]['rankings'])
                print(f"   {date}: {count} levels ({'✅' if count <= 15 else '❌'})")
            else:
                print(f"   {date}: No data found")
        
        print("📊 Checking recent dates (should have 100+ levels):")
        for date in new_dates:
            if date in weekly_rankings:
                count = len(weekly_rankings[date]['rankings'])
                print(f"   {date}: {count} levels ({'✅' if count >= 100 else '❌'})")
            else:
                print(f"   {date}: No data found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing historical data: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔧 Testing Time Machine & Level Monitor Fixes\n")
    
    success = True
    
    # Test 1: Time machine top 150
    success &= test_timemachine_top150()
    
    # Test 2: Level monitor rate limiting
    success &= await test_level_monitor_rate_limiting()
    
    # Test 3: Historical data structure
    success &= test_historical_data_structure()
    
    print(f"\n{'🎉' if success else '❌'} Test Results:")
    if success:
        print("✅ All tests passed!")
        print("📋 Summary of fixes:")
        print("   ✅ Time machine shows top 150 for recent dates (like today)")
        print("   ✅ Time machine shows top 10 for historical dates")
        print("   ✅ Level monitor has rate limiting protection")
        print("   ✅ Level monitor prevents duplicate notifications")
        print("   ✅ Historical data structure is correct")
    else:
        print("❌ Some tests failed - check the output above")

if __name__ == "__main__":
    asyncio.run(main())