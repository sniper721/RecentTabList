#!/usr/bin/env python3
"""
Discord Bot Debug Script
Run this to diagnose Discord bot connection issues
"""

import os
import asyncio
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment_variables():
    """Check if all required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = {
        'DISCORD_BOT_TOKEN': os.environ.get('DISCORD_BOT_TOKEN'),
        'DISCORD_GUILD_ID': os.environ.get('DISCORD_GUILD_ID'),
        'DISCORD_ADMIN_CHANNEL_ID': os.environ.get('DISCORD_ADMIN_CHANNEL_ID')
    }
    
    all_good = True
    for var_name, var_value in required_vars.items():
        if var_value:
            if var_name == 'DISCORD_BOT_TOKEN':
                # Show only first and last few characters of token
                masked_token = f"{var_value[:10]}...{var_value[-10:]}" if len(var_value) > 20 else "***"
                print(f"✅ {var_name}: {masked_token}")
            else:
                print(f"✅ {var_name}: {var_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_good = False
    
    return all_good, required_vars

async def test_bot_connection(token, guild_id, admin_channel_id):
    """Test bot connection and permissions"""
    print("\n🤖 Testing Bot Connection...")
    
    # Create bot with minimal intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    
    class TestBot(discord.Client):
        def __init__(self):
            super().__init__(intents=intents)
            self.connection_successful = False
            self.guild_found = False
            self.channel_found = False
            self.permissions_ok = False
        
        async def on_ready(self):
            print(f"✅ Bot connected as: {self.user}")
            print(f"✅ Bot ID: {self.user.id}")
            self.connection_successful = True
            
            # Check guild
            if guild_id:
                guild = self.get_guild(int(guild_id))
                if guild:
                    print(f"✅ Found guild: {guild.name} (ID: {guild.id})")
                    print(f"✅ Bot is member of guild: {guild.me is not None}")
                    self.guild_found = True
                    
                    # Check admin channel
                    if admin_channel_id:
                        channel = guild.get_channel(int(admin_channel_id))
                        if channel:
                            print(f"✅ Found admin channel: {channel.name} (ID: {channel.id})")
                            self.channel_found = True
                            
                            # Check permissions
                            permissions = channel.permissions_for(guild.me)
                            print(f"✅ Bot permissions in #{channel.name}:")
                            print(f"   - Send Messages: {permissions.send_messages}")
                            print(f"   - Embed Links: {permissions.embed_links}")
                            print(f"   - Read Message History: {permissions.read_message_history}")
                            print(f"   - View Channel: {permissions.view_channel}")
                            
                            if permissions.send_messages and permissions.embed_links:
                                self.permissions_ok = True
                                print("✅ Bot has required permissions!")
                            else:
                                print("❌ Bot missing required permissions!")
                        else:
                            print(f"❌ Admin channel not found with ID: {admin_channel_id}")
                    else:
                        print("⚠️ No admin channel ID provided")
                else:
                    print(f"❌ Guild not found with ID: {guild_id}")
                    print("❌ Make sure the bot is invited to your server!")
            else:
                print("⚠️ No guild ID provided")
            
            # Close after checking
            await self.close()
    
    try:
        bot = TestBot()
        await bot.start(token)
        return bot.connection_successful, bot.guild_found, bot.channel_found, bot.permissions_ok
    except discord.LoginFailure:
        print("❌ Invalid bot token!")
        return False, False, False, False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False, False, False, False

def generate_invite_link(client_id):
    """Generate bot invite link"""
    if not client_id:
        return None
    
    # Required permissions for the bot
    permissions = (
        discord.Permissions.send_messages |
        discord.Permissions.embed_links |
        discord.Permissions.read_message_history |
        discord.Permissions.view_channel |
        discord.Permissions.manage_roles  # For role checking
    )
    
    invite_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={permissions.value}&scope=bot"
    return invite_url

async def main():
    """Main diagnostic function"""
    print("🔧 Discord Bot Diagnostic Tool")
    print("=" * 50)
    
    # Check environment variables
    env_ok, env_vars = check_environment_variables()
    
    if not env_ok:
        print("\n❌ Missing required environment variables!")
        print("Make sure you have set these in Render:")
        print("- DISCORD_BOT_TOKEN")
        print("- DISCORD_GUILD_ID") 
        print("- DISCORD_ADMIN_CHANNEL_ID")
        return
    
    # Test bot connection
    token = env_vars['DISCORD_BOT_TOKEN']
    guild_id = env_vars['DISCORD_GUILD_ID']
    admin_channel_id = env_vars['DISCORD_ADMIN_CHANNEL_ID']
    
    connected, guild_found, channel_found, permissions_ok = await test_bot_connection(
        token, guild_id, admin_channel_id
    )
    
    print("\n📊 Diagnostic Summary:")
    print("=" * 30)
    print(f"Bot Connection: {'✅' if connected else '❌'}")
    print(f"Guild Found: {'✅' if guild_found else '❌'}")
    print(f"Channel Found: {'✅' if channel_found else '❌'}")
    print(f"Permissions OK: {'✅' if permissions_ok else '❌'}")
    
    if not connected:
        print("\n🔧 Troubleshooting Steps:")
        print("1. Check if your DISCORD_BOT_TOKEN is correct")
        print("2. Make sure the bot is created in Discord Developer Portal")
        
    elif not guild_found:
        print("\n🔧 Troubleshooting Steps:")
        print("1. Check if DISCORD_GUILD_ID is correct")
        print("2. Make sure the bot is invited to your server")
        
        # Generate invite link
        client_id = os.environ.get('DISCORD_CLIENT_ID')
        if client_id:
            invite_link = generate_invite_link(client_id)
            print(f"3. Use this invite link: {invite_link}")
        
    elif not channel_found:
        print("\n🔧 Troubleshooting Steps:")
        print("1. Check if DISCORD_ADMIN_CHANNEL_ID is correct")
        print("2. Make sure the channel exists in your server")
        
    elif not permissions_ok:
        print("\n🔧 Troubleshooting Steps:")
        print("1. Give the bot 'Send Messages' permission in the admin channel")
        print("2. Give the bot 'Embed Links' permission")
        print("3. Make sure the bot role is above other roles it needs to manage")
    
    else:
        print("\n🎉 Everything looks good! The bot should work properly.")

if __name__ == "__main__":
    asyncio.run(main())