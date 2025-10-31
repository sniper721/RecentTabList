#!/usr/bin/env python3
"""
Script to verify the 150-level extension is working correctly
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
    """Calculate points based on position using new exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.965)^x where x is the placement of the level on the list
    return round(250 * (0.965 ** position), 2)

def main():
    print("🔍 Verifying 150-level extension...")
    
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
    
    # Check main list count
    main_list_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
    total_count = main_list_count + legacy_count
    
    print(f"\n📊 Level counts:")
    print(f"  Main list: {main_list_count}")
    print(f"  Legacy: {legacy_count}")
    print(f"  Total: {total_count}")
    
    # Verify main list positions 1-150
    main_levels = list(mongo_db.levels.find({
        "is_legacy": {"$ne": True}
    }).sort("position", 1))
    
    print(f"\n🔍 Verifying main list positions...")
    position_issues = []
    points_issues = []
    
    for i, level in enumerate(main_levels):
        expected_position = i + 1
        actual_position = level["position"]
        expected_points = calculate_level_points(actual_position)
        actual_points = level.get("points", 0)
        
        if actual_position != expected_position:
            position_issues.append(f"Position gap: expected {expected_position}, found {actual_position}")
        
        if abs(actual_points - expected_points) > 0.01:
            points_issues.append(f"Points mismatch at #{actual_position}: expected {expected_points}, found {actual_points}")
    
    if position_issues:
        print(f"❌ Position issues found:")
        for issue in position_issues[:5]:  # Show first 5
            print(f"  {issue}")
        if len(position_issues) > 5:
            print(f"  ... and {len(position_issues) - 5} more")
    else:
        print(f"✅ All main list positions are sequential (1-{main_list_count})")
    
    if points_issues:
        print(f"❌ Points issues found:")
        for issue in points_issues[:5]:  # Show first 5
            print(f"  {issue}")
        if len(points_issues) > 5:
            print(f"  ... and {len(points_issues) - 5} more")
    else:
        print(f"✅ All main list points match the new formula")
    
    # Check legacy list starts at position 151
    legacy_levels = list(mongo_db.levels.find({
        "is_legacy": True
    }).sort("position", 1))
    
    if legacy_levels:
        first_legacy_pos = legacy_levels[0]["position"]
        print(f"\n🔍 Legacy list verification:")
        print(f"  First legacy position: {first_legacy_pos}")
        print(f"  Legacy count: {len(legacy_levels)}")
        
        if first_legacy_pos == 151:
            print(f"✅ Legacy list starts at correct position (151)")
        else:
            print(f"❌ Legacy list should start at 151, but starts at {first_legacy_pos}")
    else:
        print(f"\n✅ No legacy levels found")
    
    # Show points distribution
    print(f"\n📈 Points distribution verification:")
    sample_positions = [1, 10, 25, 50, 75, 100, 125, 150]
    
    for pos in sample_positions:
        expected_points = calculate_level_points(pos)
        level = mongo_db.levels.find_one({"position": pos, "is_legacy": {"$ne": True}})
        
        if level:
            actual_points = level.get("points", 0)
            status = "✅" if abs(actual_points - expected_points) < 0.01 else "❌"
            print(f"  Position #{pos}: {actual_points} points (expected {expected_points}) {status}")
        else:
            print(f"  Position #{pos}: No level found ❌")
    
    # Show top levels in new positions 101-150
    print(f"\n🆕 New main list levels (positions 101-150):")
    new_main_levels = list(mongo_db.levels.find({
        "is_legacy": {"$ne": True},
        "position": {"$gte": 101, "$lte": 150}
    }).sort("position", 1).limit(10))
    
    for level in new_main_levels:
        pos = level["position"]
        name = level["name"]
        points = level.get("points", 0)
        print(f"  #{pos}: {name} ({points} points)")
    
    if len(new_main_levels) == 10:
        print(f"  ... and {50 - 10} more levels")
    
    print(f"\n🎉 Verification completed!")

if __name__ == "__main__":
    main()