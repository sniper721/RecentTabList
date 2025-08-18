#!/usr/bin/env python3
"""
Add test country data to existing users for demonstration
"""

import pymongo
import random
from datetime import datetime
import os

# Get MongoDB connection from environment or use the same as main app
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://spinerspinerreal:EfitlEyLK6Rx8jb2@rtl.mongocluster.cosmos.azure.com/?retryWrites=true&w=majority&appName=RTL')

try:
    client = pymongo.MongoClient(MONGODB_URI)
    # Test connection
    client.admin.command('ping')
    db = client.rtl_database
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Using alternative connection method...")
    try:
        # Alternative connection without SRV
        client = pymongo.MongoClient("mongodb://spinerspinerreal:EfitlEyLK6Rx8jb2@rtl.mongocluster.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=RTL")
        client.admin.command('ping')
        db = client.rtl_database
        print("✅ Connected with alternative method")
    except Exception as e2:
        print(f"❌ Alternative connection also failed: {e2}")
        print("Please check your MongoDB connection settings")
        exit(1)

def add_test_countries():
    """Add countries to existing users for testing"""
    
    # Sample countries with their codes
    countries = [
        'US', 'CA', 'GB', 'DE', 'FR', 'IT', 'ES', 'RU', 'CN', 'JP', 
        'KR', 'BR', 'MX', 'AU', 'IN', 'NL', 'SE', 'NO', 'PL', 'FI'
    ]
    
    # Get all users
    users = list(db.users.find())
    print(f"Found {len(users)} users")
    
    updated_count = 0
    
    for user in users:
        # Only update users who don't have a country set
        if not user.get('country'):
            # Assign random country
            country = random.choice(countries)
            
            # Update user with country
            db.users.update_one(
                {"_id": user['_id']},
                {"$set": {"country": country}}
            )
            
            print(f"Updated {user['username']} with country: {country}")
            updated_count += 1
    
    print(f"\n✅ Updated {updated_count} users with countries!")
    
    # Show country distribution
    print("\n📊 Country Distribution:")
    country_stats = list(db.users.aggregate([
        {"$match": {"country": {"$exists": True, "$ne": ""}}},
        {"$group": {
            "_id": "$country",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]))
    
    for stat in country_stats:
        print(f"  {stat['_id']}: {stat['count']} users")

def create_sample_users_with_points():
    """Create some sample users with points for testing"""
    
    sample_users = [
        {"username": "speedrunner_us", "country": "US", "points": 1250, "nickname": "Speed King"},
        {"username": "demon_slayer_jp", "country": "JP", "points": 980, "nickname": "Demon Slayer"},
        {"username": "geometry_master_de", "country": "DE", "points": 875, "nickname": "Geo Master"},
        {"username": "dash_legend_gb", "country": "GB", "points": 750, "nickname": "Dash Legend"},
        {"username": "cube_crusher_ca", "country": "CA", "points": 650, "nickname": "Cube Crusher"},
        {"username": "level_lord_fr", "country": "FR", "points": 580, "nickname": "Level Lord"},
        {"username": "jump_genius_au", "country": "AU", "points": 520, "nickname": "Jump Genius"},
        {"username": "spike_survivor_se", "country": "SE", "points": 480, "nickname": "Spike Survivor"},
        {"username": "orb_collector_br", "country": "BR", "points": 420, "nickname": "Orb Collector"},
        {"username": "portal_pro_nl", "country": "NL", "points": 380, "nickname": "Portal Pro"}
    ]
    
    created_count = 0
    
    for user_data in sample_users:
        # Check if user already exists
        existing = db.users.find_one({"username": user_data["username"]})
        if not existing:
            # Create new user
            user_doc = {
                "username": user_data["username"],
                "nickname": user_data["nickname"],
                "email": f"{user_data['username']}@example.com",
                "password_hash": "dummy_hash_for_demo",
                "country": user_data["country"],
                "points": user_data["points"],
                "date_joined": datetime.now(),
                "is_admin": False,
                "public_profile": True
            }
            
            result = db.users.insert_one(user_doc)
            print(f"Created user: {user_data['username']} ({user_data['country']}) - {user_data['points']} points")
            created_count += 1
        else:
            # Update existing user with country and points
            db.users.update_one(
                {"_id": existing['_id']},
                {"$set": {
                    "country": user_data["country"],
                    "points": user_data["points"],
                    "nickname": user_data["nickname"]
                }}
            )
            print(f"Updated user: {user_data['username']} ({user_data['country']}) - {user_data['points']} points")
            created_count += 1
    
    print(f"\n✅ Processed {created_count} sample users!")

if __name__ == "__main__":
    print("🌍 Adding test country data...")
    print("=" * 50)
    
    # Add countries to existing users
    add_test_countries()
    
    print("\n" + "=" * 50)
    
    # Create sample users with points
    create_sample_users_with_points()
    
    print("\n🎉 Test data added successfully!")
    print("\nNow you can:")
    print("1. Visit http://127.0.0.1:10000/world to see the world leaderboard")
    print("2. Click on countries to see country-specific leaderboards")
    print("3. Check user settings to set your own country")
    print("4. View the beautiful world map interface!")