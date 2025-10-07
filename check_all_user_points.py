#!/usr/bin/env python3
"""
Check All User Points
====================

This script checks ALL users to see how many have incorrect points
compared to what they should have based on their approved records.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

def connect_to_database():
    """Connect to MongoDB database"""
    try:
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print(f"✅ Connected to database: {mongodb_db}")
        
        return db
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0.0
    return round(250 * (0.9475 ** (position - 1)), 2)

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0.0
    
    if record['progress'] == 100:
        return float(level['points'])
    
    min_percentage = level.get('min_percentage', 100)
    if record['progress'] >= min_percentage and min_percentage < 100:
        return round(float(level['points']) * 0.1, 2)
    
    return 0.0

def check_all_user_points():
    """Check all users' points for accuracy"""
    print("🔍 Checking All User Points for Accuracy")
    print("=" * 60)
    
    db = connect_to_database()
    
    # Get all users with points
    users = list(db.users.find({"points": {"$exists": True}}, {"_id": 1, "username": 1, "points": 1}))
    
    print(f"👥 Found {len(users)} users to check")
    print("\nChecking points accuracy...")
    
    incorrect_users = []
    correct_users = []
    users_with_no_records = []
    
    for i, user in enumerate(users, 1):
        if i % 10 == 0:
            print(f"  Processed {i}/{len(users)} users...")
        
        user_id = user['_id']
        current_points = user.get('points', 0)
        username = user.get('username', 'Unknown')
        
        # Calculate correct points using aggregation
        pipeline = [
            {"$match": {"user_id": user_id, "status": "approved"}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id", 
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$project": {
                "progress": 1,
                "status": 1,
                "level.points": 1,
                "level.is_legacy": 1,
                "level.min_percentage": 1,
                "level.position": 1
            }}
        ]
        
        records_with_levels = list(db.records.aggregate(pipeline))
        
        if not records_with_levels:
            if current_points != 0:
                users_with_no_records.append({
                    'username': username,
                    'current_points': current_points,
                    'should_be': 0
                })
            continue
        
        # Calculate correct total
        correct_total = 0
        for record in records_with_levels:
            level = record['level']
            # Use correct level points based on position
            expected_level_points = calculate_level_points(level['position'], level.get('is_legacy', False))
            level_for_calc = dict(level)
            level_for_calc['points'] = expected_level_points
            
            record_with_status = {
                'progress': record['progress'],
                'status': record.get('status', 'approved')
            }
            
            points_earned = calculate_record_points(record_with_status, level_for_calc)
            correct_total += points_earned
        
        correct_total = round(correct_total, 2)
        
        # Check if points are correct (with small tolerance for floating point)
        if abs(float(current_points) - float(correct_total)) > 0.01:
            incorrect_users.append({
                'username': username,
                'current_points': current_points,
                'correct_points': correct_total,
                'difference': correct_total - current_points,
                'records_count': len(records_with_levels)
            })
        else:
            correct_users.append(username)
    
    # Results
    print(f"\n📊 RESULTS:")
    print(f"✅ Users with correct points: {len(correct_users)}")
    print(f"❌ Users with incorrect points: {len(incorrect_users)}")
    print(f"⚠️  Users with no records but have points: {len(users_with_no_records)}")
    
    if incorrect_users:
        print(f"\n❌ TOP 10 USERS WITH MOST INCORRECT POINTS:")
        print("-" * 70)
        print(f"{'Username':<20} {'Current':<10} {'Should Be':<10} {'Difference':<12}")
        print("-" * 70)
        
        # Sort by absolute difference
        sorted_incorrect = sorted(incorrect_users, key=lambda x: abs(x['difference']), reverse=True)
        
        for user in sorted_incorrect[:10]:
            username = user['username'][:19] if len(user['username']) > 19 else user['username']
            current = f"{user['current_points']:.2f}"
            correct = f"{user['correct_points']:.2f}"
            diff = f"{user['difference']:+.2f}"
            print(f"{username:<20} {current:<10} {correct:<10} {diff:<12}")
    
    if users_with_no_records:
        print(f"\n⚠️  USERS WITH POINTS BUT NO RECORDS:")
        for user in users_with_no_records[:5]:
            print(f"  • {user['username']}: {user['current_points']} points (should be 0)")
    
    print(f"\n🎯 SUMMARY:")
    total_incorrect = len(incorrect_users) + len(users_with_no_records)
    print(f"Total users needing point correction: {total_incorrect}")
    print(f"Percentage of users with wrong points: {(total_incorrect/len(users)*100):.1f}%")
    
    return total_incorrect > 0

if __name__ == "__main__":
    try:
        needs_fix = check_all_user_points()
        if needs_fix:
            print(f"\n🚨 CONCLUSION: The points system needs a global recalculation!")
        else:
            print(f"\n✅ CONCLUSION: All user points are correct!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()