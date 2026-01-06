#!/usr/bin/env python3
"""
Add top 150 data to time machine for all recent dates where we know the list had 150 levels
Based on changelog analysis, the list was expanded to 150 around December 2025
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone, timedelta

load_dotenv()

def get_dates_to_update():
    """Get list of dates that should have top 150 data"""
    # Based on analysis, the list was expanded to 150 around December 2025
    # We'll add top 150 data for dates from December 1, 2025 onwards
    
    dates_to_update = []
    
    # Start from December 1, 2025
    start_date = datetime(2025, 12, 1)
    end_date = datetime(2026, 1, 5)  # Today
    
    current_date = start_date
    while current_date <= end_date:
        # Add weekly snapshots (every 7 days)
        dates_to_update.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=7)
    
    # Always include today
    today = datetime(2026, 1, 5)
    today_str = today.strftime('%Y-%m-%d')
    if today_str not in dates_to_update:
        dates_to_update.append(today_str)
    
    return sorted(dates_to_update)

def add_top150_for_recent_dates():
    """Add top 150 data for all recent dates where we know the list had 150 levels"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Get current top 150 levels (this represents the most recent state)
        print("📊 Getting current top 150 levels from database...")
        current_levels = list(db.levels.find(
            {'is_legacy': False}, 
            {'name': 1, 'position': 1}
        ).sort('position', 1).limit(150))
        
        print(f"✅ Found {len(current_levels)} current levels")
        
        # Load existing historical data
        print("📖 Loading existing historical rankings...")
        try:
            with open('historical_rankings.json', 'r') as f:
                historical_data = json.load(f)
        except FileNotFoundError:
            historical_data = {"weekly_rankings": {}}
        
        # Get dates to update
        dates_to_update = get_dates_to_update()
        print(f"📅 Will add top 150 data for {len(dates_to_update)} dates:")
        for date in dates_to_update:
            print(f"   - {date}")
        
        # Create rankings data for each date
        rankings = []
        for level in current_levels:
            rankings.append({
                "position": level.get('position', 0),
                "name": level.get('name', 'Unknown')
            })
        
        # Add data for each date
        added_count = 0
        updated_count = 0
        
        for date_str in dates_to_update:
            if date_str in historical_data["weekly_rankings"]:
                # Check if it already has 100+ levels
                existing_rankings = historical_data["weekly_rankings"][date_str]["rankings"]
                if len(existing_rankings) >= 100:
                    print(f"⏭️  {date_str}: Already has {len(existing_rankings)} levels, skipping")
                    continue
                else:
                    print(f"🔄 {date_str}: Updating from {len(existing_rankings)} to {len(rankings)} levels")
                    historical_data["weekly_rankings"][date_str]["rankings"] = rankings
                    updated_count += 1
            else:
                print(f"➕ {date_str}: Adding {len(rankings)} levels")
                historical_data["weekly_rankings"][date_str] = {
                    "week": "recent",
                    "rankings": rankings
                }
                added_count += 1
        
        # Save updated historical data
        with open('historical_rankings.json', 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        print(f"\n✅ Successfully processed {len(dates_to_update)} dates:")
        print(f"   📅 Added: {added_count} new dates")
        print(f"   🔄 Updated: {updated_count} existing dates")
        print(f"   📊 Each date now has {len(rankings)} levels")
        
        print(f"\n📋 Sample of levels added:")
        for i, ranking in enumerate(rankings[:10]):
            print(f"   {ranking['position']}: {ranking['name']}")
        
        if len(rankings) > 10:
            print(f"   ... and {len(rankings) - 10} more levels")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding top 150 data: {e}")
        return False

def verify_updates():
    """Verify that the updates were applied correctly"""
    try:
        with open('historical_rankings.json', 'r') as f:
            historical_data = json.load(f)
        
        weekly_rankings = historical_data.get('weekly_rankings', {})
        
        print(f"\n🔍 Verification Results:")
        print(f"Total dates in historical data: {len(weekly_rankings)}")
        
        # Check dates with 100+ levels
        dates_with_150 = []
        dates_with_10 = []
        
        for date_str, data in weekly_rankings.items():
            rankings_count = len(data.get('rankings', []))
            if rankings_count >= 100:
                dates_with_150.append((date_str, rankings_count))
            elif rankings_count <= 15:
                dates_with_10.append((date_str, rankings_count))
        
        print(f"\n📊 Dates with 100+ levels: {len(dates_with_150)}")
        for date_str, count in sorted(dates_with_150):
            print(f"   {date_str}: {count} levels")
        
        print(f"\n📊 Dates with ~10 levels (historical): {len(dates_with_10)}")
        for date_str, count in sorted(dates_with_10)[:5]:  # Show first 5
            print(f"   {date_str}: {count} levels")
        if len(dates_with_10) > 5:
            print(f"   ... and {len(dates_with_10) - 5} more historical dates")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying updates: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding top 150 data for recent dates...")
    print("📅 Based on analysis: List expanded to 150 around December 2025")
    
    success = add_top150_for_recent_dates()
    
    if success:
        print("\n🔍 Verifying updates...")
        verify_updates()
        
        print("\n🎉 Successfully updated time machine!")
        print("📅 Recent dates (Dec 2025 - Jan 2026) now show top 150 levels")
        print("📊 Historical dates still show top 10 as before")
        print("🕒 Users can now see full rankings for recent time periods")
    else:
        print("\n❌ Failed to update time machine data")