#!/usr/bin/env python3
"""
Script to extend the main list to 150 levels and update points formula.
This will:
1. Move the top 50 legacy levels to the main list (positions 101-150)
2. Update all level points using the new formula: p = 250(0.965)^x
3. Recalculate all user points
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
    print("🚀 Starting main list extension to 150 levels...")
    
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
    
    # Step 1: Get current main list count
    main_list_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    print(f"📊 Current main list has {main_list_count} levels")
    
    # Step 2: Get top 50 legacy levels (sorted by position, which represents their legacy ranking)
    legacy_levels = list(mongo_db.levels.find({
        "is_legacy": True
    }).sort("position", 1).limit(50))
    
    print(f"📊 Found {len(legacy_levels)} legacy levels to potentially move")
    
    # Step 3: Move top 50 legacy levels to main list (positions 101-150)
    moved_count = 0
    for i, level in enumerate(legacy_levels):
        new_position = 101 + i  # Positions 101-150
        if new_position <= 150:
            # Calculate new points
            new_points = calculate_level_points(new_position, is_legacy=False)
            
            # Update the level
            result = mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {
                    "is_legacy": False,
                    "position": new_position,
                    "points": new_points
                }}
            )
            
            if result.modified_count > 0:
                moved_count += 1
                print(f"✅ Moved '{level['name']}' to position #{new_position} ({new_points} points)")
            else:
                print(f"⚠️  Failed to move '{level['name']}'")
    
    print(f"🎉 Successfully moved {moved_count} levels from legacy to main list")
    
    # Step 4: Update points for all existing main list levels (1-100) with new formula
    main_levels = list(mongo_db.levels.find({
        "is_legacy": {"$ne": True},
        "position": {"$lte": 100}
    }))
    
    updated_count = 0
    for level in main_levels:
        position = level["position"]
        new_points = calculate_level_points(position, is_legacy=False)
        old_points = level.get("points", 0)
        
        if abs(new_points - old_points) > 0.01:  # Only update if points changed significantly
            result = mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {"points": new_points}}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"🔄 Updated '{level['name']}' at position #{position}: {old_points} → {new_points} points")
    
    print(f"🎉 Updated points for {updated_count} existing main list levels")
    
    # Step 5: Shift remaining legacy levels to start at position 151
    remaining_legacy = list(mongo_db.levels.find({
        "is_legacy": True
    }).sort("position", 1))
    
    legacy_updated = 0
    for i, level in enumerate(remaining_legacy):
        new_position = 151 + i  # Start legacy at position 151
        
        result = mongo_db.levels.update_one(
            {"_id": level["_id"]},
            {"$set": {
                "position": new_position,
                "points": 0.0  # Legacy levels have 0 points
            }}
        )
        
        if result.modified_count > 0:
            legacy_updated += 1
    
    print(f"🔄 Updated positions for {legacy_updated} remaining legacy levels")
    
    # Step 6: Show summary of new points distribution
    print("\n📈 New points distribution:")
    sample_positions = [1, 10, 25, 50, 75, 100, 125, 150]
    for pos in sample_positions:
        points = calculate_level_points(pos)
        print(f"  Position #{pos}: {points} points")
    
    # Step 7: Final verification
    final_main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    final_legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
    
    print(f"\n🎯 Final summary:")
    print(f"  Main list levels: {final_main_count}")
    print(f"  Legacy levels: {final_legacy_count}")
    print(f"  Total levels: {final_main_count + final_legacy_count}")
    
    print("\n✅ Main list extension completed successfully!")
    print("⚠️  Note: You should run a user points recalculation to update all user scores with the new point values.")

if __name__ == "__main__":
    main()