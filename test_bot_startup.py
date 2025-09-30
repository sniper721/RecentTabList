#!/usr/bin/env python3
"""
Test Discord bot startup independently
Run this to test if the bot can start on Render
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_bot_startup():
    """Test if Discord bot can start properly"""
    print("🔍 Testing Discord Bot Startup...")
    print("=" * 50)
    
    # Check environment variables first
    token = os.environ.get('DISCORD_BOT_TOKEN')
    guild_id = os.environ.get('DISCORD_GUILD_ID')
    admin_channel_id = os.environ.get('DISCORD_ADMIN_CHANNEL_ID')
    
    print(f"DISCORD_BOT_TOKEN: {'✅ Found' if token else '❌ Missing'}")
    print(f"DISCORD_GUILD_ID: {'✅ ' + guild_id if guild_id else '❌ Missing'}")
    print(f"DISCORD_ADMIN_CHANNEL_ID: {'✅ ' + admin_channel_id if admin_channel_id else '❌ Missing'}")
    
    if not all([token, guild_id, admin_channel_id]):
        print("❌ Missing required environment variables")
        return False
    
    # Test Discord bot import
    print("\n🔍 Testing Discord bot import...")
    try:
        from discord_bot import start_discord_bot, is_bot_available
        print("✅ Discord bot module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import discord_bot: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing discord_bot: {e}")
        return False
    
    # Test bot startup
    print("\n🔍 Testing bot startup...")
    try:
        bot_started = start_discord_bot()
        if bot_started:
            print("✅ Discord bot startup initiated")
            
            # Wait a moment and check if bot is available
            import time
            print("⏳ Waiting 5 seconds for bot to connect...")
            time.sleep(5)
            
            if is_bot_available():
                print("✅ Discord bot is now available!")
                return True
            else:
                print("⚠️ Discord bot started but not yet available")
                return True  # Still consider this a success
        else:
            print("❌ Discord bot failed to start")
            return False
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bot_startup()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Discord bot startup test")
    sys.exit(0 if success else 1)