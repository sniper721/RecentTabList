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
    DISCORD_GUILD_ID = 1386176113448845322  # Hardcoded server ID
    print(f"🔍 Discord Guild ID: {'✅ ' + str(DISCORD_GUILD_ID) if DISCORD_GUILD_ID else '❌ Missing'}")
except ValueError as e:
    print(f"❌ Invalid DISCORD_GUILD_ID format: {e}")
    DISCORD_GUILD_ID = 1386176113448845322  # Fallback to hardcoded server ID

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
mongo_db = None  # MongoDB reference to be set from main.py

# Points milestone roles mapping
POINTS_ROLES = {
    1: "1407154476900548638",      # 1+ points
    50: "1434561864477708412",     # 50+ points
    100: "1434559158056910859",    # 100+ points
    150: "1434559357978284072",    # 150+ points
    200: "1434559491164078210",    # 200+ points
    250: "1434559736430334013",    # 250+ points
    300: "1434559950142832812",    # 300+ points
    350: "1434560160193450056",    # 350+ points
    400: "1434560335540654170",    # 400+ points
    450: "1434560559315030279",    # 450+ points
    500: "1434560792845353073",    # 500+ points
    600: "1434562564607447072",    # 600+ points
    700: "1434562844678029322",    # 700+ points
    800: "1434563139302854796",    # 800+ points
    900: "1434563355917680722",    # 900+ points
    1000: "1434563588349100135",   # 1000+ points
    1500: "1434563863126474782",   # 1500+ points
    2000: "1434564153032315120",   # 2000+ points
    2500: "1434564465084596325",   # 2500+ points
    3000: "1434564672949977219",   # 3000+ points
    3500: "1434564972083413123",   # 3500+ points
    4000: "1434566288256012393"    # 4000+ points
}

# Additional achievement roles mapping
ACHIEVEMENT_ROLES = {
    "completed_entire_list": "1407749092821565632",      # Has beaten the entire list at least once!
    "stats_viewer_top_1": "1434573744889794591",         # you're the #1 player on the stats viewer
    "stats_viewer_top_10": "1434089770040168499",        # you're in the top 10 players on the stats viewer
    "current_top_1": "1387947809948307516",              # Role for completing the current top 1, gets taken after being dethroned
    "top_5_completer": "1387947951426371735",            # Role for those who have completed a level in the top 5 of the main list
    "top_10_completer": "1387948023073738792",           # Role for those who have completed a level in the top 10 of the main list
    "future_list_verifier": "1418198223851618327",       # You've verified a level in the future list
    "list_verifier": "1387982674043338804",              # Role for people who have verified a level currently on the list
    "first_victor": "1387982763549790229"                # Role for people who are the first victor of a level on the list
}

# Role names for notifications
ROLE_NAMES = {
    "1407154476900548638": "List Player",
    "1434561864477708412": "50+ Points",
    "1434559158056910859": "100+ Points",
    "1434559357978284072": "150+ Points",
    "1434559491164078210": "200+ Points",
    "1434559736430334013": "250+ Points",
    "1434559950142832812": "300+ Points",
    "1434560160193450056": "350+ Points",
    "1434560335540654170": "400+ Points",
    "1434560559315030279": "450+ Points",
    "1434560792845353073": "500+ Points",
    "1434562564607447072": "600+ Points",
    "1434562844678029322": "700+ Points",
    "1434563139302854796": "800+ Points",
    "1434563355917680722": "900+ Points",
    "1434563588349100135": "1000+ Points",
    "1434563863126474782": "1500+ Points",
    "1434564153032315120": "2000+ Points",
    "1434564465084596325": "2500+ Points",
    "1434564672949977219": "3000+ Points",
    "1434564972083413123": "3500+ Points",
    "1434566288256012393": "4000+ Points",
    # Additional roles
    "1407749092821565632": "Completed Entire List",
    "1434573744889794591": "#1 Player on Stats Viewer",
    "1434089770040168499": "Top 10 Player on Stats Viewer",
    "1387947809948307516": "Current Top 1 Player",
    "1387947951426371735": "Top 5 Level Completer",
    "1387948023073738792": "Top 10 Level Completer",
    "1418198223851618327": "Future List Verifier",
    "1387982674043338804": "List Verifier",
    "1387982763549790229": "First Victor"
}

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
        
        # Check and update user roles based on their points
        if DISCORD_BOT_AVAILABLE:
            print("🔄 Starting automatic role synchronization for all users...")
            try:
                await sync_all_user_roles()
                print("✅ Role synchronization completed successfully")
            except Exception as e:
                print(f"❌ Error during role synchronization: {e}")
                import traceback
                traceback.print_exc()
    
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

async def assign_role_to_user(discord_id, role_id):
    """Assign a role to a user by their Discord ID"""
    if not bot or not guild:
        return False
    
    try:
        # Get the member
        member = await get_user_by_discord_id(discord_id)
        if not member:
            print(f"Could not find member with ID {discord_id}")
            return False
        
        # Get the role
        role = guild.get_role(int(role_id))
        if not role:
            print(f"Could not find role with ID {role_id}")
            return False
        
        # Assign the role
        await member.add_roles(role, reason="RTL Points Milestone")
        print(f"✅ Assigned role {role.name} to {member.display_name}")
        return True
    except Exception as e:
        print(f"Error assigning role: {e}")
        return False

async def remove_role_from_user(discord_id, role_id):
    """Remove a role from a user by their Discord ID"""
    if not bot or not guild:
        return False
    
    try:
        # Get the member
        member = await get_user_by_discord_id(discord_id)
        if not member:
            print(f"Could not find member with ID {discord_id}")
            return False
        
        # Get the role
        role = guild.get_role(int(role_id))
        if not role:
            print(f"Could not find role with ID {role_id}")
            return False
        
        # Remove the role
        await member.remove_roles(role, reason="RTL Points Milestone")
        print(f"✅ Removed role {role.name} from {member.display_name}")
        return True
    except Exception as e:
        print(f"Error removing role: {e}")
        return False

# Synchronous wrapper functions for Flask app
def is_bot_available():
    """Check if Discord bot is currently available"""
    return DISCORD_BOT_AVAILABLE

def assign_discord_role(discord_id, role_id):
    """Synchronous wrapper to assign a role to a user"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                assign_role_to_user(discord_id, role_id), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in assign_discord_role: {e}")
    return False

def remove_discord_role(discord_id, role_id):
    """Synchronous wrapper to remove a role from a user"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                remove_role_from_user(discord_id, role_id), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in remove_discord_role: {e}")
    return False

def assign_verifier_role(discord_id):
    """Assign the List Verifier role to a user"""
    role_id = "1387982674043338804"  # List Verifier role ID
    return assign_discord_role(discord_id, role_id)

def assign_future_list_verifier_role(discord_id):
    """Assign the Future List Verifier role to a user"""
    role_id = "1418198223851618327"  # Future List Verifier role ID
    return assign_discord_role(discord_id, role_id)

def assign_top_1_player_role(discord_id):
    """Assign the Current Top 1 Player role to a user"""
    role_id = "1387947809948307516"  # Current Top 1 Player role ID
    return assign_discord_role(discord_id, role_id)

def remove_top_1_player_role(discord_id):
    """Remove the Current Top 1 Player role from a user"""
    role_id = "1387947809948307516"  # Current Top 1 Player role ID
    return remove_discord_role(discord_id, role_id)

def assign_completed_entire_list_role(discord_id):
    """Assign the Completed Entire List role to a user"""
    role_id = "1407749092821565632"  # Completed Entire List role ID
    return assign_discord_role(discord_id, role_id)

def assign_stats_viewer_top_1_role(discord_id):
    """Assign the #1 Player on Stats Viewer role to a user"""
    role_id = "1434573744889794591"  # #1 Player on Stats Viewer role ID
    return assign_discord_role(discord_id, role_id)

def assign_stats_viewer_top_10_role(discord_id):
    """Assign the Top 10 Player on Stats Viewer role to a user"""
    role_id = "1434089770040168499"  # Top 10 Player on Stats Viewer role ID
    return assign_discord_role(discord_id, role_id)

def assign_current_top_1_role(discord_id):
    """Assign the Current Top 1 Player role to a user"""
    role_id = "1387947809948307516"  # Current Top 1 Player role ID
    return assign_discord_role(discord_id, role_id)

def assign_top_5_completer_role(discord_id):
    """Assign the Top 5 Level Completer role to a user"""
    role_id = "1387947951426371735"  # Top 5 Level Completer role ID
    return assign_discord_role(discord_id, role_id)

def assign_top_10_completer_role(discord_id):
    """Assign the Top 10 Level Completer role to a user"""
    role_id = "1387948023073738792"  # Top 10 Level Completer role ID
    return assign_discord_role(discord_id, role_id)

def assign_first_victor_role(discord_id):
    """Assign the First Victor role to a user"""
    role_id = "1387982763549790229"  # First Victor role ID
    return assign_discord_role(discord_id, role_id)

async def send_verification_embed(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments, level_id=None):
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
        
        # Add Level ID if provided - make it more prominent
        if level_id:
            embed.add_field(name="🆔 Level ID", value=f"**{level_id}**", inline=True)
        else:
            embed.add_field(name="🆔 Level ID", value="**Not provided**", inline=True)
        
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

def notify_verification_submission(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments, level_id=None):
    """Send notification about new verification submission with embed"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                send_verification_embed(username, level_name, creator, verifier, difficulty, placement, experience, enjoyment, video_url, comments, level_id), loop
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

async def sync_all_user_roles():
    """Synchronize all users' Discord roles based on their current points"""
    global bot, guild
    
    if not bot or not guild:
        print("❌ Cannot sync roles: Bot or guild not available")
        return False
    
    try:
        # Import MongoDB reference - this will be set from main.py
        from discord_bot import mongo_db
        if mongo_db is None:
            print("❌ Cannot sync roles: MongoDB not available")
            return False
            
        # Get all users with Discord connections
        users_with_discord = list(mongo_db.users.find({"discord_id": {"$exists": True, "$ne": None}}))
        print(f"🔍 Found {len(users_with_discord)} users with Discord connections")
        
        # Import role mappings and functions
        from discord_bot import POINTS_ROLES, ROLE_NAMES, remove_role_from_user, assign_role_to_user
        
        # Sort milestones in descending order for proper role assignment
        sorted_milestones = sorted(POINTS_ROLES.items(), key=lambda x: x[0], reverse=True)
        
        updated_users = 0
        error_users = 0
        
        for user in users_with_discord:
            try:
                discord_id = user.get('discord_id')
                username = user.get('username', 'Unknown')
                current_points = user.get('points', 0)
                
                print(f"🔄 Checking roles for user: {username} (ID: {discord_id}, Points: {current_points})")
                
                # Get current user's Discord roles
                member = await get_user_by_discord_id(discord_id)
                if not member:
                    print(f"⚠️ Could not find Discord member for user {username}")
                    continue
                
                user_role_ids = [str(role.id) for role in member.roles]
                
                # Remove roles for milestones no longer achieved
                for points_threshold, role_id in sorted_milestones:
                    if str(role_id) in user_role_ids and current_points < points_threshold:
                        # User has role but no longer qualifies
                        role_name = ROLE_NAMES.get(str(role_id), f"{points_threshold}+ Points")
                        print(f"⬇️ Removing role '{role_name}' from {username} (points: {current_points} < threshold: {points_threshold})")
                        await remove_role_from_user(discord_id, role_id)
                
                # Add roles for milestones achieved (assign highest milestone and all below it)
                highest_qualified_milestone = 0
                for points_threshold, role_id in sorted_milestones:
                    if current_points >= points_threshold:
                        highest_qualified_milestone = points_threshold
                        break
                
                # Assign all roles up to the highest qualified milestone
                if highest_qualified_milestone > 0:
                    for points_threshold, role_id in sorted_milestones:
                        if points_threshold <= highest_qualified_milestone:
                            role_name = ROLE_NAMES.get(str(role_id), f"{points_threshold}+ Points")
                            if str(role_id) not in user_role_ids:
                                # User qualifies but doesn't have the role
                                print(f"⬆️ Assigning role '{role_name}' to {username} (points: {current_points} >= threshold: {points_threshold})")
                                await assign_role_to_user(discord_id, role_id)
                
                updated_users += 1
                
            except Exception as e:
                print(f"❌ Error processing user {user.get('username', 'Unknown')}: {e}")
                error_users += 1
                continue
        
        print(f"✅ Role synchronization complete: {updated_users} users processed, {error_users} errors")
        
        # Update the last sync timestamp
        try:
            from discord_bot import mongo_db
            if mongo_db:
                # Store the last sync time in site_settings
                mongo_db.site_settings.update_one(
                    {"_id": "discord_bot"},
                    {"$set": {"last_role_sync": datetime.now(timezone.utc)}},
                    upsert=True
                )
                print("✅ Updated last role sync timestamp")
        except Exception as e:
            print(f"⚠️ Could not update last sync timestamp: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in sync_all_user_roles: {e}")
        import traceback
        traceback.print_exc()
        return False
