#!/usr/bin/env python3
"""
Script to make a user a head admin
Usage: python make_head_admin.py <user_id>
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import mongo_db
    
    if len(sys.argv) != 2:
        print("Usage: python make_head_admin.py <user_id>")
        print("\nCurrent admin users:")
        admin_users = list(mongo_db.users.find({"is_admin": True}))
        for user in admin_users:
            print(f"  - {user['username']} (ID: {user['_id']})")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    
    # Find the user
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        print(f"User with ID {user_id} not found")
        sys.exit(1)
    
    # Make the user a head admin
    result = mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"head_admin": True}}
    )
    
    if result.modified_count > 0:
        print(f"✅ {user['username']} (ID: {user_id}) is now a head admin!")
    else:
        print(f"⚠️  No changes made for {user['username']} (ID: {user_id})")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()