#!/usr/bin/env python3
"""
Check InsaneI's Current Points in Database
==========================================
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def main():
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    # Find InsaneI
    user = db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
    
    if user:
        print(f"👤 User: {user['username']}")
        print(f"🏆 Current Points in DB: {user.get('points', 'No points field')}")
        print(f"📊 Should Have: 2214.91 points")
        
        current = float(user.get('points', 0))
        should_have = 2214.91
        difference = should_have - current
        
        print(f"📈 Difference: {difference:+.2f} points")
        
        if abs(difference) > 0.01:
            print("❌ Points are INCORRECT!")
            return False
        else:
            print("✅ Points are correct!")
            return True
    else:
        print("❌ InsaneI not found")
        return False

if __name__ == "__main__":
    main()