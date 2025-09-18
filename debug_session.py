#!/usr/bin/env python3
"""
Debug script to check session variables
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import mongo_db, app
    from flask import session
    import traceback
    
    print("Checking session variables...")
    
    # Let's manually check what would be in the session for ENGINE user
    user = mongo_db.users.find_one({"username": "ENGINE"})
    if user:
        print(f"User found: {user['username']}")
        print(f"is_admin from DB: {user.get('is_admin', False)}")
        print(f"head_admin from DB: {user.get('head_admin', False)}")
    else:
        print("User ENGINE not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()