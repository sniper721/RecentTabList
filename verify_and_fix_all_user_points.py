#!/usr/bin/env python3
"""
Comprehensive script to verify and fix all user points with the new formula
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using corrected exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.965)^(x-1) where x is the placement of the level on the list
    return round(250 * (0.965 ** (position - 1)), 2)

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0.0
    
    # Full completion (100% points)
    if record['progress'] == 100:
        return float(level['points'])
    
    # Partial completion - 10% of full points when reaching minimum percentage
    min_percentage = level.get('min_percentage', 100)
    if record['progress'] >= min_percentage and min_percentage < 100:
        return round(float(level['points']) * 0.1, 2)  # 10% of full points
    
    return 0.0

def main():
    print("🔍 Comprehensive user points verification and fix...")
    
    # Connect to MongoDB
    try:
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000
        )
        mongo_db = mongo_client[mongodb_db]
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return
    
    # First, verify all level points are correct
    print("\n🔍 Step 1: Verifying all level points...")
    levels = list(mongo_db.levels.find({}))
    level_fixes = 0
    
    for level in levels:
        position = level.get("position", 0)
        is_legacy = level.get("is_legacy", False)
        current_points = level.get("points", 0)
        correct_points = calculate_level_points(position, is_legacy)
        
        if abs(current_points - correct_points) > 0.01:
            print(f"  🔧 Fixing level '{level['name']}' at #{position}: {current_points} → {correct_points}")
            mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {"points": correct_points}}
            )
            level_fixes += 1
    
    if level_fixes > 0:
        print(f"✅ Fixed {level_fixes} level point values")
    else:
        print("✅ All level points are correct")
    
    # Reload levels with correct points
    levels = list(mongo_db.levels.find({}))
    level_lookup = {str(level['_id']): level for level in levels}
    
    # Now verify and fix all user points
    print("\n🔍 Step 2: Verifying all user points...")
    users = list(mongo_db.users.find({}))
    print(f"📊 Checking {len(users)} users...")
    
    users_with_issues = []
    users_fixed = 0
    total_points_corrected = 0.0
    
    for user in users:
        user_id = user['_id']
        username = user.get('username', 'Unknown')
        current_points = user.get('points', 0.0)
        
        # Get all approved records for this user
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        # Calculate correct total points
        correct_total_points = 0.0
        record_details = []
        
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            
            if level:
                points = calculate_record_points(record, level)
                correct_total_points += points
                if points > 0:
                    record_details.append({
                        'level_name': level['name'],
                        'position': level.get('position', '?'),
                        'progress': record['progress'],
                        'points': points
                    })
        
        # Round to 2 decimal places
        correct_total_points = round(correct_total_points, 2)
        
        # Check if points are incorrect
        if abs(correct_total_points - current_points) > 0.01:
            users_with_issues.append({
                'username': username,
                'user_id': user_id,
                'current_points': current_points,
                'correct_points': correct_total_points,
                'difference': correct_total_points - current_points,
                'record_count': len([r for r in record_details if r['points'] > 0]),
                'records': record_details[:5]  # Show first 5 records
            })
    
    # Display and fix issues
    if users_with_issues:
        print(f"\n❌ Found {len(users_with_issues)} users with incorrect points:")
        
        for user_issue in users_with_issues:
            print(f"\n👤 {user_issue['username']}:")
            print(f"   Current: {user_issue['current_points']} points")
            print(f"   Correct: {user_issue['correct_points']} points")
            print(f"   Difference: {user_issue['difference']:+.2f}")
            print(f"   Records: {user_issue['record_count']} approved completions")
            
            # Show some record details
            if user_issue['records']:
                print(f"   Top records:")
                for record in user_issue['records']:
                    print(f"     #{record['position']}: {record['level_name']} ({record['progress']}%) = {record['points']} pts")
            
            # Fix the user's points
            result = mongo_db.users.update_one(
                {"_id": user_issue['user_id']},
                {"$set": {"points": user_issue['correct_points']}}
            )
            
            if result.modified_count > 0:
                users_fixed += 1
                total_points_corrected += user_issue['difference']
                print(f"   ✅ FIXED")
            else:
                print(f"   ❌ FAILED TO FIX")
        
        print(f"\n🎉 Summary:")
        print(f"   Users fixed: {users_fixed}/{len(users_with_issues)}")
        print(f"   Total points corrected: {total_points_corrected:+.2f}")
        
    else:
        print("✅ All user points are correct!")
    
    # Final verification - show top 10 users
    print(f"\n🏆 Top 10 users after verification/fixes:")
    top_users = list(mongo_db.users.find({}).sort("points", -1).limit(10))
    
    for i, user in enumerate(top_users, 1):
        username = user.get('username', 'Unknown')
        points = user.get('points', 0)
        print(f"  #{i}: {username} - {points} points")
    
    # Verify a few users manually by recalculating their points
    print(f"\n🔍 Manual verification of top 3 users:")
    for user in top_users[:3]:
        user_id = user['_id']
        username = user.get('username', 'Unknown')
        stored_points = user.get('points', 0)
        
        # Recalculate manually
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        manual_total = 0.0
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            if level:
                manual_total += calculate_record_points(record, level)
        
        manual_total = round(manual_total, 2)
        
        if abs(manual_total - stored_points) < 0.01:
            print(f"  ✅ {username}: {stored_points} points (verified)")
        else:
            print(f"  ❌ {username}: {stored_points} stored vs {manual_total} calculated")

if __name__ == "__main__":
    main()