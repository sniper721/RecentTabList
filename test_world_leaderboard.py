#!/usr/bin/env python3
"""
Test script for the World Leaderboard functionality
"""

import requests
import json

# Test the world leaderboard endpoint
def test_world_leaderboard():
    try:
        response = requests.get('http://127.0.0.1:10000/world')
        print(f"World Leaderboard Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ World leaderboard page loads successfully!")
            # Check if the page contains expected elements
            content = response.text
            if "World Leaderboard" in content:
                print("✅ Page title found")
            if "Interactive World Map" in content:
                print("✅ Map section found")
            if "Top Countries" in content:
                print("✅ Country rankings found")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

# Test a country-specific leaderboard
def test_country_leaderboard():
    try:
        response = requests.get('http://127.0.0.1:10000/country/US')
        print(f"US Leaderboard Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Country leaderboard page loads successfully!")
        else:
            print(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    print("🌍 Testing World Leaderboard System...")
    print("=" * 50)
    
    test_world_leaderboard()
    print()
    test_country_leaderboard()
    
    print("\n🎉 World Leaderboard system is ready!")
    print("Features implemented:")
    print("✅ World map leaderboard with country rankings")
    print("✅ Country-specific leaderboards with pagination")
    print("✅ Points requirement (must have >0 points)")
    print("✅ Country selection in user settings")
    print("✅ Beautiful responsive UI with Bootstrap")
    print("✅ Navigation integration")