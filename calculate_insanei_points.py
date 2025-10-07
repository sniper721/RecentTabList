#!/usr/bin/env python3
"""
Calculate InsaneI's Correct Points
=================================

This script calculates what InsaneI's points should be based on:
1. All their approved records
2. Current level positions and points
3. The points calculation formula

Does NOT check their current points - only calculates what they should have.
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
    # p = 250(0.9475)^(position-1)
    return round(250 * (0.9475 ** (position - 1)), 2)

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
        return round(float(level['points']) * 0.1, 2)
    
    return 0.0

def calculate_insanei_points():
    """Calculate InsaneI's correct points"""
    print("🧮 Calculating InsaneI's Correct Points")
    print("=" * 50)
    
    # Connect to database
    db = connect_to_database()
    
    # Find InsaneI user (case insensitive)
    user = db.users.find_one({"username": {"$regex": "^insanei$", "$options": "i"}})
    
    if not user:
        print("❌ User 'InsaneI' not found")
        return
    
    print(f"👤 Found user: {user['username']} (ID: {user['_id']})")
    
    # Get all approved records for InsaneI using aggregation
    pipeline = [
        {"$match": {"user_id": user['_id'], "status": "approved"}},
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
            "date_submitted": 1,
            "level.name": 1,
            "level.position": 1,
            "level.points": 1,
            "level.is_legacy": 1,
            "level.min_percentage": 1
        }},
        {"$sort": {"level.position": 1}}  # Sort by level position
    ]
    
    records_with_levels = list(db.records.aggregate(pipeline))
    
    if not records_with_levels:
        print("❌ No approved records found for InsaneI")
        return
    
    print(f"📊 Found {len(records_with_levels)} approved records")
    print("\n📋 Detailed Breakdown:")
    print("-" * 80)
    print(f"{'Level Name':<25} {'Pos':<4} {'Progress':<8} {'Level Points':<12} {'Earned Points':<12}")
    print("-" * 80)
    
    total_points = 0
    record_count = 0
    
    for record in records_with_levels:
        level = record['level']
        
        # Calculate what the level points should be based on current position
        expected_level_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        
        # Use the expected points for calculation (in case DB points are wrong)
        level_for_calc = dict(level)
        level_for_calc['points'] = expected_level_points
        
        record_with_status = {
            'progress': record['progress'],
            'status': record.get('status', 'approved')
        }
        
        points_earned = calculate_record_points(record_with_status, level_for_calc)
        total_points += points_earned
        record_count += 1
        
        # Format the output
        level_name = level['name'][:24] if len(level['name']) > 24 else level['name']
        position = f"#{level['position']}"
        progress = f"{record['progress']}%"
        level_points = f"{expected_level_points:.2f}"
        earned_points = f"{points_earned:.2f}"
        
        print(f"{level_name:<25} {position:<4} {progress:<8} {level_points:<12} {earned_points:<12}")
    
    print("-" * 80)
    print(f"{'TOTAL':<25} {'':<4} {f'{record_count} records':<8} {'':<12} {f'{total_points:.2f}':<12}")
    print("-" * 80)
    
    # Summary
    print(f"\n📈 CALCULATION SUMMARY")
    print(f"👤 User: {user['username']}")
    print(f"✅ Approved Records: {record_count}")
    print(f"🏆 Total Correct Points: {total_points:.2f}")
    
    # Additional statistics
    full_completions = sum(1 for r in records_with_levels if r['progress'] == 100)
    partial_completions = record_count - full_completions
    
    print(f"\n📊 Record Breakdown:")
    print(f"  • Full completions (100%): {full_completions}")
    print(f"  • Partial completions: {partial_completions}")
    
    if record_count > 0:
        avg_progress = sum(r['progress'] for r in records_with_levels) / record_count
        print(f"  • Average progress: {avg_progress:.1f}%")
    
    # Show top records by points
    print(f"\n🏆 Top 5 Records by Points:")
    sorted_records = sorted(records_with_levels, key=lambda r: calculate_record_points({
        'progress': r['progress'], 
        'status': 'approved'
    }, {
        'points': calculate_level_points(r['level']['position'], r['level'].get('is_legacy', False)),
        'is_legacy': r['level'].get('is_legacy', False),
        'min_percentage': r['level'].get('min_percentage', 100)
    }), reverse=True)
    
    for i, record in enumerate(sorted_records[:5], 1):
        level = record['level']
        expected_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        earned = calculate_record_points({
            'progress': record['progress'], 
            'status': 'approved'
        }, {
            'points': expected_points,
            'is_legacy': level.get('is_legacy', False),
            'min_percentage': level.get('min_percentage', 100)
        })
        print(f"  {i}. {level['name']} (#{level['position']}) - {record['progress']}% = {earned:.2f} points")
    
    return total_points

if __name__ == "__main__":
    try:
        total = calculate_insanei_points()
        if total is not None:
            print(f"\n🎯 FINAL ANSWER: InsaneI should have {total:.2f} points")
    except KeyboardInterrupt:
        print("\n\n⚠️  Calculation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)