#!/usr/bin/env python3
"""
Script to list users and their IDs
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import mongo_db
    
    print("Current users:")
    users = list(mongo_db.users.find({}, {"username": 1, "_id": 1}))
    for user in users:
        print(f"  - {user['username']} (ID: {user['_id']})")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()