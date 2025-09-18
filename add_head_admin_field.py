#!/usr/bin/env python3
"""
Migration script to add head_admin field to all existing users
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import mongo_db
    
    print("Adding head_admin field to all users...")
    
    # Update all users to add head_admin field (default False)
    result = mongo_db.users.update_many(
        {"head_admin": {"$exists": False}},
        {"$set": {"head_admin": False}}
    )
    
    print(f"Updated {result.modified_count} users with head_admin field")
    
    # Show current admin users
    admin_users = list(mongo_db.users.find({"is_admin": True}))
    print(f"\nCurrent admin users ({len(admin_users)}):")
    for user in admin_users:
        print(f"  - {user['username']} (ID: {user['_id']})")
    
    print("\n✅ Migration completed successfully!")
    print("\nTo make yourself a head admin, run:")
    print("  python make_head_admin.py <your_user_id>")
    
except Exception as e:
    print(f"❌ Error during migration: {e}")
    import traceback
    traceback.print_exc()