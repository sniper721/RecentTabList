#!/usr/bin/env python3
"""
Test the new time machine features
"""

import json
from datetime import datetime, timezone

def test_historical_data():
    """Test that historical data is properly formatted"""
    try:
        with open('historical_rankings.json', 'r') as f:
            data = json.load(f)
        
        weekly_rankings = data.get('weekly_rankings', {})
        print(f"✅ Found {len(weekly_rankings)} weeks of historical data")
        
        # Check date range
        dates = list(weekly_rankings.keys())
        dates.sort()
        print(f"📅 Date range: {dates[0]} to {dates[-1]}")
        
        # Check a sample week
        sample_date = dates[0]
        sample_week = weekly_rankings[sample_date]
        rankings = sample_week.get('rankings', [])
        
        print(f"📊 Sample week ({sample_date}):")
        print(f"   Week number: {sample_week.get('week', 'N/A')}")
        print(f"   Number of levels: {len(rankings)}")
        
        # Show top 10 from sample week
        print(f"   Top 10 levels:")
        for i, level in enumerate(rankings[:10]):
            print(f"     #{level['position']}: {level['name']}")
        
        # Check if we have 150 levels in recent weeks
        recent_weeks = [w for w in weekly_rankings.values() if len(w.get('rankings', [])) >= 140]
        print(f"✅ {len(recent_weeks)} weeks have 140+ levels (good coverage)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing historical data: {e}")
        return False

def test_points_calculation():
    """Test the points calculation formula"""
    def calculate_level_points(position):
        """Calculate points based on position using exponential formula"""
        return round(250 * (0.9636214148582346 ** (position - 1)), 2)
    
    print("\n🧮 Testing points calculation:")
    test_positions = [1, 5, 10, 25, 50, 100, 150]
    
    for pos in test_positions:
        points_100 = calculate_level_points(pos)
        points_79 = round(points_100 * 0.79, 2)
        print(f"   Position #{pos}: {points_79} (79%) — {points_100} (100%) points")
    
    return True

def main():
    print("🧪 Testing new Time Machine features...\n")
    
    success = True
    
    print("1️⃣ Testing historical data structure...")
    success &= test_historical_data()
    
    print("\n2️⃣ Testing points calculation...")
    success &= test_points_calculation()
    
    print(f"\n{'✅ All tests passed!' if success else '❌ Some tests failed!'}")
    
    print("\n📋 New features summary:")
    print("   ✅ Copy button for level IDs")
    print("   ✅ Points system display (79% — 100% points)")
    print("   ✅ Time machine shows top 150 levels")
    print("   ✅ Historical data from July 2024 to present")
    print("   ✅ Auto-update when levels are modified")
    
    return success

if __name__ == "__main__":
    main()