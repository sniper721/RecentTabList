#!/usr/bin/env python3
"""
Discord bot for RTL (Recent Tab List) notifications
Sends alerts to admin channel when records are submitted
"""

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import aiohttp
from datetime import datetime

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
ADMIN_CHANNEL_ID = int(os.environ.get('DISCORD_ADMIN_CHANNEL_ID', '0'))
GUILD_ID = int(os.environ.get('DISCORD_GUILD_ID', '0'))

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!rtl ', intents=intents)

@bot.event
async def on_ready():
    """Bot startup event"""
    print(f'✅ RTL Discord Bot logged in as {bot.user}')
    print(f'📊 Connected to {len(bot.guilds)} servers')
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.watching, name="RTL submissions")
    await bot.change_presence(activity=activity)

@bot.command(name='ping')
async def ping(ctx):
    """Test command to check if bot is responsive"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: {latency}ms",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command(name='status')
async def status(ctx):
    """Show bot status and statistics"""
    embed = discord.Embed(
        title="🤖 RTL Bot Status",
        color=0x3b82f6
    )
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.timestamp = datetime.utcnow()
    
    await ctx.send(embed=embed)

async def send_record_notification(record_data):
    """Send notification when a new record is submitted"""
    if not ADMIN_CHANNEL_ID:
        print("❌ No admin channel ID configured")
        return
    
    try:
        channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if not channel:
            print(f"❌ Could not find channel with ID {ADMIN_CHANNEL_ID}")
            return
        
        # Create embed for the notification
        embed = discord.Embed(
            title="📝 New Record Submission",
            description="A new record has been submitted for review",
            color=0xfbbf24,  # Yellow/warning color
            timestamp=datetime.utcnow()
        )
        
        # Add record details
        embed.add_field(
            name="👤 Player", 
            value=record_data.get('username', 'Unknown'), 
            inline=True
        )
        embed.add_field(
            name="🎮 Level", 
            value=record_data.get('level_name', 'Unknown'), 
            inline=True
        )
        embed.add_field(
            name="📊 Progress", 
            value=f"{record_data.get('progress', 0)}%", 
            inline=True
        )
        
        if record_data.get('video_url'):
            embed.add_field(
                name="🎥 Video", 
                value=f"[Watch Video]({record_data['video_url']})", 
                inline=False
            )
        
        # Add admin panel link
        website_url = os.environ.get('WEBSITE_URL', 'http://localhost:10000')
        embed.add_field(
            name="⚙️ Admin Panel", 
            value=f"[Review Submission]({website_url}/admin)", 
            inline=False
        )
        
        # Add footer
        embed.set_footer(text="RTL Admin Notification System")
        
        # Send the notification
        await channel.send(embed=embed)
        print(f"✅ Sent Discord notification for record by {record_data.get('username')}")
        
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")

async def send_record_approved_notification(record_data):
    """Send notification when a record is approved"""
    if not ADMIN_CHANNEL_ID:
        return
    
    try:
        channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="✅ Record Approved",
            description="A record has been approved and added to the leaderboard",
            color=0x10b981,  # Green color
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="👤 Player", 
            value=record_data.get('username', 'Unknown'), 
            inline=True
        )
        embed.add_field(
            name="🎮 Level", 
            value=record_data.get('level_name', 'Unknown'), 
            inline=True
        )
        embed.add_field(
            name="📊 Progress", 
            value=f"{record_data.get('progress', 0)}%", 
            inline=True
        )
        embed.add_field(
            name="🏆 Points Earned", 
            value=f"{record_data.get('points_earned', 0)} pts", 
            inline=True
        )
        
        embed.set_footer(text="RTL Admin Notification System")
        
        await channel.send(embed=embed)
        print(f"✅ Sent approval notification for {record_data.get('username')}")
        
    except Exception as e:
        print(f"❌ Error sending approval notification: {e}")

# Global variable to store the bot instance for external access
_bot_instance = None

def get_bot():
    """Get the bot instance"""
    return _bot_instance

async def start_bot():
    """Start the Discord bot"""
    global _bot_instance
    _bot_instance = bot
    
    if not DISCORD_TOKEN:
        print("❌ No Discord bot token found. Please set DISCORD_BOT_TOKEN in .env")
        return
    
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error starting Discord bot: {e}")

def run_bot():
    """Run the Discord bot (blocking)"""
    if not DISCORD_TOKEN:
        print("❌ No Discord bot token found. Please set DISCORD_BOT_TOKEN in .env")
        return
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error running Discord bot: {e}")

if __name__ == "__main__":
    run_bot()