"""
Quick check - just verify database is accessible
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB')

print("Quick Database Check")
print("=" * 60)

try:
    client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[mongodb_db]
    
    # Just ping
    db.command('ping')
    print("✅ Database connection: OK")
    
    # Quick count (fast)
    main_count = db.levels.count_documents({"is_legacy": {"$ne": True}})
    legacy_count= db.levels.count_documents({"is_legacy": True})
    
    print(f"✅ Main list levels: {main_count}")
    print(f"✅ Legacy levels: {legacy_count}")
    
    if main_count >= 99:
        print(f"\n✅ Main list size looks good ({main_count} levels)")
    
    # Get one sample level (should be fast)
    sample = db.levels.find_one({"is_legacy": {"$ne": True}})
    if sample:
        print(f"\n✅ Sample level: #{sample.get('position')} - {sample.get('name')}")
    
    print("\n✅ Database is working!")
    print("   Next: Start server with 'python main.py'")
    
except Exception as e:
    print(f"❌ Error: {e}")
