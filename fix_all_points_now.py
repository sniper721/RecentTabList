#!/usr/bin/env python3
"""
Fix All Points Now - Automated
==============================

This script automatically fixes all user points without requiring confirmation.
It will recalculate all level points and all user points to their correct values.
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

def main():
    """Main recalculation process"""
    print("🔄 AUTOMATED POINTS RECALCULATION")
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
        sys.exit(1)
    
    # Create manager
    manager = RealTimePointsManager(db)
    
    print("\n🔄 Starting automatic recalculation process...")
    
    # Step 1: Recalculate level points
    print("\n1️⃣  Recalculating ALL level points...")
    levels_updated = manager.recalculate_all_level_points()
    
    # Step 2: Recalculate user points
    print("\n2️⃣  Recalculating ALL user points...")
    users_updated = manager.recalculate_all_user_points()
    
    # Get system status after
    print("\n📊 Verifying system health...")
    status_after = manager.get_system_status()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 RECALCULATION COMPLETE")
    print("=" * 50)
    print(f"✅ Levels updated: {levels_updated}")
    print(f"✅ Users updated: {users_updated}")
    
    if 'error' not in status_after:
        print(f"📊 System Status:")
        print(f"  • Total levels: {status_after['total_levels']}")
        print(f"  • Total users: {status_after['total_users']}")
        print(f"  • Total approved records: {status_after['total_approved_records']}")
        print(f"  • Levels with incorrect points: {status_after['levels_with_incorrect_points']}")
        print(f"  • System healthy: {status_after['system_healthy']}")
        
        if status_after.get('system_healthy', False):
            print("\n🎉 SUCCESS: All points are now correct!")
        else:
            print(f"\n⚠️  WARNING: {status_after['levels_with_incorrect_points']} levels still have incorrect points")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return status_after.get('system_healthy', False)

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎯 ALL POINTS HAVE BEEN FIXED!")
            print("Everyone now has the correct points based on their records and current level positions.")
        else:
            print("\n⚠️  Some issues may remain. Check the output above.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)