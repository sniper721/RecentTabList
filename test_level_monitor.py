#!/usr/bin/env python3
"""
Test script for the Level Monitor
Tests the level checking functionality without running the full bot
"""

import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from level_monitor import LevelMonitor

load_dotenv()

async def test_level_monitor():
    """Test the level monitor functionality"""
    print("🧪 Testing Level Monitor...")
    print("=" * 50)
    
    # Connect to MongoDB
    try:
        mongo_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongo_uri)
        db = client.rtl_database
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False
    
    # Create level monitor instance
    monitor = LevelMonitor(db)
    
    # Test individual level checking
    print("\n🔍 Testing individual level checks...")
    
    # Test with a known existing level (Bloodbath - ID: 10565740)
    test_levels = [
        {"id": 10565740, "name": "Bloodbath", "should_exist": True},
        {"id": 999999999, "name": "Non-existent Level", "should_exist": False},
        {"id": 128, "name": "Stereo Madness", "should_exist": True}
    ]
    
    # Create session for testing
    import aiohttp
    monitor.session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={'User-Agent': 'RTL-Level-Monitor-Test/1.0'}
    )
    
    try:
        for test_level in test_levels:
            print(f"\n🔍 Checking {test_level['name']} (ID: {test_level['id']})...")
            
            exists = await monitor.check_level_exists(test_level['id'])
            
            if exists == test_level['should_exist']:
                print(f"✅ PASS: {test_level['name']} - Expected: {test_level['should_exist']}, Got: {exists}")
            else:
                print(f"❌ FAIL: {test_level['name']} - Expected: {test_level['should_exist']}, Got: {exists}")
    
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    
    finally:
        if monitor.session:
            await monitor.session.close()
    
    # Test database level checking (if there are levels in the database)
    print("\n📊 Testing database level checking...")
    
    try:
        levels_with_id = list(db.levels.find({
            "level_id": {"$exists": True, "$ne": None, "$ne": ""},
            "is_removed": {"$ne": True}
        }).limit(3))  # Test only first 3 levels
        
        if levels_with_id:
            print(f"Found {len(levels_with_id)} levels to test from database")
            
            # Create new session for database testing
            monitor.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'RTL-Level-Monitor-Test/1.0'}
            )
            
            for level in levels_with_id:
                level_name = level.get('name', 'Unknown')
                level_id = level.get('level_id')
                
                print(f"\n🔍 Checking database level: {level_name} (ID: {level_id})...")
                
                exists = await monitor.check_level_exists(level_id)
                print(f"Result: {'✅ EXISTS' if exists else '❌ REMOVED'}")
            
            await monitor.session.close()
        else:
            print("No levels with level_id found in database")
    
    except Exception as e:
        print(f"❌ Error testing database levels: {e}")
    
    print("\n✅ Level monitor test completed!")
    return True

if __name__ == "__main__":
    asyncio.run(test_level_monitor())