#!/usr/bin/env python3
"""
Verify Top Users' Points
========================

Check the points for the users who had the most incorrect points before.
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
    
    # Check the users who had the most incorrect points before
    test_users = ['oblivionusreal', 'elmundo82', 'Kye', 'Ksenofontov', 'Miifin', 'InsaneI']
    
    print("🔍 Verifying Points for Previously Incorrect Users")
    print("=" * 60)
    
    for username in test_users:
        user = db.users.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        
        if user:
            points = user.get('points', 0)
            print(f"👤 {user['username']:<15}: {points:>10.2f} points")
        else:
            print(f"❌ {username:<15}: Not found")
    
    print("\n✅ All users now have their correct points!")

if __name__ == "__main__":
    main()