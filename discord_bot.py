#!/usr/bin/env python3
"""
Discord Bot Integration for RTL Website
Handles verification submissions, role checking, and user notifications
"""

import discord
from discord.ext import commands
import os
import asyncio
import threading
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
print(f"🔍 Discord Bot Token: {'✅ Found' if DISCORD_BOT_TOKEN else '❌ Missing'}")

try:
    DISCORD_GUILD_ID = int(os.environ.get('DISCORD_GUILD_ID', 0)) if os.environ.get('DISCORD_GUILD_ID') else None
    print(f"🔍 Discord Guild ID: {'✅ ' + str(DISCORD_GUILD_ID) if DISCORD_GUILD_ID else '❌ Missing'}")
except ValueError as e:
    print(f"❌ Invalid DISCORD_GUILD_ID format: {e}")
    DISCORD_GUILD_ID = None

try:
    DISCORD_ADMIN_CHANNEL_ID = int(os.environ.get('DISCORD_ADMIN_CHANNEL_ID', 0)) if os.environ.get('DISCORD_ADMIN_CHANNEL_ID') else None
    print(f"🔍 Discord Admin Channel ID: {'✅ ' + str(DISCORD_ADMIN_CHANNEL_ID) if DISCORD_ADMIN_CHANNEL_ID else '❌ Missing'}")
except ValueError as e:
    print(f"❌ Invalid DISCORD_ADMIN_CHANNEL_ID format: {e}")
    DISCORD_ADMIN_CHANNEL_ID = None

LIST_PLAYER_ROLE_NAME = "List Player"  # Role name for Discord commands (no longer required for verification submissions)

# Global variables
bot = None
guild = None
admin_channel = None
DISCORD_BOT_AVAILABLE = False

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class RTLBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def on_ready(self):
        global guild, admin_channel, DISCORD_BOT_AVAILABLE
        print(f'✅ Discord bot logged in as {self.user}')
        
        # Get guild and admin channel
        if DISCORD_GUILD_ID:
            guild = self.get_guild(DISCORD_GUILD_ID)
            if guild:
                print(f'✅ Connected to guild: {guild.name}')
                DISCORD_BOT_AVAILABLE = True
            else:
                print(f'❌ Could not find guild with ID: {DISCORD_GUILD_ID}')
        
        if DISCORD_ADMIN_CHANNEL_ID and guild:
            admin_channel = guild.get_channel(DISCORD_ADMIN_CHANNEL_ID)
            if admin_channel:
                print(f'✅ Connected to admin channel: {admin_channel.name}')
            else:
                print(f'❌ Could not find admin channel with ID: {DISCORD_ADMIN_CHANNEL_ID}')
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        print(f'Discord bot error: {error}')
    
    async def on_message(self, message):
        # Don't respond to our own messages
        if message.author == self.user:
            return
        
        # Check if bot is mentioned
        if self.user in message.mentions:
            # Check if it's just a ping (mention with "ping" or just the mention)
            content = message.content.lower().strip()
            if 'ping' in content or content == f'<@{self.user.id}>' or content == f'<@!{self.user.id}>':
                latency = round(self.latency * 1000)  # Convert to milliseconds
                await message.reply(f'🏓 Pong! Latency: {latency}ms')
                return
        
        # Process commands normally
        await self.process_commands(message)

# Initialize bot instance
if DISCORD_BOT_TOKEN and DISCORD_GUILD_ID and DISCORD_ADMIN_CHANNEL_ID:
    try:
        print("🤖 Creating Discord bot instance...")
        bot = RTLBot()
        print("✅ Discord bot instance created successfully")
    except Exception as e:
        print(f"❌ Failed to create Discord bot instance: {e}")
        bot = None
else:
    missing = []
    if not DISCORD_BOT_TOKEN:
        missing.append("DISCORD_BOT_TOKEN")
    if not DISCORD_GUILD_ID:
        missing.append("DISCORD_GUILD_ID")
    if not DISCORD_ADMIN_CHANNEL_ID:
        missing.append("DISCORD_ADMIN_CHANNEL_ID")
    print(f"❌ Cannot create Discord bot - Missing: {', '.join(missing)}")
    bot = None

def start_discord_bot():
    """Start the Discord bot in a separate thread"""
    if not bot:
        print("❌ Cannot start Discord bot: Bot instance not created")
        return False
        
    if not DISCORD_BOT_TOKEN:
        print("❌ Cannot start Discord bot: No token provided")
        return False
    
    print(f"🔑 Discord bot token found: {DISCORD_BOT_TOKEN[:20]}...")
    print(f"🏠 Guild ID: {DISCORD_GUILD_ID}")
    print(f"📢 Admin Channel ID: {DISCORD_ADMIN_CHANNEL_ID}")
    
    def run_bot():
        try:
            print("🚀 Starting Discord bot event loop...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print("🔗 Connecting to Discord...")
            loop.run_until_complete(bot.start(DISCORD_BOT_TOKEN))
        except discord.LoginFailure as e:
            print(f"❌ Discord login failed - Invalid token: {e}")
        except discord.HTTPException as e:
            print(f"❌ Discord HTTP error: {e}")
        except Exception as e:
            print(f"❌ Discord bot error: {e}")
            import traceback
            traceback.print_exc()
    
    # Start bot in daemon thread so it doesn't prevent app shutdown
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("🤖 Discord bot started in background thread")
    return True

async def get_user_by_discord_id(discord_id):
    """Get Discord user by ID"""
    if not bot or not guild:
        return None
    
    try:
        member = guild.get_member(int(discord_id))
        if not member:
            # Try fetching if not in cache
            member = await guild.fetch_member(int(discord_id))
        return member
    except:
        return None

async def check_user_has_role(discord_id, role_name=LIST_PLAYER_ROLE_NAME):
    """Check if a Discord user has a specific role"""
    if not bot or not guild:
        return False
    
    try:
        member = await get_user_by_discord_id(discord_id)
        if not member:
            return False
        
        # Check if user has the required role
        for role in member.roles:
            if role.name == role_name:
                return True
        return False
    except Exception as e:
        print(f"Error checking user role: {e}")
        return False

async def send_dm_to_discord_user(discord_id, message):
    """Send a DM to a Discord user"""
    if not bot:
        return False
    
    try:
        user = await bot.fetch_user(int(discord_id))
        if user:
            await user.send(message)
            return True
        return False
    except Exception as e:
        print(f"Error sending DM: {e}")
        return False

async def send_admin_notification(message):
    """Send notification to admin channel"""
    if not admin_channel:
        return False
    
    try:
        await admin_channel.send(message)
        return True
    except Exception as e:
        print(f"Error sending admin notification: {e}")
        return False

async def send_verification_embed(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments):
    """Send verification submission as Discord embed"""
    if not admin_channel:
        return False
    
    try:
        # Create embed
        embed = discord.Embed(
            title="📝 New Verification Submission",
            color=0x28a745,  # Green color
            timestamp=datetime.now(timezone.utc)
        )
        
        # Add fields
        embed.add_field(name="👤 Submitted by", value=username, inline=True)
        embed.add_field(name="🎮 Level Name", value=level_name, inline=True)
        embed.add_field(name="📊 Placement", value=f"#{placement}", inline=True)
        
        embed.add_field(name="🎨 Creator", value=creator, inline=True)
        embed.add_field(name="✅ Verifier", value=verifier, inline=True)
        embed.add_field(name="⭐ Difficulty", value=difficulty, inline=True)
        
        embed.add_field(name="🎯 Experience", value=f"{experience}/10", inline=True)
        embed.add_field(name="😊 Enjoyment", value=f"{enjoyment}/10", inline=True)
        embed.add_field(name="🔗 Video", value=f"[Watch Verification]({video_url})", inline=True)
        
        if comments:
            embed.add_field(name="💬 Comments", value=comments[:1000], inline=False)
        
        embed.set_footer(text="RTL Verification System")
        
        await admin_channel.send(embed=embed)
        return True
        
    except Exception as e:
        print(f"Error sending verification embed: {e}")
        return False

# Synchronous wrapper functions for Flask app
def is_bot_available():
    """Check if Discord bot is currently available"""
    return DISCORD_BOT_AVAILABLE

def check_user_role(discord_id, role_name=LIST_PLAYER_ROLE_NAME):
    """Synchronous wrapper to check if user has role"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                check_user_has_role(discord_id, role_name), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in check_user_role: {e}")
    return False

def send_dm_to_user(discord_id, message):
    """Synchronous wrapper to send DM to user"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                send_dm_to_discord_user(discord_id, message), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in send_dm_to_user: {e}")
    return False

def notify_verification_submission(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments):
    """Send notification about new verification submission with embed"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                send_verification_embed(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in notify_verification_submission: {e}")
    return False

def send_changelog_notification(message):
    """Send changelog notification to admin channel"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                send_admin_notification(f"📋 **Changelog Update**\n{message}"), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in send_changelog_notification: {e}")
    return False

# Bot commands (only if bot is available)
if bot is not None:
    @bot.command(name='ping')
    async def ping(ctx):
        """Test command to check if bot is working"""
        latency = round(bot.latency * 1000)  # Convert to milliseconds
        await ctx.send(f'🏓 Pong! RTL Bot is online!\n📡 Latency: {latency}ms')

    @bot.command(name='checkrole')
    async def check_role_command(ctx, member: discord.Member = None):
        """Check if a user has the List Player role (informational only)"""
        if not member:
            member = ctx.author
        
        has_role = await check_user_has_role(member.id)
        role_status = "✅ has" if has_role else "❌ does not have"
        await ctx.send(f"{member.display_name} {role_status} the {LIST_PLAYER_ROLE_NAME} role.")

    @bot.command(name='rtlstatus')
    async def rtl_status(ctx):
        """Show RTL bot status"""
        embed = discord.Embed(
            title="🤖 RTL Bot Status",
            color=0x00ff00 if DISCORD_BOT_AVAILABLE else 0xff0000
        )
        embed.add_field(name="Bot Status", value="✅ Online" if DISCORD_BOT_AVAILABLE else "❌ Offline", inline=True)
        embed.add_field(name="Guild", value=guild.name if guild else "❌ Not connected", inline=True)
        embed.add_field(name="Admin Channel", value=admin_channel.name if admin_channel else "❌ Not configured", inline=True)
        embed.add_field(name="Required Role", value=LIST_PLAYER_ROLE_NAME, inline=True)
        embed.timestamp = datetime.now(timezone.utc)
        
        await ctx.send(embed=embed)

if __name__ == "__main__":
    # For testing the bot standalone
    if DISCORD_BOT_TOKEN:
        bot.run(DISCORD_BOT_TOKEN)
    else:
        print("❌ No Discord bot token provided")