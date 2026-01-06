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
        
        # Auto-start level monitoring if it was enabled before restart
        if DISCORD_BOT_AVAILABLE and mongo_db:
            try:
                from level_monitor import auto_start_level_monitor_if_enabled, get_level_monitor
                monitor = auto_start_level_monitor_if_enabled(mongo_db, self)
                if monitor:
                    # If monitor was created but not started due to event loop issues, start it now
                    if not monitor.running:
                        success = monitor.start_monitoring_task(self.loop)
                        if success:
                            print("✅ Level monitoring started successfully with Discord bot event loop")
                        else:
                            print("❌ Failed to start level monitoring even with Discord bot event loop")
                    else:
                        print("✅ Level monitoring auto-started (was enabled before restart)")
                else:
                    print("ℹ️ Level monitoring not auto-started (was disabled before restart)")
            except Exception as e:
                print(f"⚠️ Could not auto-start level monitoring: {e}")
                import traceback
                traceback.print_exc()
        
        # Check and update user roles based on their points (only for users who need updates)
        if DISCORD_BOT_AVAILABLE:
            # Check if role sync on startup is enabled (can be disabled via environment variable)
            startup_sync_enabled = os.environ.get('DISCORD_STARTUP_ROLE_SYNC', 'true').lower() == 'true'
            
            if startup_sync_enabled:
                print("🔄 Starting smart role synchronization (only updating users who need changes)...")
                try:
                    await sync_user_roles_smart()
                    print("✅ Smart role synchronization completed successfully")
                except Exception as e:
                    print(f"❌ Error during role synchronization: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("⏭️ Startup role synchronization disabled via DISCORD_STARTUP_ROLE_SYNC=false")
                print("💡 Use !syncsmartroles command to manually sync roles when needed")
    
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

def sync_single_user_roles(discord_id, current_points):
    """Synchronize roles for a single user based on their current points"""
    if not bot or not DISCORD_BOT_AVAILABLE:
        return False
    
    try:
        loop = bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                sync_single_user_roles_async(discord_id, current_points), loop
            )
            return future.result(timeout=10)
    except Exception as e:
        print(f"Error in sync_single_user_roles: {e}")
    return False

async def sync_single_user_roles_async(discord_id, current_points):
    """Async function to synchronize roles for a single user"""
    try:
        # Get current user's Discord roles
        member = await get_user_by_discord_id(discord_id)
        if not member:
            print(f"⚠️ Could not find Discord member for ID {discord_id}")
            return False
        
        user_role_ids = [str(role.id) for role in member.roles]
        
        # Sort milestones in descending order for proper role assignment
        sorted_milestones = sorted(POINTS_ROLES.items(), key=lambda x: x[0], reverse=True)
        
        # Find the highest milestone the user qualifies for
        highest_qualified_milestone = 0
        highest_qualified_role_id = None
        for points_threshold, role_id in sorted_milestones:
            if current_points >= points_threshold:
                highest_qualified_milestone = points_threshold
                highest_qualified_role_id = role_id
                break
        
        # Check if user already has the correct role
        needs_update = False
        current_milestone_roles = []
        
        for points_threshold, role_id in sorted_milestones:
            if str(role_id) in user_role_ids:
                current_milestone_roles.append((points_threshold, role_id))
        
        # Determine if update is needed
        if not current_milestone_roles and highest_qualified_milestone > 0:
            needs_update = True
        elif current_milestone_roles:
            # Check if user has the correct role and only that role
            has_correct_role = highest_qualified_role_id and str(highest_qualified_role_id) in user_role_ids
            has_only_one_role = len(current_milestone_roles) == 1
            
            if not (has_correct_role and has_only_one_role):
                needs_update = True
        elif current_milestone_roles and highest_qualified_milestone == 0:
            needs_update = True
        
        if needs_update:
            print(f"🔄 Updating roles for Discord user {discord_id} (Points: {current_points})")
            
            # Remove ALL milestone roles first
            for points_threshold, role_id in sorted_milestones:
                if str(role_id) in user_role_ids:
                    await remove_role_from_user(discord_id, role_id)
            
            # Assign only the highest qualified milestone role
            if highest_qualified_milestone > 0 and highest_qualified_role_id:
                role_name = ROLE_NAMES.get(str(highest_qualified_role_id), f"{highest_qualified_milestone}+ Points")
                print(f"⬆️ Assigning role '{role_name}' to Discord user {discord_id}")
                await assign_role_to_user(discord_id, highest_qualified_role_id)
            
            return True
        else:
            print(f"✅ Discord user {discord_id} already has correct roles (Points: {current_points})")
            return True
            
    except Exception as e:
        print(f"❌ Error syncing roles for Discord user {discord_id}: {e}")
        return False

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

    @bot.command(name='syncallroles')
    @commands.has_permissions(administrator=True)
    async def sync_all_roles_command(ctx):
        """Admin command to manually trigger a full role synchronization"""
        await ctx.send("🔄 Starting full role synchronization for all users... This may take a while.")
        
        try:
            success = await sync_all_user_roles()
            if success:
                await ctx.send("✅ Full role synchronization completed successfully!")
            else:
                await ctx.send("❌ Role synchronization failed. Check bot logs for details.")
        except Exception as e:
            await ctx.send(f"❌ Error during role synchronization: {str(e)}")

    @bot.command(name='syncsmartroles')
    @commands.has_permissions(administrator=True)
    async def sync_smart_roles_command(ctx):
        """Admin command to trigger smart role synchronization (only users who need updates)"""
        await ctx.send("🔄 Starting smart role synchronization (only updating users who need changes)...")
        
        try:
            success = await sync_user_roles_smart()
            if success:
                await ctx.send("✅ Smart role synchronization completed successfully!")
            else:
                await ctx.send("❌ Role synchronization failed. Check bot logs for details.")
        except Exception as e:
            await ctx.send(f"❌ Error during role synchronization: {str(e)}")

    @bot.command(name='startmonitor')
    @commands.has_permissions(administrator=True)
    async def start_monitor_command(ctx):
        """Admin command to start level monitoring"""
        try:
            from level_monitor import start_level_monitor, get_level_monitor
            
            existing_monitor = get_level_monitor()
            if existing_monitor and existing_monitor.running:
                await ctx.send("⚠️ Level monitor is already running!")
                return
                
            monitor = start_level_monitor(mongo_db, bot)
            if monitor:
                await ctx.send("✅ Level monitor started! Will check for removed levels every 5 minutes.")
            else:
                await ctx.send("❌ Failed to start level monitor.")
                
        except Exception as e:
            await ctx.send(f"❌ Error starting level monitor: {str(e)}")

    @bot.command(name='stopmonitor')
    @commands.has_permissions(administrator=True)
    async def stop_monitor_command(ctx):
        """Admin command to stop level monitoring"""
        try:
            from level_monitor import stop_level_monitor, get_level_monitor
            
            monitor = get_level_monitor()
            if not monitor or not monitor.running:
                await ctx.send("⚠️ Level monitor is not running!")
                return
                
            stop_level_monitor()
            await ctx.send("✅ Level monitor stopped.")
            
        except Exception as e:
            await ctx.send(f"❌ Error stopping level monitor: {str(e)}")

    @bot.command(name='monitorstatus')
    @commands.has_permissions(administrator=True)
    async def monitor_status_command(ctx):
        """Admin command to check level monitor status"""
        try:
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            if monitor and monitor.running:
                interval_minutes = monitor.check_interval // 60
                embed = discord.Embed(
                    title="🔍 Level Monitor Status",
                    color=0x00ff00,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Status", value="✅ Running", inline=True)
                embed.add_field(name="Check Interval", value=f"{interval_minutes} minutes", inline=True)
                embed.add_field(name="Session", value="✅ Active" if monitor.session else "❌ Inactive", inline=True)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🔍 Level Monitor Status",
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Status", value="❌ Not Running", inline=True)
                embed.add_field(name="Info", value="Use `!startmonitor` to start monitoring", inline=False)
                await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error checking monitor status: {str(e)}")

    @bot.command(name='setmonitorinterval')
    @commands.has_permissions(administrator=True)
    async def set_monitor_interval_command(ctx, minutes: int):
        """Admin command to set level monitor check interval"""
        try:
            if minutes < 1 or minutes > 1440:  # 1 minute to 24 hours
                await ctx.send("❌ Interval must be between 1 and 1440 minutes (24 hours).")
                return
                
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            if monitor:
                monitor.set_check_interval(minutes)
                embed = discord.Embed(
                    title="⏰ Monitor Interval Updated",
                    color=0x00ff00,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="New Interval", value=f"{minutes} minutes", inline=True)
                embed.add_field(name="Persistent", value="✅ Saved (survives restarts)", inline=True)
                embed.add_field(name="Next Check", value=f"In {minutes} minutes", inline=True)
                embed.set_footer(text="Level Monitor Configuration")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Level monitor is not running. Start it first with `!startchecks`.")
                
        except ValueError:
            await ctx.send("❌ Please provide a valid number of minutes.")
        except Exception as e:
            await ctx.send(f"❌ Error setting monitor interval: {str(e)}")

    @bot.command(name='checklevelnow')
    @commands.has_permissions(administrator=True)
    async def check_level_now_command(ctx, level_id: str):
        """Admin command to manually check if a specific GD level ID exists"""
        try:
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            if not monitor or not monitor.running:
                await ctx.send("❌ Level checking is disabled. Use `!startchecks` to enable checking.")
                return
            
            # Validate level_id is numeric
            try:
                int(level_id)
            except ValueError:
                await ctx.send("❌ Level ID must be a number (e.g. `!checklevelnow 12345678`)")
                return
                
            await ctx.send(f"🔍 Checking GD level ID {level_id}...")
            
            exists = await monitor.check_level_exists(level_id)
            
            embed = discord.Embed(
                title=f"🔍 Level Check Result",
                color=0x00ff00 if exists else 0xff0000,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="GD Level ID", value=level_id, inline=True)
            embed.add_field(name="Status", value="✅ EXISTS" if exists else "❌ NOT FOUND", inline=True)
            
            if exists:
                embed.add_field(name="Result", value="Level is accessible on GD servers", inline=False)
            else:
                embed.add_field(name="Result", value="Level was not found on GD servers (may be removed)", inline=False)
            
            embed.set_footer(text="Manual Level Check")
            await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error checking level: {str(e)}")

    @bot.command(name='checklevel')
    @commands.has_permissions(administrator=True)
    async def check_level_by_name_command(ctx, *, level_name: str):
        """Admin command to check a level from the database by name"""
        try:
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            if not monitor or not monitor.running:
                await ctx.send("❌ Level checking is disabled. Use `!startchecks` to enable checking.")
                return
            
            # Search for level in database (case insensitive)
            level = mongo_db.levels.find_one({
                "name": {"$regex": f"^{level_name}$", "$options": "i"}
            })
            
            if not level:
                await ctx.send(f"❌ Level '{level_name}' not found in database.")
                return
            
            level_gd_id = level.get('level_id')
            if not level_gd_id:
                await ctx.send(f"❌ Level '{level_name}' has no GD level ID in database.")
                return
            
            position = level.get('position', '?')
            is_legacy = level.get('is_legacy', False)
            list_type = "Legacy List" if is_legacy else "Main List"
            
            await ctx.send(f"🔍 Checking '{level_name}' (GD ID: {level_gd_id})...")
            
            exists = await monitor.check_level_exists(level_gd_id)
            
            embed = discord.Embed(
                title=f"🔍 Level Check: {level['name']}",
                color=0x00ff00 if exists else 0xff0000,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="Level Name", value=level['name'], inline=True)
            embed.add_field(name="GD Level ID", value=str(level_gd_id), inline=True)
            embed.add_field(name="Position", value=f"#{position} ({list_type})", inline=True)
            
            embed.add_field(name="Creator", value=level.get('creator', 'Unknown'), inline=True)
            embed.add_field(name="Verifier", value=level.get('verifier', 'Unknown'), inline=True)
            embed.add_field(name="Status", value="✅ EXISTS" if exists else "❌ NOT FOUND", inline=True)
            
            if exists:
                embed.add_field(name="Result", value="✅ Level is accessible on GD servers", inline=False)
            else:
                embed.add_field(name="Result", value="❌ Level was not found on GD servers (may be removed)", inline=False)
            
            embed.set_footer(text="Database Level Check")
            await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error checking level: {str(e)}")

    @bot.command(name='stopchecking')
    @commands.has_permissions(administrator=True)
    async def stop_checking_command(ctx):
        """Admin command to stop all level checking (monitoring and manual checks)"""
        try:
            from level_monitor import get_level_monitor, stop_level_monitor
            
            monitor = get_level_monitor()
            if monitor and monitor.running:
                # Use the monitor's stop method to save persistent state
                await monitor.stop_monitoring()
                
                embed = discord.Embed(
                    title="🛑 Level Checking Stopped",
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Status", value="❌ All level checking stopped", inline=False)
                embed.add_field(name="Automatic Monitoring", value="❌ Disabled", inline=True)
                embed.add_field(name="Manual Checks", value="❌ Disabled", inline=True)
                embed.add_field(name="Persistent State", value="❌ Saved (won't auto-start after restarts)", inline=True)
                embed.add_field(name="To Resume", value="Use `!startchecks` to resume all checking", inline=False)
                embed.set_footer(text="Level Monitor Control • Enhanced with Persistence")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("⚠️ Level checking is not currently running.")
                
        except Exception as e:
            await ctx.send(f"❌ Error stopping level checking: {str(e)}")

    @bot.command(name='startchecks')
    @commands.has_permissions(administrator=True)
    async def start_checks_command(ctx):
        """Admin command to start/resume all level checking"""
        try:
            from level_monitor import start_level_monitor, get_level_monitor
            
            existing_monitor = get_level_monitor()
            if existing_monitor and existing_monitor.running:
                await ctx.send("⚠️ Level checking is already running!")
                return
                
            monitor = start_level_monitor(mongo_db, bot)
            if monitor:
                # Ensure the monitor is actually running
                if not monitor.running:
                    success = monitor.start_monitoring_task(bot.loop)
                    if not success:
                        await ctx.send("❌ Failed to start level monitoring task.")
                        return
                
                embed = discord.Embed(
                    title="✅ Level Checking Started",
                    color=0x00ff00,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="Status", value="✅ All level checking enabled", inline=False)
                embed.add_field(name="Automatic Monitoring", value="✅ Running every 30 minutes", inline=True)
                embed.add_field(name="Manual Checks", value="✅ Available", inline=True)
                embed.add_field(name="Persistent State", value="✅ Saved (will auto-start after restarts)", inline=True)
                embed.add_field(name="Available Commands", value="`!checklevelnow <id>`, `!checklevel <name>`, `!checkalllevels`", inline=False)
                embed.set_footer(text="Level Monitor Control • Enhanced with Persistence")
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to start level checking.")
                
        except Exception as e:
            await ctx.send(f"❌ Error starting level checking: {str(e)}")
            import traceback
            traceback.print_exc()

    @bot.command(name='checkingstatus')
    @commands.has_permissions(administrator=True)
    async def checking_status_command(ctx):
        """Admin command to check the status of level checking system"""
        try:
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            
            embed = discord.Embed(
                title="📊 Level Checking Status",
                timestamp=datetime.now(timezone.utc)
            )
            
            if monitor and monitor.running:
                embed.color = 0x00ff00
                embed.add_field(name="Monitor Status", value="✅ Running", inline=True)
                embed.add_field(name="Check Interval", value=f"{monitor.check_interval // 60} minutes", inline=True)
                embed.add_field(name="Session Status", value="✅ Active" if monitor.session else "❌ Inactive", inline=True)
                embed.add_field(name="Manual Checks", value="✅ Available", inline=True)
                embed.add_field(name="Auto Monitoring", value="✅ Active", inline=True)
                embed.add_field(name="Persistent State", value="✅ Enabled (survives restarts)", inline=True)
                embed.add_field(name="Control", value="Use `!stopchecking` to stop", inline=False)
            else:
                embed.color = 0xff0000
                embed.add_field(name="Monitor Status", value="❌ Not Running", inline=True)
                embed.add_field(name="Manual Checks", value="❌ Unavailable", inline=True)
                embed.add_field(name="Auto Monitoring", value="❌ Disabled", inline=True)
                
                # Check if it's enabled in settings but not running
                if monitor and monitor.is_enabled_in_settings():
                    embed.add_field(name="Persistent State", value="⚠️ Enabled but not running", inline=True)
                    embed.add_field(name="Issue", value="Monitor should be running but isn't", inline=True)
                else:
                    embed.add_field(name="Persistent State", value="❌ Disabled (won't auto-start)", inline=True)
                
                embed.add_field(name="Control", value="Use `!startchecks` to start", inline=False)
            
            embed.set_footer(text="Level Monitor System • Enhanced with Persistent State")
            await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error checking status: {str(e)}")

    @bot.command(name='checkalllevels')
    @commands.has_permissions(administrator=True)
    async def check_all_levels_command(ctx):
        """Admin command to manually check all levels for removal"""
        try:
            from level_monitor import get_level_monitor
            
            monitor = get_level_monitor()
            if not monitor:
                await ctx.send("❌ Level monitor is not running. Start it first with `!startmonitor`.")
                return
                
            await ctx.send("🔍 Starting manual check of all levels... This may take a while.")
            
            # Run the check in the background
            asyncio.create_task(monitor.check_all_levels())
            
            await ctx.send("✅ Level check started! You'll be notified of any removed levels.")
            
        except Exception as e:
            await ctx.send(f"❌ Error checking all levels: {str(e)}")

    @bot.command(name='levelstats')
    @commands.has_permissions(administrator=True)
    async def level_stats_command(ctx):
        """Show statistics about levels in the database"""
        try:
            # Count levels with and without level_id
            total_levels = mongo_db.levels.count_documents({})
            levels_with_id = mongo_db.levels.count_documents({"level_id": {"$exists": True, "$ne": None, "$ne": ""}})
            levels_without_id = total_levels - levels_with_id
            removed_levels = mongo_db.levels.count_documents({"is_removed": True})
            main_levels = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
            legacy_levels = mongo_db.levels.count_documents({"is_legacy": True})
            
            embed = discord.Embed(
                title="📊 Level Database Statistics",
                color=0x0099ff,
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="📈 Total Levels", value=str(total_levels), inline=True)
            embed.add_field(name="🏆 Main List", value=str(main_levels), inline=True)
            embed.add_field(name="🕰️ Legacy List", value=str(legacy_levels), inline=True)
            
            embed.add_field(name="🆔 With GD Level ID", value=str(levels_with_id), inline=True)
            embed.add_field(name="❓ Without GD Level ID", value=str(levels_without_id), inline=True)
            embed.add_field(name="🚫 Marked as Removed", value=str(removed_levels), inline=True)
            
            monitorable = levels_with_id - removed_levels
            embed.add_field(name="🔍 Monitorable Levels", value=str(monitorable), inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting level stats: {str(e)}")

if __name__ == "__main__":
    # For testing the bot standalone
    if DISCORD_BOT_TOKEN:
        bot.run(DISCORD_BOT_TOKEN)
    else:
        print("❌ No Discord bot token provided")

async def sync_user_roles_smart():
    """Smart role synchronization - only update users who actually need role changes"""
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
        
        users_needing_updates = 0
        users_already_correct = 0
        error_users = 0
        
        for user in users_with_discord:
            try:
                discord_id = user.get('discord_id')
                username = user.get('username', 'Unknown')
                current_points = user.get('points', 0)
                
                # Get current user's Discord roles
                member = await get_user_by_discord_id(discord_id)
                if not member:
                    print(f"⚠️ Could not find Discord member for user {username}")
                    continue
                
                user_role_ids = [str(role.id) for role in member.roles]
                
                # Find the highest milestone the user qualifies for
                highest_qualified_milestone = 0
                highest_qualified_role_id = None
                for points_threshold, role_id in sorted_milestones:
                    if current_points >= points_threshold:
                        highest_qualified_milestone = points_threshold
                        highest_qualified_role_id = role_id
                        break
                
                # Check what milestone roles the user currently has
                current_milestone_roles = []
                for points_threshold, role_id in sorted_milestones:
                    if str(role_id) in user_role_ids:
                        current_milestone_roles.append((points_threshold, role_id))
                
                # Determine if user needs role updates
                needs_update = False
                
                # Case 1: User has no milestone roles but should have one
                if not current_milestone_roles and highest_qualified_milestone > 0:
                    needs_update = True
                    print(f"📝 {username} needs role: No roles but qualifies for {highest_qualified_milestone}+ points")
                
                # Case 2: User has milestone roles but not the correct one
                elif current_milestone_roles:
                    # Check if user has the correct highest role
                    has_correct_role = False
                    if highest_qualified_role_id:
                        has_correct_role = str(highest_qualified_role_id) in user_role_ids
                    
                    # Check if user has multiple milestone roles (should only have one)
                    has_multiple_roles = len(current_milestone_roles) > 1
                    
                    # Check if user has wrong role (lower than they qualify for)
                    has_wrong_role = False
                    if not has_correct_role and highest_qualified_milestone > 0:
                        has_wrong_role = True
                    
                    # Check if user has role they don't qualify for (higher than their points)
                    has_unqualified_role = False
                    for points_threshold, role_id in current_milestone_roles:
                        if current_points < points_threshold:
                            has_unqualified_role = True
                            break
                    
                    if has_multiple_roles or has_wrong_role or has_unqualified_role:
                        needs_update = True
                        reasons = []
                        if has_multiple_roles:
                            reasons.append(f"has {len(current_milestone_roles)} roles (should have 1)")
                        if has_wrong_role:
                            reasons.append(f"missing {highest_qualified_milestone}+ role")
                        if has_unqualified_role:
                            reasons.append("has unqualified roles")
                        print(f"📝 {username} needs role update: {', '.join(reasons)}")
                
                # Case 3: User has milestone roles but qualifies for none (0 points)
                elif current_milestone_roles and highest_qualified_milestone == 0:
                    needs_update = True
                    print(f"📝 {username} needs role removal: Has roles but 0 points")
                
                # Only update if needed
                if needs_update:
                    print(f"🔄 Updating roles for {username} (Points: {current_points})")
                    
                    # Remove ALL milestone roles first
                    for points_threshold, role_id in sorted_milestones:
                        if str(role_id) in user_role_ids:
                            role_name = ROLE_NAMES.get(str(role_id), f"{points_threshold}+ Points")
                            await remove_role_from_user(discord_id, role_id)
                    
                    # Assign only the highest qualified milestone role
                    if highest_qualified_milestone > 0 and highest_qualified_role_id:
                        role_name = ROLE_NAMES.get(str(highest_qualified_role_id), f"{highest_qualified_milestone}+ Points")
                        print(f"⬆️ Assigning role '{role_name}' to {username}")
                        await assign_role_to_user(discord_id, highest_qualified_role_id)
                    
                    users_needing_updates += 1
                else:
                    users_already_correct += 1
                
            except Exception as e:
                print(f"❌ Error processing user {user.get('username', 'Unknown')}: {e}")
                error_users += 1
                continue
        
        print(f"✅ Smart role sync complete: {users_needing_updates} users updated, {users_already_correct} already correct, {error_users} errors")
        
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
        print(f"❌ Error in sync_user_roles_smart: {e}")
        import traceback
        traceback.print_exc()
        return False

async def sync_all_user_roles():
    """Synchronize all users' Discord roles based on their current points (FULL SYNC - use sparingly)"""
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
        print(f"🔍 FULL SYNC: Found {len(users_with_discord)} users with Discord connections")
        
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
                
                print(f"🔄 FULL SYNC: Checking roles for user: {username} (ID: {discord_id}, Points: {current_points})")
                
                # Get current user's Discord roles
                member = await get_user_by_discord_id(discord_id)
                if not member:
                    print(f"⚠️ Could not find Discord member for user {username}")
                    continue
                
                user_role_ids = [str(role.id) for role in member.roles]
                
                # Find the highest milestone the user qualifies for
                highest_qualified_milestone = 0
                highest_qualified_role_id = None
                for points_threshold, role_id in sorted_milestones:
                    if current_points >= points_threshold:
                        highest_qualified_milestone = points_threshold
                        highest_qualified_role_id = role_id
                        break
                
                # Remove ALL milestone roles first
                for points_threshold, role_id in sorted_milestones:
                    if str(role_id) in user_role_ids:
                        role_name = ROLE_NAMES.get(str(role_id), f"{points_threshold}+ Points")
                        print(f"⬇️ Removing role '{role_name}' from {username} for role cleanup")
                        await remove_role_from_user(discord_id, role_id)
                
                # Assign only the highest qualified milestone role
                if highest_qualified_milestone > 0 and highest_qualified_role_id:
                    role_name = ROLE_NAMES.get(str(highest_qualified_role_id), f"{highest_qualified_milestone}+ Points")
                    print(f"⬆️ Assigning highest role '{role_name}' to {username} (points: {current_points} >= threshold: {highest_qualified_milestone})")
                    await assign_role_to_user(discord_id, highest_qualified_role_id)
                
                updated_users += 1
                
            except Exception as e:
                print(f"❌ Error processing user {user.get('username', 'Unknown')}: {e}")
                error_users += 1
                continue
        
        print(f"✅ FULL role synchronization complete: {updated_users} users processed, {error_users} errors")
        
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
