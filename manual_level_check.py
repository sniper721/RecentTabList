#!/usr/bin/env python3
"""
Manual level check to force the monitor to check a specific level
"""

import asyncio
import aiohttp
from level_monitor import LevelMonitor
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

async def force_check_level(level_id):
    """Force check a specific level and handle removal if needed"""
    
    print(f"🔍 Force checking level ID {level_id}...")
    
    # Connect to database
    client = MongoClient(os.environ.get('MONGODB_URI'))
    db = client.rtl_database
    
    # Get level from database
    level_doc = db.levels.find_one({'level_id': level_id})
    if not level_doc:
        print(f"❌ Level {level_id} not found in database")
        return
    
    print(f"📋 Found level in database: {level_doc.get('name', 'Unknown')}")
    print(f"Position: {level_doc.get('position', 'Unknown')}")
    print(f"Is Legacy: {level_doc.get('is_legacy', False)}")
    print(f"Is Removed: {level_doc.get('is_removed', False)}")
    
    # Create monitor instance
    monitor = LevelMonitor(db)
    monitor.session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        headers={'User-Agent': 'RTL-Level-Monitor/1.0'}
    )
    
    try:
        print(f"\n🔍 Checking if level exists on GD servers...")
        exists = await monitor.check_level_exists(level_id)
        
        print(f"\n📊 RESULT: Level {'EXISTS' if exists else 'REMOVED'}")
        
        if not exists:
            print(f"\n🚨 Level detected as REMOVED - handling removal...")
            await monitor.handle_level_removed(level_doc)
            print(f"✅ Level marked as removed in database")
        else:
            print(f"\n✅ Level still exists on GD servers")
            
            # If it was previously marked as removed, unmark it
            if level_doc.get('is_removed', False):
                print(f"🔄 Level was previously marked as removed, unmarking...")
                db.levels.update_one(
                    {"_id": level_doc["_id"]},
                    {
                        "$unset": {
                            "is_removed": "",
                            "removed_at": "",
                            "removal_detected_by": ""
                        }
                    }
                )
                print(f"✅ Level unmarked as removed")
        
    except Exception as e:
        print(f"❌ Error checking level: {e}")
    finally:
        await monitor.session.close()

async def test_with_known_removed_level():
    """Test with a level that we know is removed"""
    
    # Test with a very high ID that definitely doesn't exist
    fake_level_id = 999999999
    
    print(f"\n🧪 Testing with fake level ID {fake_level_id} (should not exist)...")
    
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
        exists = await monitor.check_level_exists(fake_level_id)
        print(f"Fake level result: {'EXISTS (ERROR!)' if exists else 'REMOVED (CORRECT)'}")
        
        if exists:
            print(f"⚠️ WARNING: Monitor thinks fake level exists - there might be an issue with the API checks")
        else:
            print(f"✅ Monitor correctly detected fake level as removed")
            
    except Exception as e:
        print(f"❌ Error testing fake level: {e}")
    finally:
        await monitor.session.close()

async def main():
    level_id = 130869575
    
    print("🔧 Manual Level Check Tool")
    print("=" * 50)
    
    # First test with the specific level
    await force_check_level(level_id)
    
    # Then test with a known non-existent level to verify the monitor works
    await test_with_known_removed_level()
    
    print(f"\n💡 Summary:")
    print(f"If your level shows as 'EXISTS' but you deleted it:")
    print(f"1. Check if someone re-uploaded it with the same ID")
    print(f"2. GD servers might have caching delays")
    print(f"3. The level might have been restored from backup")
    print(f"4. Try checking the level directly in Geometry Dash")

if __name__ == "__main__":
    asyncio.run(main())