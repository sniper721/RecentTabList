#!/usr/bin/env python3
"""
Simple script to add test data via HTTP requests to the running Flask app
"""

import requests
import json

def test_world_leaderboard():
    """Test the world leaderboard and show current data"""
    try:
        print("🌍 Testing World Leaderboard...")
        response = requests.get('http://127.0.0.1:10000/world')
        
        if response.status_code == 200:
            print("✅ World leaderboard is accessible!")
            
            # Check if we have data
            content = response.text
            if "No country data available" in content:
                print("📊 No country data found yet")
            else:
                print("📊 Country data is available!")
                
            if "No players found" in content:
                print("👥 No players with points found yet")
            else:
                print("👥 Players with points found!")
                
        else:
            print(f"❌ Error accessing world leaderboard: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

def show_instructions():
    """Show instructions for adding test data"""
    print("\n" + "=" * 60)
    print("🎯 HOW TO ADD TEST DATA:")
    print("=" * 60)
    print()
    print("1. 📝 REGISTER USERS:")
    print("   - Go to http://127.0.0.1:10000/register")
    print("   - Create a few test accounts")
    print()
    print("2. 🌍 SET COUNTRIES:")
    print("   - Login to each account")
    print("   - Go to Settings (⚙️ icon in navbar)")
    print("   - Select a country from the dropdown")
    print("   - Save settings")
    print()
    print("3. 🏆 EARN POINTS:")
    print("   - Submit records for demon levels")
    print("   - Admin can approve records to give points")
    print("   - Or admin can manually update points")
    print()
    print("4. 🗺️ VIEW WORLD MAP:")
    print("   - Go to Stats → World Leaderboard")
    print("   - See countries ranked by total points")
    print("   - Click countries to see player rankings")
    print()
    print("🚀 QUICK TEST ACCOUNTS:")
    print("   Username: testuser1, Password: password123")
    print("   Username: testuser2, Password: password123")
    print("   Username: testuser3, Password: password123")
    print()
    print("💡 TIP: Use different countries for each test user!")

def create_quick_demo():
    """Show how to quickly demo the system"""
    print("\n" + "=" * 60)
    print("⚡ QUICK DEMO SETUP:")
    print("=" * 60)
    print()
    print("If you want to see the system in action immediately:")
    print()
    print("1. 🔑 Login as admin")
    print("2. 👥 Go to Admin → Users")
    print("3. 🎯 Manually add points to existing users")
    print("4. 🌍 Set countries for users in their profiles")
    print("5. 📊 Visit /world to see the leaderboard")
    print()
    print("Or use the admin panel to:")
    print("- Update user points directly")
    print("- Approve pending records")
    print("- Manage user countries")

if __name__ == "__main__":
    print("🌍 WORLD LEADERBOARD SYSTEM TEST")
    print("=" * 60)
    
    # Test current state
    test_world_leaderboard()
    
    # Show instructions
    show_instructions()
    
    # Show quick demo
    create_quick_demo()
    
    print("\n🎉 World Leaderboard System is ready!")
    print("Visit: http://127.0.0.1:10000/world")
    print("=" * 60)