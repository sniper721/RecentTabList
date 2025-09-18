#!/usr/bin/env python3
"""
Changelog Discord integration for Flask app
Sends changelog notifications to a separate Discord webhook
"""

import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import discord
import asyncio
import threading
import time

# Load environment variables
load_dotenv()

# Changelog webhook URL from environment variable or default
CHANGELOG_WEBHOOK_URL = os.environ.get('CHANGELOG_WEBHOOK_URL', "https://discord.com/api/webhooks/1412683830539714632/KiH21Ciq1Qpz6im9ZxZ5VC2MXcfjVI18hHwLtY5ooDvygnJ3au9ofXHUzODHewqv9QVw")

# Discord Bot configuration for message deletion
CHANGELOG_BOT_TOKEN = os.environ.get('CHANGELOG_BOT_TOKEN')
CHANGELOG_CHANNEL_ID = int(os.environ.get('CHANGELOG_CHANNEL_ID', '0'))

# Store message IDs for deletion
sent_messages = []

# Global database reference (will be set by main.py)
mongo_db = None


def set_mongo_db(db):
    """Set the MongoDB reference for the changelog notifier"""
    global mongo_db
    mongo_db = db

class ChangelogDiscordNotifier:
    """Discord notification handler for changelog updates"""
    
    def __init__(self):
        self.webhook_url = CHANGELOG_WEBHOOK_URL
        self.bot_token = CHANGELOG_BOT_TOKEN
        self.channel_id = CHANGELOG_CHANNEL_ID
        self.bot = None
        self.loop = None
        self.bot_thread = None
        self.message_storage = {}  # Store message IDs with timestamps
    
    def start_bot(self):
        """Start the Discord bot in a separate thread for message deletion"""
        if self.bot_token and self.channel_id and not self.bot_thread:
            try:
                self.bot = discord.Client(intents=discord.Intents.default())
                self.loop = asyncio.new_event_loop()
                
                @self.bot.event
                async def on_ready():
                    print(f'✅ Changelog Discord Bot logged in as {self.bot.user}')
                
                self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
                self.bot_thread.start()
                print("✅ Changelog Discord Bot thread started")
            except Exception as e:
                print(f"❌ Error starting Discord bot: {e}")
    
    def _run_bot(self):
        """Run the Discord bot in its own event loop"""
        try:
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.bot.start(self.bot_token))
        except Exception as e:
            print(f"❌ Error in Discord bot loop: {e}")
    
    def stop_bot(self):
        """Stop the Discord bot"""
        if self.bot and self.loop:
            try:
                asyncio.run_coroutine_threadsafe(self.bot.close(), self.loop)
                print("🛑 Changelog Discord Bot stopped")
            except Exception as e:
                print(f"❌ Error stopping Discord bot: {e}")
    
    def send_changelog_message(self, message, admin_username=None):
        """Send a changelog message via webhook and store for potential deletion"""
        # Check if webhook is enabled (first check environment variable, then database)
        webhook_enabled_env = os.environ.get('CHANGELOG_WEBHOOK_ENABLED', 'false').lower() == 'true'
        
        # If environment variable is not set, check database settings
        webhook_enabled_db = False
        if mongo_db is not None:
            try:
                changelog_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
                if changelog_settings:
                    webhook_enabled_db = changelog_settings.get("webhook_enabled", False)
            except Exception as e:
                print(f"Error checking database for webhook settings: {e}")
        
        # Webhook is enabled if either environment variable or database setting is True
        webhook_enabled = webhook_enabled_env or webhook_enabled_db
        
        if not webhook_enabled:
            print("🚨 Changelog Discord notifications are DISABLED")
            return False
        
        print(f"🔔 Sending changelog message: {message}")
        
        try:
            # Prepare payload
            payload = {
                "content": message,
                "username": "Changelog Bot",
                "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
            }
            
            # Send via webhook
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                print("✅ Changelog message sent successfully via webhook")
                # Store message timestamp for cleanup
                self.message_storage[str(time.time())] = time.time()
                return True
            else:
                print(f"❌ Failed to send changelog message: {response.status_code} - {response.text}")
                return False
                        
        except Exception as e:
            print(f"❌ Error sending changelog message: {e}")
            return False
    
    async def _delete_message_async(self, message_id):
        """Asynchronously delete a message (internal method)"""
        if not self.bot or not self.bot.is_ready():
            print("❌ Discord bot not ready for message deletion")
            return False
        
        try:
            channel = self.bot.get_channel(self.channel_id)
            if not channel:
                print(f"❌ Could not find channel {self.channel_id}")
                return False
            
            message = await channel.fetch_message(int(message_id))
            await message.delete()
            print(f"✅ Deleted message {message_id}")
            return True
        except discord.NotFound:
            print(f"❌ Message {message_id} not found")
            return False
        except Exception as e:
            print(f"❌ Error deleting message {message_id}: {e}")
            return False
    
    def delete_message(self, message_id):
        """Delete a specific message using the bot"""
        if not self.bot_token or not self.channel_id:
            print("❌ Discord bot not configured for message deletion")
            return False
        
        # Start bot if not already running
        if not self.bot_thread:
            self.start_bot()
        
        try:
            # Run the deletion in the bot's event loop
            if self.loop and self.bot:
                future = asyncio.run_coroutine_threadsafe(
                    self._delete_message_async(message_id), 
                    self.loop
                )
                result = future.result(timeout=10)  # Wait up to 10 seconds
                return result
            else:
                print("❌ Discord bot not properly initialized")
                return False
        except Exception as e:
            print(f"❌ Error during message deletion: {e}")
            return False
    
    def delete_all_messages(self):
        """Delete all stored messages (clear storage)"""
        try:
            # For webhook messages, we can't actually delete them
            # but we can clear our storage and reset the counter
            self.message_storage.clear()
            print("✅ Cleared message storage")
            return True
        except Exception as e:
            print(f"❌ Error clearing message storage: {e}")
            return False

# Global notifier instance
changelog_notifier = ChangelogDiscordNotifier()

def notify_changelog(message, admin_username=None):
    """Convenience function to send changelog notifications"""
    # Send message without custom message functionality
    return changelog_notifier.send_changelog_message(message, admin_username)

def delete_changelog_message(message_id):
    """Convenience function to delete a specific changelog message"""
    return changelog_notifier.delete_message(message_id)

def delete_all_changelog_messages():
    """Convenience function to delete all changelog messages"""
    return changelog_notifier.delete_all_messages()

# Start the bot when the module is imported
changelog_notifier.start_bot()