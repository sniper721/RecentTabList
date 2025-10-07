#!/usr/bin/env python3
"""
Manual Points Recalculation Tool
================================

This script allows you to manually trigger a complete points recalculation
for all levels and users in the system. Use this when:

1. You want to ensure all points are correct after making changes
2. You've added the real-time system and want to fix existing data
3. You suspect there are inconsistencies in the points system

Usage:
    python manual_points_recalculation.py

This script will:
- Recalculate all level points based on current positions
- Recalculate all user points based on their approved records
- Show a detailed report of what was changed
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
        
        print(f"Connecting to database: {mongodb_db}")
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print("✅ Database connection successful")
        
        return db
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def main():
    """Main recalculation process"""
    print("🔄 Manual Points Recalculation Tool")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to database
    db = connect_to_database()
    
    # Import the real-time points system
    try:
        from real_time_points_system import RealTimePointsManager
        print("✅ Real-time points system loaded")
    except ImportError as e:
        print(f"❌ Failed to import real-time points system: {e}")
        print("Make sure real_time_points_system.py is in the same directory")
        sys.exit(1)
    
    # Create manager
    manager = RealTimePointsManager(db)
    
    # Get system status before
    print("\n📊 System Status Before Recalculation:")
    status_before = manager.get_system_status()
    if 'error' not in status_before:
        print(f"  Total levels: {status_before['total_levels']}")
        print(f"  Total users: {status_before['total_users']}")
        print(f"  Total approved records: {status_before['total_approved_records']}")
        print(f"  Levels with incorrect points: {status_before['levels_with_incorrect_points']}")
        print(f"  System healthy: {status_before['system_healthy']}")
    
    # Ask for confirmation
    if status_before.get('levels_with_incorrect_points', 0) == 0:
        print("\n✅ All level points appear to be correct already.")
        response = input("Do you still want to recalculate everything? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Operation cancelled.")
            return
    else:
        print(f"\n⚠️  Found {status_before['levels_with_incorrect_points']} levels with incorrect points.")
        response = input("Proceed with recalculation? (Y/n): ").strip().lower()
        if response in ['n', 'no']:
            print("Operation cancelled.")
            return
    
    print("\n🔄 Starting recalculation process...")
    
    # Step 1: Recalculate level points
    print("\n1️⃣  Recalculating level points...")
    levels_updated = manager.recalculate_all_level_points()
    
    # Step 2: Recalculate user points
    print("\n2️⃣  Recalculating user points...")
    users_updated = manager.recalculate_all_user_points()
    
    # Get system status after
    print("\n📊 System Status After Recalculation:")
    status_after = manager.get_system_status()
    if 'error' not in status_after:
        print(f"  Total levels: {status_after['total_levels']}")
        print(f"  Total users: {status_after['total_users']}")
        print(f"  Total approved records: {status_after['total_approved_records']}")
        print(f"  Levels with incorrect points: {status_after['levels_with_incorrect_points']}")
        print(f"  System healthy: {status_after['system_healthy']}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 RECALCULATION SUMMARY")
    print("=" * 50)
    print(f"✅ Levels updated: {levels_updated}")
    print(f"✅ Users updated: {users_updated}")
    
    if status_after.get('system_healthy', False):
        print("🎉 System is now healthy! All points are correct.")
    else:
        print("⚠️  There may still be some issues. Check the status above.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 The real-time points system will now keep everything in sync automatically!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)