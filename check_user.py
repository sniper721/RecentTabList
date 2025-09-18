#!/usr/bin/env python3
"""
Script to check user ENGINE's admin status
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import mongo_db
    
    # Find the ENGINE user
    user = mongo_db.users.find_one({"username": "ENGINE"}, {"head_admin": 1, "is_admin": 1})
    
    if user:
        is_admin = user.get("is_admin", False)
        head_admin = user.get("head_admin", False)
        print(f"User: ENGINE")
        print(f"is_admin: {is_admin}")
        print(f"head_admin: {head_admin}")
    else:
        print("User ENGINE not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()