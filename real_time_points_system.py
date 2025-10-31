#!/usr/bin/env python3
"""
Real-time Points Recalculation System
=====================================

This module implements a comprehensive real-time points recalculation system that:
1. Recalculates all level points when positions change
2. Recalculates all user points when level points change
3. Handles cascading updates efficiently
4. Provides logging and monitoring

Usage:
    from real_time_points_system import RealTimePointsManager
    
    manager = RealTimePointsManager(mongo_db)
    manager.handle_level_position_change(level_id, old_position, new_position)
"""

from datetime import datetime, timezone
from pymongo import UpdateOne
import time

class RealTimePointsManager:
    def __init__(self, mongo_db):
        self.mongo_db = mongo_db
        
    def calculate_level_points(self, position, is_legacy=False):
        """Calculate points based on position using exponential formula"""
        if is_legacy:
            return 0.0
        # p = 250(0.9475)^(x-1) where x is the placement of the level on the list
        # Position 1 = 250(0.9475)^0 = 250 points
        return round(250 * (0.9475 ** (position - 1)), 2)
    
    def calculate_record_points(self, record, level):
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
    
    def recalculate_all_level_points(self):
        """Recalculate points for ALL levels based on their current positions"""
        print("🔄 Starting global level points recalculation...")
        start_time = time.time()
        
        try:
            # Get all levels sorted by position
            levels = list(self.mongo_db.levels.find({}, {
                "_id": 1, "position": 1, "is_legacy": 1, "points": 1, "name": 1
            }).sort("position", 1))
            
            # Prepare bulk operations
            bulk_operations = []
            levels_updated = 0
            
            for level in levels:
                new_points = self.calculate_level_points(
                    level['position'], 
                    level.get('is_legacy', False)
                )
                
                current_points = level.get('points', 0)
                if abs(float(current_points) - float(new_points)) > 0.01:
                    bulk_operations.append(
                        UpdateOne(
                            {"_id": level['_id']},
                            {"$set": {"points": new_points}}
                        )
                    )
                    levels_updated += 1
                    print(f"  📊 {level.get('name', 'Unknown')} (#{level['position']}): {current_points} → {new_points} points")
            
            # Execute bulk update if there are changes
            if bulk_operations:
                result = self.mongo_db.levels.bulk_write(bulk_operations)
                print(f"✅ Updated {result.modified_count} level point values")
            else:
                print("✅ All level points are already correct")
            
            elapsed = time.time() - start_time
            print(f"⏱️  Level points recalculation completed in {elapsed:.2f}s")
            
            return levels_updated
            
        except Exception as e:
            print(f"❌ Error in global level points recalculation: {e}")
            return 0
    
    def recalculate_all_user_points(self):
        """Recalculate points for ALL users based on their approved records"""
        print("🔄 Starting global user points recalculation...")
        start_time = time.time()
        
        try:
            # Get all users with points
            users = list(self.mongo_db.users.find({}, {"_id": 1, "username": 1, "points": 1}))
            users_updated = 0
            
            for user in users:
                old_points = user.get('points', 0)
                new_points = self.recalculate_user_points(user['_id'])
                
                if abs(float(old_points) - float(new_points)) > 0.01:
                    users_updated += 1
                    print(f"  👤 {user.get('username', 'Unknown')}: {old_points} → {new_points} points")
            
            elapsed = time.time() - start_time
            print(f"✅ User points recalculation completed in {elapsed:.2f}s")
            print(f"📊 Updated {users_updated} user point totals")
            
            return users_updated
            
        except Exception as e:
            print(f"❌ Error in global user points recalculation: {e}")
            return 0
    
    def recalculate_user_points(self, user_id):
        """Recalculate and update a single user's total points"""
        try:
            # Use aggregation to join records with levels
            pipeline = [
                {"$match": {
                    "user_id": user_id, 
                    "status": "approved",
                    "$or": [
                        {"hidden": {"$exists": False}},
                        {"hidden": False}
                    ]
                }},
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
                    "level.min_percentage": 1
                }}
            ]
            
            records_with_levels = list(self.mongo_db.records.aggregate(pipeline))
            total_points = 0
            
            for record in records_with_levels:
                level = record['level']
                record_with_status = {
                    'progress': record['progress'],
                    'status': record.get('status', 'approved')
                }
                points = self.calculate_record_points(record_with_status, level)
                total_points += points
            
            # Update user's total points
            self.mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"points": total_points}}
            )
            
            return total_points
            
        except Exception as e:
            print(f"❌ Error recalculating points for user {user_id}: {e}")
            return 0
    
    def handle_level_position_change(self, level_id, old_position, new_position, admin_username="System"):
        """
        Handle a level position change with full real-time recalculation
        This is the main function to call when a level moves positions
        """
        print(f"🔄 Handling level position change: #{old_position} → #{new_position}")
        start_time = time.time()
        
        try:
            # Step 1: Update the level's position and points
            level = self.mongo_db.levels.find_one({"_id": level_id})
            if not level:
                print(f"❌ Level {level_id} not found")
                return False
            
            old_points = level.get('points', 0)
            new_points = self.calculate_level_points(new_position, level.get('is_legacy', False))
            
            # Update the level
            self.mongo_db.levels.update_one(
                {"_id": level_id},
                {"$set": {"position": new_position, "points": new_points}}
            )
            
            print(f"📊 Level '{level.get('name', 'Unknown')}' points: {old_points} → {new_points}")
            
            # Step 2: Recalculate ALL level points (since positions may have shifted)
            levels_updated = self.recalculate_all_level_points()
            
            # Step 3: Recalculate ALL user points (since level points changed)
            users_updated = self.recalculate_all_user_points()
            
            # Step 4: Log the change
            self.log_position_change(level_id, old_position, new_position, admin_username)
            
            elapsed = time.time() - start_time
            print(f"✅ Position change completed in {elapsed:.2f}s")
            print(f"📈 Summary: {levels_updated} levels updated, {users_updated} users updated")
            
            return True
            
        except Exception as e:
            print(f"❌ Error handling level position change: {e}")
            return False
    
    def handle_level_addition(self, level_id, position):
        """Handle adding a new level at a specific position"""
        print(f"➕ Handling new level addition at position #{position}")
        
        try:
            # Shift all levels at or after this position down by 1
            self.mongo_db.levels.update_many(
                {"position": {"$gte": position}, "is_legacy": {"$ne": True}},
                {"$inc": {"position": 1}}
            )
            
            # Recalculate all points
            self.recalculate_all_level_points()
            self.recalculate_all_user_points()
            
            print(f"✅ New level addition handled successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error handling level addition: {e}")
            return False
    
    def handle_level_removal(self, level_id):
        """Handle removing a level from the list"""
        print(f"➖ Handling level removal")
        
        try:
            # Get the level's position before removal
            level = self.mongo_db.levels.find_one({"_id": level_id})
            if not level:
                return False
            
            position = level['position']
            
            # Remove the level
            self.mongo_db.levels.delete_one({"_id": level_id})
            
            # Shift all levels after this position up by 1
            self.mongo_db.levels.update_many(
                {"position": {"$gt": position}, "is_legacy": {"$ne": True}},
                {"$inc": {"position": -1}}
            )
            
            # Recalculate all points
            self.recalculate_all_level_points()
            self.recalculate_all_user_points()
            
            print(f"✅ Level removal handled successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error handling level removal: {e}")
            return False
    
    def log_position_change(self, level_id, old_position, new_position, admin_username):
        """Log position changes for audit trail"""
        try:
            change_log = {
                "level_id": level_id,
                "old_position": old_position,
                "new_position": new_position,
                "change_date": datetime.now(timezone.utc),
                "changed_by": admin_username,
                "change_type": "move_up" if new_position < old_position else "move_down"
            }
            
            self.mongo_db.position_changes.insert_one(change_log)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not log position change: {e}")
    
    def get_system_status(self):
        """Get status information about the points system"""
        try:
            total_levels = self.mongo_db.levels.count_documents({})
            total_users = self.mongo_db.users.count_documents({})
            total_records = self.mongo_db.records.count_documents({"status": "approved"})
            
            # Check for inconsistencies
            levels_with_wrong_points = 0
            for level in self.mongo_db.levels.find({}, {"position": 1, "is_legacy": 1, "points": 1}):
                expected_points = self.calculate_level_points(level['position'], level.get('is_legacy', False))
                current_points = level.get('points', 0)
                if abs(float(current_points) - float(expected_points)) > 0.01:
                    levels_with_wrong_points += 1
            
            return {
                "total_levels": total_levels,
                "total_users": total_users,
                "total_approved_records": total_records,
                "levels_with_incorrect_points": levels_with_wrong_points,
                "system_healthy": levels_with_wrong_points == 0
            }
            
        except Exception as e:
            return {"error": str(e)}

# Convenience functions for easy integration
def create_points_manager(mongo_db):
    """Create a new RealTimePointsManager instance"""
    return RealTimePointsManager(mongo_db)

def handle_level_move(mongo_db, level_id, old_position, new_position, admin_username="System"):
    """Convenience function to handle level position changes"""
    manager = RealTimePointsManager(mongo_db)
    return manager.handle_level_position_change(level_id, old_position, new_position, admin_username)

def recalculate_all_points(mongo_db):
    """Convenience function to recalculate all points in the system"""
    manager = RealTimePointsManager(mongo_db)
    levels_updated = manager.recalculate_all_level_points()
    users_updated = manager.recalculate_all_user_points()
    return levels_updated, users_updated

if __name__ == "__main__":
    # Test script
    print("Real-time Points System Test")
    print("This module should be imported and used within the main application")