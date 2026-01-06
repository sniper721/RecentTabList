#!/usr/bin/env python3
"""
Test the specific level ID 130869575 to see if it exists on GD servers
"""

import asyncio
import aiohttp
from level_monitor import LevelMonitor
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

async def test_level_130869575():
    """Test the specific level ID that was mentioned"""
    level_id = 130869575
    
    print(f"🔍 Testing level ID {level_id}...")
    
    # Connect to database
    client = MongoClient(os.environ.get('MONGODB_URI'))
    db = client.rtl_database
    
    # Create monitor instance
    monitor = LevelMonitor(db)
    monitor.session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={'User-Agent': 'RTL-Level-Monitor/1.0'}
    )
    
    try:
        # Check if level exists
        exists = await monitor.check_level_exists(level_id)
        
        print(f"\n📊 FINAL RESULT:")
        print(f"Level {level_id}: {'✅ EXISTS' if exists else '❌ REMOVED'}")
        
        # Also check database status
        level_doc = db.levels.find_one({'level_id': level_id})
        if level_doc:
            print(f"\n📋 Database Status:")
            print(f"Name: {level_doc.get('name', 'Unknown')}")
            print(f"Position: {level_doc.get('position', 'Unknown')}")
            print(f"Is Legacy: {level_doc.get('is_legacy', False)}")
            print(f"Is Removed: {level_doc.get('is_removed', False)}")
            
            if not exists and not level_doc.get('is_removed', False):
                print(f"\n⚠️ ISSUE DETECTED:")
                print(f"Level doesn't exist on GD servers but is not marked as removed in database!")
                print(f"The monitor should have detected this.")
        else:
            print(f"\n❌ Level not found in database")
            
    except Exception as e:
        print(f"❌ Error testing level: {e}")
    finally:
        await monitor.session.close()

async def test_individual_apis():
    """Test each API individually for the level"""
    level_id = 130869575
    
    print(f"\n🔧 Testing individual APIs for level {level_id}...")
    
    # Connect to database
    client = MongoClient(os.environ.get('MONGODB_URI'))
    db = client.rtl_database
    
    # Create monitor instance
    monitor = LevelMonitor(db)
    monitor.session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={'User-Agent': 'RTL-Level-Monitor/1.0'}
    )
    
    try:
        print(f"\n1️⃣ Testing GDBrowser API...")
        gdbrowser_result = await monitor.check_gdbrowser(level_id)
        print(f"GDBrowser: {'✅ EXISTS' if gdbrowser_result else '❌ NOT FOUND'}")
        
        print(f"\n2️⃣ Testing Alternative API...")
        alt_result = await monitor.check_alternative_api(level_id)
        print(f"Alternative: {'✅ EXISTS' if alt_result else '❌ NOT FOUND'}")
        
        print(f"\n3️⃣ Testing Direct GD API...")
        direct_result = await monitor.check_gd_direct(level_id)
        print(f"Direct GD: {'✅ EXISTS' if direct_result else '❌ NOT FOUND'}")
        
        print(f"\n📊 Summary:")
        print(f"GDBrowser: {'✅' if gdbrowser_result else '❌'}")
        print(f"Alternative: {'✅' if alt_result else '❌'}")
        print(f"Direct GD: {'✅' if direct_result else '❌'}")
        
        total_exists = sum([gdbrowser_result, alt_result, direct_result])
        print(f"Total APIs saying it exists: {total_exists}/3")
        
    except Exception as e:
        print(f"❌ Error testing APIs: {e}")
    finally:
        await monitor.session.close()

async def main():
    print("🧪 Testing Level 130869575 Detection...")
    
    await test_level_130869575()
    await test_individual_apis()
    
    print(f"\n💡 If the level shows as removed but the monitor hasn't detected it:")
    print(f"   1. The monitor might not be running")
    print(f"   2. The level might be on legacy list (check if monitor covers legacy)")
    print(f"   3. There might be an issue with the API checks")

if __name__ == "__main__":
    asyncio.run(main())