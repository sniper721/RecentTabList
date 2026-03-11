"""
Simple test to verify the main list loads from database
This simulates what happens when you visit the website
"""
import sys
sys.path.insert(0, '.')

print("="*80)
print("Testing Main List Loading - Simulating Website Visit")
print("="*80)

try:
    # Import just the essentials
    from dotenv import load_dotenv
    load_dotenv()
    
    from pymongo import MongoClient
    import os
    import time
    
    # Connect to MongoDB (mimicking the app's connection)
    print("\n1. Connecting to MongoDB...")
    uri = os.environ.get('MONGODB_URI')
    db_name = os.environ.get('MONGODB_DB')
    
    client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000
    )
    db = client[db_name]
    
    # Test connection
    try:
        client.admin.command('ping')
        print("   ✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        sys.exit(1)
    
    # Query for main levels (using the FIXED query)
    print("\n2. Querying for MAIN levels (is_legacy: False)...")
    start = time.time()
    
    cursor = db.levels.find(
        {"is_legacy": False},  # THE FIX: explicit False instead of $ne
        {
            "_id": 1,
            "name": 1,
            "creator": 1,
            "verifier": 1,
            "position": 1,
            "points": 1,
            "level_id": 1,
            "difficulty": 1
        }
    ).sort("position", 1)
    
    main_levels = list(cursor)
    elapsed = time.time() - start
    
    print(f"   ✅ Found {len(main_levels)} main levels in {elapsed:.2f}s")
    
    if len(main_levels) > 0:
        print(f"\n3. Sample levels (first 5):")
        for i, level in enumerate(main_levels[:5], 1):
            print(f"   #{level['position']} - {level['name']} by {level['creator']}")
        
        print(f"\n4. Last few levels:")
        for level in main_levels[-3:]:
            print(f"   #{level['position']} - {level['name']} by {level['creator']}")
        
        print(f"\n✅ SUCCESS!")
        print(f"   The main list will display {len(main_levels)} levels")
        print(f"   When you visit the website, it should show all these levels")
        print(f"   First load may take a few seconds, then it will be cached")
        
    else:
        print(f"\n❌ WARNING: No main levels found!")
        print(f"   This shouldn't happen based on our earlier tests")
        print(f"   Please check the database connection and data")
    
    # Also check legacy for completeness
    print(f"\n5. Checking legacy levels for reference...")
    legacy_count = db.levels.count_documents({"is_legacy": True})
    print(f"   Found {legacy_count} legacy levels")
    
    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
