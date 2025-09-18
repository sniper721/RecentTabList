#!/usr/bin/env python3
"""
Badge System Cleanup Script
Removes all badge-related data from the database after badge system removal
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId

# Add the parent directory to Python path to import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import MONGODB_URI, DATABASE_NAME
except ImportError:
    print("Error: Could not import database configuration.")
    print("Please ensure config.py exists with MONGODB_URI and DATABASE_NAME.")
    sys.exit(1)

def cleanup_badge_system():
    """Remove all badge-related data from the database"""
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI)
        db = client[DATABASE_NAME]
        
        print("🗑️ Starting badge system cleanup...")
        
        # 1. Remove badges field from all users
        print("📝 Removing badges field from user documents...")
        result = db.users.update_many(
            {"badges": {"$exists": True}},
            {"$unset": {"badges": ""}}
        )
        print(f"   Updated {result.modified_count} user documents")
        
        # 2. Drop the badges collection entirely
        print("🗂️ Dropping badges collection...")
        db.badges.drop()
        print("   Badges collection removed")
        
        # 3. Clean up any admin logs related to badge operations
        print("📋 Cleaning up badge-related admin logs...")
        badge_log_result = db.admin_logs.delete_many({
            "$or": [
                {"action": {"$regex": "BADGE", "$options": "i"}},
                {"action": {"$regex": "badge", "$options": "i"}}
            ]
        })
        print(f"   Removed {badge_log_result.deleted_count} badge-related admin log entries")
        
        print("\n✅ Badge system cleanup completed successfully!")
        print("\nSummary:")
        print(f"   - Modified {result.modified_count} user documents")
        print(f"   - Dropped badges collection")
        print(f"   - Removed {badge_log_result.deleted_count} badge-related logs")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("Badge System Cleanup Tool")
    print("=" * 50)
    
    # Confirm before proceeding
    response = input("\n⚠️  This will permanently remove ALL badge data from the database.\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        cleanup_badge_system()
    else:
        print("❌ Cleanup cancelled.")
        sys.exit(0)