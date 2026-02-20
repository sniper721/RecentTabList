#!/usr/bin/env python3
"""
Verification script to confirm the new points formula is working correctly
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
    # p = 250(0.963655)^(x-1) where x is the placement of the level on the list
    # Position 1 = 250(0.963655)^0 = 250 points
    # Position 100 = 250(0.963655)^99 = 6.4 points
    return round(250 * (0.9636550814213581 ** (position - 1)), 2)

def main():
    print("Connecting to MongoDB...")
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db]
    
    print("\n=== VERIFICATION: New Points Formula ===")
    print("Formula: p = 250 * (0.963655)^(position-1)")
    print()
    
    # Check key positions
    key_positions = [1, 10, 25, 50, 75, 100, 125, 150]
    print("Key Position Verification:")
    print("Position | Expected | Actual | Match")
    print("---------|----------|--------|------")
    
    all_match = True
    for pos in key_positions:
        expected = calculate_level_points(pos)
        level = db.levels.find_one({"position": pos, "is_legacy": {"$ne": True}})
        if level:
            actual = level.get('points', 0)
            match = "✓" if abs(expected - actual) < 0.01 else "✗"
            if match == "✗":
                all_match = False
            print(f"   #{pos:3d}   | {expected:7.2f} | {actual:6.2f} | {match}")
        else:
            print(f"   #{pos:3d}   | {expected:7.2f} |  MISSING  | ✗")
            all_match = False
    
    print()
    if all_match:
        print("✅ ALL KEY POSITIONS MATCH THE NEW FORMULA!")
    else:
        print("❌ SOME POSITIONS DON'T MATCH - RECALCULATION MAY BE NEEDED")
    
    # Check top users and their points
    print("\n=== TOP USERS WITH NEW POINTS ===")
    top_users = list(db.users.find({}).sort("points", -1).limit(10))
    print("Rank | Username | Points")
    print("-----|----------|-------")
    for i, user in enumerate(top_users, 1):
        print(f"  {i:2d} | {user.get('username', 'Unknown'):12s} | {user.get('points', 0):.2f}")
    
    # Check a few specific examples
    print("\n=== SPECIFIC LEVEL EXAMPLES ===")
    example_levels = [
        {"name": "Femboy Temple", "position": 100},
        {"name": "kaotik", "position": 2},
        {"name": "projectflame", "position": 3}
    ]
    
    for level_info in example_levels:
        level = db.levels.find_one({"name": level_info["name"]})
        if level:
            pos = level.get('position', 0)
            expected = calculate_level_points(pos)
            actual = level.get('points', 0)
            print(f"{level_info['name']} (#{pos}): Expected {expected:.2f}, Actual {actual:.2f} - {'✓' if abs(expected - actual) < 0.01 else '✗'}")

if __name__ == "__main__":
    main()