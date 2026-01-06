#!/usr/bin/env python3
"""
Add current top 150 data to time machine for today's date (January 5, 2026)
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timezone

load_dotenv()

def add_current_top150_to_historical_data():
    """Add current top 150 data to historical rankings for today's date"""
    try:
        # Connect to MongoDB
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Get current top 150 levels
        print("📊 Getting current top 150 levels from database...")
        current_levels = list(db.levels.find(
            {'is_legacy': False}, 
            {'name': 1, 'position': 1}
        ).sort('position', 1).limit(150))
        
        print(f"✅ Found {len(current_levels)} current levels")
        
        # Create rankings data for today (January 5, 2026)
        today_date = "2026-01-05"
        rankings = []
        
        for level in current_levels:
            rankings.append({
                "position": level.get('position', 0),
                "name": level.get('name', 'Unknown')
            })
        
        # Load existing historical data
        print("📖 Loading existing historical rankings...")
        try:
            with open('historical_rankings.json', 'r') as f:
                historical_data = json.load(f)
        except FileNotFoundError:
            historical_data = {"weekly_rankings": {}}
        
        # Add today's data
        print(f"📅 Adding top {len(rankings)} levels for {today_date}...")
        historical_data["weekly_rankings"][today_date] = {
            "week": "current",
            "rankings": rankings
        }
        
        # Save updated historical data
        with open('historical_rankings.json', 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        print(f"✅ Successfully added {len(rankings)} levels for {today_date}")
        print(f"📋 Top 10 levels added:")
        for i, ranking in enumerate(rankings[:10]):
            print(f"   {ranking['position']}: {ranking['name']}")
        
        if len(rankings) > 10:
            print(f"   ... and {len(rankings) - 10} more levels")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding current top 150 data: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Adding current top 150 data to time machine...")
    success = add_current_top150_to_historical_data()
    
    if success:
        print("\n🎉 Successfully updated time machine with current top 150 data!")
        print("📅 January 5, 2026 now shows the full top 150 levels")
        print("📊 Historical dates still show top 10 as before")
    else:
        print("\n❌ Failed to update time machine data")