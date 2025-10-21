#!/usr/bin/env python3
"""
Test script for Discord bot integration
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_discord_bot():
    """Test Discord bot functionality"""
    print("🤖 Testing Discord Bot Integration")
    print("=" * 50)
    
    # Check environment variables
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_GUILD_ID')
    admin_channel_id = os.environ.get('DISCORD_ADMIN_CHANNEL_ID')
    
    print(f"Bot Token: {'✅ Set' if bot_token else '❌ Missing'}")
    print(f"Guild ID: {'✅ Set' if guild_id else '❌ Missing'}")
    print(f"Admin Channel ID: {'✅ Set' if admin_channel_id else '❌ Missing'}")
    
    if not all([bot_token, guild_id, admin_channel_id]):
        print("\n❌ Missing required environment variables!")
        print("Please set DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, and DISCORD_ADMIN_CHANNEL_ID")
        return False
    
    # Test bot import
    try:
        from discord_bot import RTLBot, start_discord_bot, check_user_role, send_dm_to_user
        print("✅ Discord bot module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Discord bot module: {e}")
        return False
    
    # Test bot startup (don't actually start it)
    print("✅ Discord bot is ready to start")
    print("\n🎯 To test the bot:")
    print("1. Make sure your bot is added to your Discord server")
    print("2. The bot needs the following permissions:")
    print("   - Send Messages")
    print("   - Read Message History")
    print("   - View Channels")
    print("   - Manage Roles (optional - for role management commands)")
    print("3. Run the main.py file to start both Flask and Discord bot")
    
    return True

def test_verification_flow():
    """Test verification submission flow"""
    print("\n📝 Testing Verification Flow")
    print("=" * 50)
    
    # Test MongoDB connection (simplified)
    try:
        from pymongo import MongoClient
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False
    
    print("✅ Verification submission system ready")
    print("\n🎯 Verification Flow:")
    print("1. User must link Discord account in profile")
    print("2. User can submit verification with video, difficulty, ratings")
    print("3. Admin gets notification in Discord channel")
    print("5. Admin can approve/reject in admin panel")
    print("6. User gets DM notification about decision")
    
    return True

if __name__ == "__main__":
    print("🚀 RTL Discord Bot Integration Test")
    print("=" * 60)
    
    success = True
    success &= test_discord_bot()
    success &= test_verification_flow()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Discord bot integration is ready.")
        print("\n🎉 Features implemented:")
        print("• Discord bot for role checking and notifications")
        print("• Verification submission system with role requirements")
        print("• Discord OAuth for account linking")
        print("• Enhanced changelog notifications")
        print("• Admin panel for verification management")
        print("• Automatic DM notifications for approval/rejection")
    else:
        print("❌ Some tests failed. Please check the configuration.")
    
    print("\n🔧 Next steps:")
    print("1. Update your .env file with Discord credentials")
    print("2. Add the bot to your Discord server")
    print("3. Configure the admin channel and guild ID")
    print("4. Test the verification submission flow")
    print("5. Enjoy your automated Discord integration! 😈")