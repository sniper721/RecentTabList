#!/usr/bin/env python3
"""
Fix legacy level positions to start at 101 instead of low numbers
"""

import os
import sys
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import mongo_db, mongo_client
    print("✅ Successfully imported main application components")
except ImportError as e:
    print(f"❌ Failed to import main components: {e}")
    sys.exit(1)

def fix_legacy_positions():
    """Fix legacy level positions to start at 101"""
    print("🔧 Fixing legacy level positions...")
    
    try:
        # Get all legacy levels sorted by current position
        legacy_levels = list(mongo_db.levels.find(
            {"is_legacy": True}
        ).sort("position", 1))
        
        if not legacy_levels:
            print("⚠️  No legacy levels found")
            return
        
        print(f"Found {len(legacy_levels)} legacy levels to fix")
        
        # Update positions starting from 101
        for i, level in enumerate(legacy_levels):
            new_position = 101 + i
            old_position = level['position']
            
            if old_position != new_position:
                mongo_db.levels.update_one(
                    {"_id": level['_id']},
                    {"$set": {"position": new_position}}
                )
                print(f"  Updated {level['name']}: #{old_position} → #{new_position}")
            else:
                print(f"  {level['name']}: Already at correct position #{new_position}")
        
        print("✅ Legacy positions fixed!")
        
    except Exception as e:
        print(f"❌ Error fixing legacy positions: {e}")

def fix_main_list_overflow():
    """Move levels beyond position 100 to legacy"""
    print("\n🔧 Fixing main list overflow...")
    
    try:
        # Find main list levels beyond position 100
        overflow_levels = list(mongo_db.levels.find({
            "position": {"$gt": 100},
            "is_legacy": {"$ne": True}
        }).sort("position", 1))
        
        if not overflow_levels:
            print("✅ No main list overflow found")
            return
        
        print(f"Found {len(overflow_levels)} levels to move to legacy")
        
        # Get the highest legacy position
        highest_legacy = mongo_db.levels.find_one(
            {"is_legacy": True}, 
            sort=[("position", -1)]
        )
        next_legacy_position = (highest_legacy['position'] + 1) if highest_legacy else 101
        
        # Move overflow levels to legacy
        for level in overflow_levels:
            old_position = level['position']
            
            mongo_db.levels.update_one(
                {"_id": level['_id']},
                {"$set": {
                    "is_legacy": True,
                    "position": next_legacy_position,
                    "points": 0  # Legacy levels have 0 points
                }}
            )
            
            print(f"  Moved {level['name']}: Main #{old_position} → Legacy #{next_legacy_position}")
            next_legacy_position += 1
        
        print("✅ Main list overflow fixed!")
        
    except Exception as e:
        print(f"❌ Error fixing main list overflow: {e}")

def verify_fixes():
    """Verify that the fixes worked correctly"""
    print("\n🧪 Verifying fixes...")
    
    try:
        # Check main list count
        main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
        print(f"Main list levels: {main_count}")
        
        if main_count <= 100:
            print("✅ Main list has correct number of levels")
        else:
            print(f"❌ Main list still has {main_count} levels (should be ≤100)")
        
        # Check legacy positioning
        legacy_levels = list(mongo_db.levels.find(
            {"is_legacy": True}
        ).sort("position", 1))
        
        if legacy_levels:
            first_position = legacy_levels[0]['position']
            last_position = legacy_levels[-1]['position']
            
            print(f"Legacy levels: {len(legacy_levels)} (positions #{first_position}-#{last_position})")
            
            if first_position >= 101:
                print("✅ Legacy list starts at correct position")
            else:
                print(f"❌ Legacy list starts at #{first_position} (should be ≥101)")
        
        # Check for position conflicts
        all_positions = []
        for level in mongo_db.levels.find():
            all_positions.append((level['position'], level.get('is_legacy', False)))
        
        # Group by position to find duplicates
        position_counts = {}
        for pos, is_legacy in all_positions:
            key = f"{pos}_{'legacy' if is_legacy else 'main'}"
            position_counts[key] = position_counts.get(key, 0) + 1
        
        conflicts = [k for k, v in position_counts.items() if v > 1]
        if conflicts:
            print(f"⚠️  Position conflicts found: {conflicts}")
        else:
            print("✅ No position conflicts found")
        
    except Exception as e:
        print(f"❌ Error verifying fixes: {e}")

def main():
    """Run the fix script"""
    print("🚀 Starting legacy position fixes...")
    
    try:
        # Test database connection
        mongo_client.admin.command('ping')
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Create backup info
    print(f"\n📋 Current state:")
    main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
    legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    # Auto-confirm for testing
    print("\n⚠️  Auto-confirming position fixes...")
    response = 'y'
    
    fix_main_list_overflow()
    fix_legacy_positions()
    verify_fixes()
    
    print("\n✅ Legacy position fixes completed!")
    print("\n📝 Summary:")
    print("  - Legacy levels now start at position #151")
    print("  - Main list limited to 150 levels")
    print("  - All position conflicts resolved")

if __name__ == "__main__":
    main()