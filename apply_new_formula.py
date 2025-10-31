#!/usr/bin/env python3
"""
Apply the new formula to all existing levels and recalculate user points
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, mongo_db, calculate_level_points
from real_time_points_system import RealTimePointsManager
from datetime import datetime, timezone

def apply_new_formula():
    """Apply the new formula to all levels and recalculate user points"""
    
    print("🚀 Applying New Formula: 250 * (0.9475)^(position-1)")
    print("=" * 55)
    
    try:
        # Step 1: Update all level points with the new formula
        print("📊 Step 1: Updating level points...")
        
        levels = list(mongo_db.levels.find({}, {"_id": 1, "name": 1, "position": 1, "is_legacy": 1, "points": 1}))
        levels_updated = 0
        
        for level in levels:
            position = level.get("position", 1)
            is_legacy = level.get("is_legacy", False)
            current_points = level.get("points", 0)
            
            # Calculate new points
            new_points = calculate_level_points(position, is_legacy)
            
            # Update if different (with small tolerance for floating point)
            if abs(current_points - new_points) > 0.01:
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": new_points}}
                )
                levels_updated += 1
                
                print(f"  • {level['name']} (#{position}): {current_points} → {new_points} points")
        
        print(f"✅ Updated {levels_updated} levels with new formula")
        
        # Step 2: Recalculate all user points
        print("\n👥 Step 2: Recalculating user points...")
        
        # Use the real-time points system for accurate recalculation
        manager = RealTimePointsManager(mongo_db)
        users_updated = manager.recalculate_all_user_points()
        
        print(f"✅ Recalculated points for {users_updated} users")
        
        # Step 3: Show some examples of the new formula
        print("\n📈 Step 3: New Formula Examples:")
        print("Position | Points")
        print("-" * 20)
        
        example_positions = [1, 2, 3, 5, 10, 20, 50, 75, 100, 150]
        for pos in example_positions:
            points = calculate_level_points(pos, False)
            print(f"#{pos:3d}      | {points:6.2f}")
        
        print(f"\n🎉 Formula update complete!")
        print(f"📊 Summary:")
        print(f"  • Updated {levels_updated} level point values")
        print(f"  • Recalculated points for {users_updated} users")
        print(f"  • New formula: 250 * (0.9475)^(position-1)")
        print(f"  • Position #1 = 250.00 points")
        print(f"  • Position #150 = 0.01 points")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying new formula: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_formula_application():
    """Verify that the formula has been applied correctly"""
    
    print("\n🔍 Verifying Formula Application...")
    print("=" * 35)
    
    try:
        # Check a few random levels
        sample_levels = list(mongo_db.levels.find(
            {"is_legacy": {"$ne": True}}, 
            {"name": 1, "position": 1, "points": 1}
        ).limit(10))
        
        all_correct = True
        
        for level in sample_levels:
            position = level.get("position", 1)
            current_points = level.get("points", 0)
            expected_points = calculate_level_points(position, False)
            
            if abs(current_points - expected_points) > 0.01:
                print(f"❌ {level['name']} (#{position}): Expected {expected_points}, got {current_points}")
                all_correct = False
            else:
                print(f"✅ {level['name']} (#{position}): {current_points} points")
        
        if all_correct:
            print("\n✅ All sampled levels have correct points!")
        else:
            print("\n❌ Some levels have incorrect points!")
        
        return all_correct
        
    except Exception as e:
        print(f"❌ Error verifying formula: {e}")
        return False

def main():
    """Main function"""
    
    print("🔧 RTL Points Formula Update Tool")
    print("=" * 40)
    print("This will update all levels to use the new formula:")
    print("OLD: 250 * (0.965)^(position-1)")
    print("NEW: 250 * (0.9475)^(position-1)")
    print()
    
    # Apply the new formula
    success = apply_new_formula()
    
    if success:
        # Verify the application
        verify_success = verify_formula_application()
        
        if verify_success:
            print("\n🎉 SUCCESS! New formula has been applied and verified.")
            print("\n📋 What changed:")
            print("  • All level points recalculated with new formula")
            print("  • All user points recalculated based on new level points")
            print("  • Formula now gives slightly lower points overall")
            print("  • Position #1 still = 250 points (unchanged)")
            print("  • Lower positions now give fewer points")
        else:
            print("\n⚠️ Formula applied but verification failed. Please check manually.")
    else:
        print("\n❌ Failed to apply new formula. Please check the error messages above.")

if __name__ == "__main__":
    main()