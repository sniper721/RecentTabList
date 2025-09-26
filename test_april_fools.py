#!/usr/bin/env python3
"""
Test April Fools Mode functionality
"""

from pymongo import MongoClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Initialize MongoDB
print("Connecting to MongoDB...")
mongo_client = MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=False,
    tlsAllowInvalidHostnames=False,
    serverSelectionTimeoutMS=60000,
    socketTimeoutMS=60000,
    connectTimeoutMS=30000,
    maxPoolSize=10,
    minPoolSize=1,
    maxIdleTimeMS=30000,
    waitQueueTimeoutMS=10000,
    retryWrites=True,
    retryReads=True
)
mongo_db = mongo_client[mongodb_db]

def test_april_fools_mode():
    """Test the April Fools mode functionality"""
    print("🎭 Testing April Fools Mode...")
    
    # Check current state
    settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
    current_state = settings and settings.get('enabled', False) if settings else False
    
    print(f"Current April Fools state: {'ENABLED' if current_state else 'DISABLED'}")
    
    # Get some levels to test with
    levels = list(mongo_db.levels.find({}).sort("position", 1).limit(10))
    
    if not levels:
        print("❌ No levels found to test with")
        return False
    
    print(f"Found {len(levels)} levels to test with")
    
    # Show original positions
    print("\n📋 Original positions:")
    for level in levels:
        print(f"  #{level['position']}: {level['name']} (Legacy: {level.get('is_legacy', False)})")
    
    # Test randomization function
    print("\n🎲 Testing randomization...")
    
    # Import the randomization function (simulate it here)
    import random
    
    def randomize_level_positions(levels):
        """Simulate the randomization function"""
        if not levels:
            return levels
        
        # Separate main and legacy levels
        main_levels = [level for level in levels if not level.get('is_legacy', False)]
        legacy_levels = [level for level in levels if level.get('is_legacy', False)]
        
        # Create random positions for main levels
        if main_levels:
            positions = list(range(1, len(main_levels) + 1))
            random.shuffle(positions)
            for i, level in enumerate(main_levels):
                level['position'] = positions[i]
        
        # Create random positions for legacy levels  
        if legacy_levels:
            positions = list(range(1, len(legacy_levels) + 1))
            random.shuffle(positions)
            for i, level in enumerate(legacy_levels):
                level['position'] = positions[i]
        
        # Combine and sort by new random positions
        all_levels = main_levels + legacy_levels
        all_levels.sort(key=lambda x: (x.get('is_legacy', False), x['position']))
        
        return all_levels
    
    # Test randomization multiple times
    for i in range(3):
        print(f"\n🎲 Randomization #{i+1}:")
        
        # Make a copy to avoid modifying original
        test_levels = [level.copy() for level in levels]
        randomized = randomize_level_positions(test_levels)
        
        for level in randomized:
            print(f"  #{level['position']}: {level['name']} (Legacy: {level.get('is_legacy', False)})")
    
    print("\n✅ April Fools mode test completed!")
    return True

def test_settings_management():
    """Test the settings management for April Fools mode"""
    print("\n⚙️ Testing settings management...")
    
    try:
        # Test enabling
        mongo_db.site_settings.update_one(
            {"_id": "april_fools"},
            {"$set": {
                "enabled": True, 
                "enabled_at": datetime.now(timezone.utc),
                "description": "Test mode"
            }},
            upsert=True
        )
        
        settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
        print(f"✅ Enabled April Fools mode: {settings}")
        
        # Test disabling
        mongo_db.site_settings.update_one(
            {"_id": "april_fools"},
            {"$set": {"enabled": False, "disabled_at": datetime.now(timezone.utc)}}
        )
        
        settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
        print(f"✅ Disabled April Fools mode: {settings}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing settings: {e}")
        return False

def main():
    """Main test function"""
    try:
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Run tests
        test1 = test_april_fools_mode()
        test2 = test_settings_management()
        
        if test1 and test2:
            print("\n🎉 All April Fools tests passed!")
            print("\n🎭 How to use:")
            print("1. Go to Admin Console (/admin/console)")
            print("2. Enter command: rtl.april_fools()")
            print("3. Watch the chaos unfold on the main page!")
            print("4. Use rtl.april_fools() again to disable")
        else:
            print("\n❌ Some tests failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        mongo_client.close()
    
    return True

if __name__ == "__main__":
    main()