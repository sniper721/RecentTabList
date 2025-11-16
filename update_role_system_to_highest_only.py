#!/usr/bin/env python3
"""
Update Role System to Highest Only
This script updates all users to have only their highest milestone role,
removing all lower milestone roles they currently have.
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timezone

# Load environment variables
load_dotenv()

# MongoDB setup
MONGODB_URI = os.environ.get('MONGODB_URI')
if not MONGODB_URI:
    print("❌ MONGODB_URI not found in environment variables")
    sys.exit(1)

try:
    mongo_client = MongoClient(MONGODB_URI)
    mongo_db = mongo_client.rtl_database
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    sys.exit(1)

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
DISCORD_GUILD_ID = 1386176113448845322

if not DISCORD_BOT_TOKEN:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    sys.exit(1)

# Points milestone roles mapping (sorted by points descending)
POINTS_ROLES = [
    (4000, "1434566288256012393"),   # 4000+ points
    (3500, "1434564972083413123"),   # 3500+ points
    (3000, "1434564672949977219"),   # 3000+ points
    (2500, "1434564465084596325"),   # 2500+ points
    (2000, "1434564153032315120"),   # 2000+ points
    (1500, "1434563863126474782"),   # 1500+ points
    (1000, "1434563588349100135"),   # 1000+ points
    (900, "1434563355917680722"),    # 900+ points
    (800, "1434563139302854796"),    # 800+ points
    (700, "1434562844678029322"),    # 700+ points
    (600, "1434562564607447072"),    # 600+ points
    (500, "1434560792845353073"),    # 500+ points
    (450, "1434560559315030279"),    # 450+ points
    (400, "1434560335540654170"),    # 400+ points
    (350, "1434560160193450056"),    # 350+ points
    (300, "1434559950142832812"),    # 300+ points
    (250, "1434559736430334013"),    # 250+ points
    (200, "1434559491164078210"),    # 200+ points
    (150, "1434559357978284072"),    # 150+ points
    (100, "1434559158056910859"),    # 100+ points
    (50, "1434561864477708412"),     # 50+ points
    (1, "1407154476900548638"),      # 1+ points
]

# Role names for logging
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
    "1434566288256012393": "4000+ Points"
}

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class RoleUpdateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def on_ready(self):
        print(f'✅ Discord bot logged in as {self.user}')
        
        # Get guild
        guild = self.get_guild(DISCORD_GUILD_ID)
        if not guild:
            print(f'❌ Could not find guild with ID: {DISCORD_GUILD_ID}')
            return
        
        print(f'✅ Connected to guild: {guild.name}')
        
        # Start role update process
        await self.update_all_user_roles(guild)
        
        # Close the bot after completion
        await self.close()
    
    async def update_all_user_roles(self, guild):
        """Update all users to have only their highest milestone role"""
        try:
            # Get all users with Discord connections
            users_with_discord = list(mongo_db.users.find({"discord_id": {"$exists": True, "$ne": None}}))
            print(f"🔍 Found {len(users_with_discord)} users with Discord connections")
            
            updated_users = 0
            error_users = 0
            
            for user in users_with_discord:
                try:
                    discord_id = user.get('discord_id')
                    username = user.get('username', 'Unknown')
                    current_points = user.get('points', 0)
                    
                    print(f"\n🔄 Processing user: {username} (ID: {discord_id}, Points: {current_points})")
                    
                    # Get Discord member
                    try:
                        member = guild.get_member(int(discord_id))
                        if not member:
                            member = await guild.fetch_member(int(discord_id))
                        if not member:
                            print(f"⚠️ Could not find Discord member for user {username}")
                            continue
                    except:
                        print(f"⚠️ Could not find Discord member for user {username}")
                        continue
                    
                    # Get current milestone roles the user has
                    user_milestone_roles = []
                    for role in member.roles:
                        role_id_str = str(role.id)
                        for points, milestone_role_id in POINTS_ROLES:
                            if role_id_str == milestone_role_id:
                                user_milestone_roles.append((points, milestone_role_id, role))
                                break
                    
                    print(f"📋 User currently has {len(user_milestone_roles)} milestone roles")
                    
                    # Find the highest milestone the user qualifies for
                    highest_qualified_milestone = 0
                    highest_qualified_role_id = None
                    for points_threshold, role_id in POINTS_ROLES:
                        if current_points >= points_threshold:
                            highest_qualified_milestone = points_threshold
                            highest_qualified_role_id = role_id
                            break
                    
                    if highest_qualified_milestone == 0:
                        print(f"⚠️ User {username} doesn't qualify for any milestone roles")
                        # Remove all milestone roles if they have any
                        for points, role_id, role in user_milestone_roles:
                            role_name = ROLE_NAMES.get(role_id, f"{points}+ Points")
                            print(f"⬇️ Removing role '{role_name}' from {username}")
                            await member.remove_roles(role, reason="RTL Role System Update - No longer qualifies")
                        continue
                    
                    print(f"🎯 User {username} qualifies for highest role: {ROLE_NAMES.get(highest_qualified_role_id, f'{highest_qualified_milestone}+ Points')}")
                    
                    # Remove ALL milestone roles first
                    for points, role_id, role in user_milestone_roles:
                        role_name = ROLE_NAMES.get(role_id, f"{points}+ Points")
                        print(f"⬇️ Removing role '{role_name}' from {username}")
                        await member.remove_roles(role, reason="RTL Role System Update - Cleanup")
                    
                    # Add only the highest qualified role
                    highest_role = guild.get_role(int(highest_qualified_role_id))
                    if highest_role:
                        role_name = ROLE_NAMES.get(highest_qualified_role_id, f"{highest_qualified_milestone}+ Points")
                        print(f"⬆️ Assigning highest role '{role_name}' to {username}")
                        await member.add_roles(highest_role, reason="RTL Role System Update - Highest role only")
                    else:
                        print(f"❌ Could not find role with ID {highest_qualified_role_id}")
                    
                    updated_users += 1
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"❌ Error processing user {user.get('username', 'Unknown')}: {e}")
                    error_users += 1
                    continue
            
            print(f"\n✅ Role update complete: {updated_users} users processed, {error_users} errors")
            
            # Update the last sync timestamp
            try:
                mongo_db.site_settings.update_one(
                    {"_id": "discord_bot"},
                    {"$set": {"last_role_sync": datetime.now(timezone.utc)}},
                    upsert=True
                )
                print("✅ Updated last role sync timestamp")
            except Exception as e:
                print(f"⚠️ Could not update last sync timestamp: {e}")
            
        except Exception as e:
            print(f"❌ Error in update_all_user_roles: {e}")
            import traceback
            traceback.print_exc()

# Run the bot
if __name__ == "__main__":
    print("🚀 Starting role system update...")
    print("📋 This will update all users to have only their highest milestone role")
    
    bot = RoleUpdateBot()
    bot.run(DISCORD_BOT_TOKEN)