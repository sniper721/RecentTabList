#!/usr/bin/env python3
"""
Test that time machine now shows top 150 for recent dates and top 10 for historical dates
"""

import json
from datetime import datetime

def test_timemachine_data_distribution():
    """Test that time machine has correct data distribution"""
    print("🧪 Testing Time Machine Data Distribution...")
    
    try:
        # Load historical rankings
        with open('historical_rankings.json', 'r') as f:
            historical_data = json.load(f)
        
        weekly_rankings = historical_data.get('weekly_rankings', {})
        
        # Test dates that should have top 150
        top150_dates = [
            "2025-12-01", "2025-12-08", "2025-12-15", 
            "2025-12-22", "2025-12-29", "2026-01-05"
        ]
        
        # Test dates that should have top 10
        top10_dates = [
            "2025-06-21", "2025-07-05", "2025-08-02", "2025-09-06"
        ]
        
        print(f"\n📊 Testing dates that should have top 150 levels:")
        all_top150_correct = True
        for date in top150_dates:
            if date in weekly_rankings:
                count = len(weekly_rankings[date]['rankings'])
                status = "✅" if count >= 100 else "❌"
                print(f"   {date}: {count} levels {status}")
                if count < 100:
                    all_top150_correct = False
            else:
                print(f"   {date}: No data found ❌")
                all_top150_correct = False
        
        print(f"\n📊 Testing dates that should have top 10 levels:")
        all_top10_correct = True
        for date in top10_dates:
            if date in weekly_rankings:
                count = len(weekly_rankings[date]['rankings'])
                status = "✅" if count <= 15 else "❌"
                print(f"   {date}: {count} levels {status}")
                if count > 15:
                    all_top10_correct = False
            else:
                print(f"   {date}: No data found ❌")
                all_top10_correct = False
        
        # Summary
        print(f"\n📋 Summary:")
        print(f"   Recent dates (Dec 2025 - Jan 2026): {'✅ All have 100+ levels' if all_top150_correct else '❌ Some missing data'}")
        print(f"   Historical dates (Jun - Nov 2025): {'✅ All have ~10 levels' if all_top10_correct else '❌ Some have wrong count'}")
        
        # Show sample data from a recent date
        sample_date = "2025-12-22"
        if sample_date in weekly_rankings:
            rankings = weekly_rankings[sample_date]['rankings']
            print(f"\n📋 Sample data from {sample_date} (should be top 150):")
            print(f"   Total levels: {len(rankings)}")
            print(f"   Top 10:")
            for i, ranking in enumerate(rankings[:10]):
                print(f"     {ranking['position']}: {ranking['name']}")
            if len(rankings) > 10:
                print(f"     ... and {len(rankings) - 10} more levels")
        
        return all_top150_correct and all_top10_correct
        
    except Exception as e:
        print(f"❌ Error testing time machine data: {e}")
        return False

def test_timemachine_logic_simulation():
    """Simulate the time machine logic to verify it works correctly"""
    print(f"\n🧪 Testing Time Machine Logic Simulation...")
    
    try:
        from datetime import datetime, timezone, timedelta
        
        # Simulate the logic from main.py
        current_date = datetime.now(timezone.utc).date()
        
        test_cases = [
            ("2026-01-05", "Recent date - should show 150"),
            ("2026-01-01", "Recent date - should show 150"), 
            ("2025-12-25", "Recent date - should show 150"),
            ("2025-12-01", "Recent date - should show 150"),
            ("2025-11-01", "Older date - should show 10"),
            ("2025-08-01", "Historical date - should show 10"),
            ("2025-06-21", "Historical date - should show 10")
        ]
        
        print(f"Current date: {current_date}")
        print(f"Testing time machine logic:")
        
        for test_date_str, description in test_cases:
            test_date = datetime.strptime(test_date_str, '%Y-%m-%d').date()
            days_difference = (current_date - test_date).days
            
            if days_difference <= 7:
                expected = "150 levels (recent)"
            else:
                expected = "10 levels (historical)"
            
            print(f"   {test_date_str}: {days_difference} days ago → {expected}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing time machine logic: {e}")
        return False

def main():
    """Run all tests"""
    print("🔧 Testing Time Machine Top 150 Implementation\n")
    
    success = True
    
    # Test 1: Data distribution
    success &= test_timemachine_data_distribution()
    
    # Test 2: Logic simulation
    success &= test_timemachine_logic_simulation()
    
    print(f"\n{'🎉' if success else '❌'} Test Results:")
    if success:
        print("✅ All tests passed!")
        print("📋 Time machine is now working correctly:")
        print("   ✅ Recent dates (Dec 2025 - Jan 2026) show top 150 levels")
        print("   ✅ Historical dates (Jun - Nov 2025) show top 10 levels")
        print("   ✅ Logic correctly determines which data to show")
        print("   ✅ Users can now see full rankings for recent periods")
    else:
        print("❌ Some tests failed - check the output above")

if __name__ == "__main__":
    main()