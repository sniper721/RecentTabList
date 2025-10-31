#!/usr/bin/env python3
"""
Final comprehensive verification of all points and systems
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

def main():
    print("🎯 FINAL COMPREHENSIVE VERIFICATION")
    print("=" * 50)
    
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
    
    # 1. Verify formula correctness
    print(f"\n1️⃣ FORMULA VERIFICATION")
    print(f"Formula: p = 250(0.965)^(x-1)")
    
    key_positions = [1, 50, 100, 150]
    expected_values = [250.0, 43.63, 7.35, 1.24]
    
    formula_correct = True
    for pos, expected in zip(key_positions, expected_values):
        calculated = calculate_level_points(pos)
        if abs(calculated - expected) < 0.5:  # Allow small rounding differences
            print(f"  ✅ Position #{pos}: {calculated} points (target: ~{expected})")
        else:
            print(f"  ❌ Position #{pos}: {calculated} points (target: ~{expected})")
            formula_correct = False
    
    # 2. Verify database structure
    print(f"\n2️⃣ DATABASE STRUCTURE VERIFICATION")
    
    main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
    total_count = main_count + legacy_count
    
    print(f"  📊 Main list levels: {main_count}")
    print(f"  📊 Legacy levels: {legacy_count}")
    print(f"  📊 Total levels: {total_count}")
    
    structure_correct = True
    if main_count == 150:
        print(f"  ✅ Main list has exactly 150 levels")
    else:
        print(f"  ❌ Main list should have 150 levels, has {main_count}")
        structure_correct = False
    
    # Check position ranges
    main_positions = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}, {"position": 1}).sort("position", 1))
    if main_positions:
        min_main = main_positions[0]["position"]
        max_main = main_positions[-1]["position"]
        
        if min_main == 1 and max_main == 150:
            print(f"  ✅ Main list positions: 1-150")
        else:
            print(f"  ❌ Main list positions: {min_main}-{max_main} (should be 1-150)")
            structure_correct = False
    
    legacy_positions = list(mongo_db.levels.find({"is_legacy": True}, {"position": 1}).sort("position", 1))
    if legacy_positions:
        min_legacy = legacy_positions[0]["position"]
        if min_legacy >= 151:
            print(f"  ✅ Legacy starts at position {min_legacy}")
        else:
            print(f"  ❌ Legacy starts at position {min_legacy} (should be ≥151)")
            structure_correct = False
    
    # 3. Verify level points
    print(f"\n3️⃣ LEVEL POINTS VERIFICATION")
    
    levels = list(mongo_db.levels.find({}))
    level_issues = 0
    
    for level in levels:
        position = level.get("position", 0)
        is_legacy = level.get("is_legacy", False)
        current_points = level.get("points", 0)
        correct_points = calculate_level_points(position, is_legacy)
        
        if abs(current_points - correct_points) > 0.01:
            level_issues += 1
    
    if level_issues == 0:
        print(f"  ✅ All {len(levels)} level points are correct")
    else:
        print(f"  ❌ {level_issues} levels have incorrect points")
    
    # 4. Verify user points (sample check)
    print(f"\n4️⃣ USER POINTS VERIFICATION (Sample)")
    
    # Create level lookup
    level_lookup = {str(level['_id']): level for level in levels}
    
    # Check top 10 users
    top_users = list(mongo_db.users.find({}).sort("points", -1).limit(10))
    user_issues = 0
    
    for user in top_users:
        user_id = user['_id']
        username = user.get('username', 'Unknown')
        current_points = user.get('points', 0.0)
        
        # Calculate expected points
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        expected_total = 0.0
        for record in records:
            level_id = str(record['level_id'])
            level = level_lookup.get(level_id)
            if level:
                level_points = calculate_level_points(level.get("position", 0), level.get("is_legacy", False))
                
                if level.get('is_legacy', False):
                    points = 0.0
                elif record['progress'] == 100:
                    points = float(level_points)
                else:
                    min_percentage = level.get('min_percentage', 100)
                    if record['progress'] >= min_percentage and min_percentage < 100:
                        points = round(float(level_points) * 0.1, 2)
                    else:
                        points = 0.0
                
                expected_total += points
        
        expected_total = round(expected_total, 2)
        
        if abs(current_points - expected_total) < 0.01:
            print(f"  ✅ {username}: {current_points} points")
        else:
            print(f"  ❌ {username}: {current_points} vs expected {expected_total}")
            user_issues += 1
    
    # 5. System status summary
    print(f"\n5️⃣ SYSTEM STATUS SUMMARY")
    print(f"=" * 30)
    
    all_systems_good = formula_correct and structure_correct and level_issues == 0 and user_issues == 0
    
    if formula_correct:
        print(f"  ✅ Points formula: CORRECT")
    else:
        print(f"  ❌ Points formula: NEEDS FIX")
    
    if structure_correct:
        print(f"  ✅ Database structure: CORRECT")
    else:
        print(f"  ❌ Database structure: NEEDS FIX")
    
    if level_issues == 0:
        print(f"  ✅ Level points: ALL CORRECT")
    else:
        print(f"  ❌ Level points: {level_issues} NEED FIX")
    
    if user_issues == 0:
        print(f"  ✅ User points (sample): ALL CORRECT")
    else:
        print(f"  ❌ User points (sample): {user_issues} NEED FIX")
    
    print(f"\n🎯 FINAL VERDICT:")
    if all_systems_good:
        print(f"🎉 ALL SYSTEMS PERFECT! 150-level extension is complete and working flawlessly!")
    else:
        print(f"⚠️  Some issues detected. Admin recalculate function will fix remaining problems.")
        if user_issues > 0:
            print(f"💡 Run the admin recalculate points function to fix user point discrepancies.")
    
    print(f"\n📊 FINAL STATISTICS:")
    print(f"  • Main list: {main_count} levels (positions 1-150)")
    print(f"  • Legacy list: {legacy_count} levels (positions 151+)")
    print(f"  • Total users: {len(list(mongo_db.users.find({})))} users")
    print(f"  • Formula: p = 250(0.965)^(x-1) ✅")
    print(f"  • Top 1 points: {calculate_level_points(1)} ✅")

if __name__ == "__main__":
    main()