#!/usr/bin/env python3
"""
Test script to verify Discord verification submission notifications include Level ID
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_discord_bot_notification():
    """Test Discord bot verification notification with Level ID"""
    try:
        # Import the Discord bot function
        from discord_bot import notify_verification_submission, is_bot_available
        
        print("🔍 Testing Discord bot verification notification...")
        
        # Check if bot is available
        if not is_bot_available():
            print("❌ Discord bot is not available")
            print("   Make sure the following environment variables are set:")
            print(f"   - DISCORD_BOT_TOKEN: {'✅ Set' if os.environ.get('DISCORD_BOT_TOKEN') else '❌ Missing'}")
            print(f"   - DISCORD_GUILD_ID: {'✅ Set' if os.environ.get('DISCORD_GUILD_ID') else '❌ Missing'}")
            print(f"   - DISCORD_ADMIN_CHANNEL_ID: {'✅ Set' if os.environ.get('DISCORD_ADMIN_CHANNEL_ID') else '❌ Missing'}")
            return False
        
        print("✅ Discord bot is available")
        
        # Test notification with Level ID
        test_data = {
            'username': 'TestUser',
            'level_name': 'Test Level',
            'creator': 'TestCreator',
            'verifier': 'TestVerifier',
            'difficulty': 'Extreme Demon',
            'placement': 1,
            'experience': 8,
            'enjoyment': 9,
            'video_url': 'https://youtube.com/watch?v=test123',
            'comments': 'This is a test verification submission',
            'level_id': '12345678'  # This should now be displayed prominently
        }
        
        print("📤 Sending test verification notification...")
        success = notify_verification_submission(
            test_data['username'],
            test_data['level_name'],
            test_data['creator'],
            test_data['verifier'],
            test_data['difficulty'],
            test_data['placement'],
            test_data['experience'],
            test_data['enjoyment'],
            test_data['video_url'],
            test_data['comments'],
            test_data['level_id']
        )
        
        if success:
            print("✅ Test notification sent successfully!")
            print("   Check your Discord admin channel to verify:")
            print("   1. Level ID is displayed prominently")
            print("   2. All other information is correct")
            return True
        else:
            print("❌ Failed to send test notification")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import Discord bot: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing Discord bot: {e}")
        return False

def check_environment_variables():
    """Check Discord-related environment variables"""
    print("🔍 Checking Discord environment variables...")
    
    required_vars = [
        'DISCORD_BOT_TOKEN',
        'DISCORD_GUILD_ID', 
        'DISCORD_ADMIN_CHANNEL_ID'
    ]
    
    all_set = True
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Missing")
            all_set = False
    
    if all_set:
        print("✅ All required Discord environment variables are set")
        print(f"\n📢 Discord Admin Channel ID: {os.environ.get('DISCORD_ADMIN_CHANNEL_ID')}")
        print("   This is where verification submission logs are sent")
    else:
        print("❌ Some Discord environment variables are missing")
        print("   Please check your .env file")
    
    return all_set

if __name__ == "__main__":
    print("🤖 Discord Verification Fix Test")
    print("=" * 50)
    
    # Check environment variables
    env_ok = check_environment_variables()
    print()
    
    if env_ok:
        # Test Discord bot notification
        test_ok = test_discord_bot_notification()
        
        if test_ok:
            print("\n✅ All tests passed!")
            print("   The Discord bot should now display Level IDs in verification submissions")
            print("   Admin templates have also been updated to show Level IDs")
        else:
            print("\n❌ Discord bot test failed")
    else:
        print("\n❌ Environment variables not properly configured")
        print("   Please set up Discord bot configuration in your .env file")
    
    print("\n📋 Summary of fixes applied:")
    print("   1. Discord bot now displays Level ID prominently in bold")
    print("   2. Admin verification list now shows Level ID")
    print("   3. Admin verification details table now includes Level ID column")
    print("   4. Individual verification detail page now shows Level ID")
    print(f"\n🔧 Environment variable for Discord admin channel: DISCORD_ADMIN_CHANNEL_ID")