#!/usr/bin/env python3
"""
Monitor Live Points System
=========================

This script monitors the points system and shows real-time status.
Run this to verify that points are updating correctly after admin actions.
"""

import os
import sys
import time
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
        return db
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def get_top_users(db, limit=5):
    """Get top users by points"""
    return list(db.users.find(
        {"points": {"$gt": 0}}, 
        {"username": 1, "points": 1}
    ).sort("points", -1).limit(limit))

def get_top_levels(db, limit=5):
    """Get top levels by position"""
    return list(db.levels.find(
        {"is_legacy": {"$ne": True}}, 
        {"name": 1, "position": 1, "points": 1}
    ).sort("position", 1).limit(limit))

def monitor_system():
    """Monitor the points system"""
    print("🔍 LIVE POINTS SYSTEM MONITOR")
    print("=" * 50)
    print("This will show you the current state of the points system.")
    print("Add/move levels in the admin panel and watch the changes!")
    print("Press Ctrl+C to stop monitoring.\n")
    
    db = connect_to_database()
    
    # Import the real-time points system
    try:
        from real_time_points_system import RealTimePointsManager
        manager = RealTimePointsManager(db)
    except ImportError as e:
        print(f"❌ Failed to import real-time points system: {e}")
        sys.exit(1)
    
    last_status = None
    last_top_users = None
    last_top_levels = None
    
    try:
        while True:
            # Clear screen (works on most terminals)
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("🔍 LIVE POINTS SYSTEM MONITOR")
            print("=" * 50)
            print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("Press Ctrl+C to stop monitoring.\n")
            
            # Get current status
            status = manager.get_system_status()
            
            # Check if status changed
            if status != last_status:
                if last_status is not None:
                    print("🔄 SYSTEM STATUS CHANGED!")
                last_status = status
            
            # Display system status
            print("📊 System Status:")
            if 'error' not in status:
                print(f"  • Total levels: {status['total_levels']}")
                print(f"  • Total users: {status['total_users']}")
                print(f"  • Total approved records: {status['total_approved_records']}")
                print(f"  • Levels with incorrect points: {status['levels_with_incorrect_points']}")
                
                if status['system_healthy']:
                    print("  • Status: ✅ HEALTHY")
                else:
                    print(f"  • Status: ⚠️ NEEDS ATTENTION ({status['levels_with_incorrect_points']} issues)")
            else:
                print(f"  • Error: {status['error']}")
            
            # Get top users
            top_users = get_top_users(db)
            
            # Check if top users changed
            if top_users != last_top_users:
                if last_top_users is not None:
                    print("\n🏆 TOP USERS CHANGED!")
                last_top_users = top_users
            
            print(f"\n🏆 Top {len(top_users)} Users by Points:")
            for i, user in enumerate(top_users, 1):
                print(f"  {i}. {user['username']}: {user['points']} points")
            
            # Get top levels
            top_levels = get_top_levels(db)
            
            # Check if top levels changed
            if top_levels != last_top_levels:
                if last_top_levels is not None:
                    print("\n📋 TOP LEVELS CHANGED!")
                last_top_levels = top_levels
            
            print(f"\n📋 Top {len(top_levels)} Levels:")
            for level in top_levels:
                print(f"  #{level['position']}. {level['name']}: {level['points']} points")
            
            print(f"\n💡 Monitoring... (refreshing every 3 seconds)")
            print("   Add/move levels in admin panel to see live updates!")
            
            # Wait before next update
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped. System is ready for live updates!")

if __name__ == "__main__":
    monitor_system()