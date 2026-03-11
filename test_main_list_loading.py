"""
Test script to verify main list loading from database
"""
import sys
import time

# Add current directory to path
sys.path.insert(0, '.')

print("="*80)
print("Testing Main List Loading from Database")
print("="*80)

try:
    # Import the main app components
    from main import mongo_manager, load_levels_from_database, levels_cache
    
    print("\n1. Checking MongoDB connection status...")
    if mongo_manager.is_connected():
        print("   ✅ MongoDB is connected")
    else:
        print("   ⏳ MongoDB is connecting in background...")
        print("   Waiting up to 30 seconds for connection...")
        for i in range(30):
            time.sleep(1)
            if mongo_manager.is_connected():
                print(f"   ✅ MongoDB connected after {i+1} seconds!")
                break
        else:
            print("   ⚠️ MongoDB didn't connect within 30 seconds")
    
    print("\n2. Testing direct database load...")
    main_levels = load_levels_from_database(is_legacy=False)
    
    if main_levels and len(main_levels) > 0:
        print(f"   ✅ Successfully loaded {len(main_levels)} main levels from database")
        print(f"\n   First 5 levels:")
        for i, level in enumerate(main_levels[:5], 1):
            print(f"   {i}. Position #{level.get('position', '?')} - {level.get('name', 'Unknown')} by {level.get('creator', 'Unknown')}")
        
        print(f"\n   Last level:")
        last = main_levels[-1]
        print(f"   {len(main_levels)}. Position #{last.get('position', '?')} - {last.get('name', 'Unknown')} by {last.get('creator', 'Unknown')}")
        
    else:
        print("   ❌ No levels loaded from database")
        print("   This could mean:")
        print("   - MongoDB is not connected yet")
        print("   - The database has no levels with is_legacy != True")
        print("   - There's a query timeout issue")
    
    print("\n3. Checking cache status...")
    print(f"   Main levels in cache: {len(levels_cache.get('main_list', []))}")
    print(f"   Legacy levels in cache: {len(levels_cache.get('legacy_list', []))}")
    print(f"   Cache last updated: {levels_cache.get('last_updated', 'Never')}")
    
    print("\n4. Testing legacy levels load...")
    legacy_levels = load_levels_from_database(is_legacy=True)
    
    if legacy_levels and len(legacy_levels) > 0:
        print(f"   ✅ Successfully loaded {len(legacy_levels)} legacy levels")
    else:
        print(f"   ⚠️ No legacy levels found (this may be normal)")
    
    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)
    
    if main_levels and len(main_levels) > 0:
        print("\n✅ SUCCESS: Main list levels can be loaded from database!")
        print("   The website should now display levels correctly.")
    else:
        print("\n⚠️ WARNING: Could not load levels from database")
        print("   Please check:")
        print("   1. MongoDB connection string in .env file")
        print("   2. MongoDB server is running and accessible")
        print("   3. The database contains levels data")
        print("   4. Check the console output above for specific errors")
    
except Exception as e:
    print(f"\n❌ ERROR during testing: {e}")
    import traceback
    traceback.print_exc()
    print("\nPlease check the error above and try again.")
