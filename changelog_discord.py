#!/usr/bin/env python3
"""
Changelog Discord integration for Flask app
Sends changelog notifications to a separate Discord webhook
"""

import requests
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Changelog webhook URL from environment variable
CHANGELOG_WEBHOOK_URL = os.environ.get('CHANGELOG_WEBHOOK_URL')

# Global database reference (will be set by main.py)
mongo_db = None

def set_mongo_db(db):
    """Set the MongoDB reference for the changelog notifier"""
    global mongo_db
    mongo_db = db

class ChangelogDiscordNotifier:
    """Discord notification handler for changelog updates using webhooks only"""
    
    def __init__(self):
        self.webhook_url = CHANGELOG_WEBHOOK_URL
    
    def send_changelog_message(self, message, admin_username=None):
        """Send a changelog message via webhook"""
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
        
        if not self.webhook_url:
            print("❌ No changelog webhook URL configured")
            return False
        
        print(f"🔔 Sending changelog message: {message}")
        
        try:
            # Prepare payload - simple text message like demon list changelogs
            payload = {
                "content": message,
                "username": "Changelog Bot",
                "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
            }
            
            # Send via webhook
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"📡 Changelog Discord API response: {response.status_code}")
            
            if response.status_code == 204:
                print("✅ Changelog message sent successfully via webhook")
                return True
            else:
                print(f"❌ Failed to send changelog message: {response.status_code} - {response.text}")
                return False
                        
        except Exception as e:
            print(f"❌ Error sending changelog message: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global notifier instance
changelog_notifier = ChangelogDiscordNotifier()

def notify_changelog(message, admin_username=None):
    """Convenience function to send changelog notifications"""
    return changelog_notifier.send_changelog_message(message, admin_username)

def send_changelog_notification(action, level_name, admin_username=None, **kwargs):
    """Send changelog notification with enhanced formatting"""
    try:
        message = ""
        
        if action == "placed":
            position = kwargs.get('position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            
            if position == 1:
                # Special case for #1 placement
                dethroned_level = kwargs.get('dethroned_level', '')
                pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
                
                message = f"**{level_name}** has been placed at **#1**"
                if dethroned_level:
                    message += f" dethroning **{dethroned_level}**"
                message += "."
                
                if pushed_to_legacy:
                    message += f" This pushes **{pushed_to_legacy}** to the legacy list."
            else:
                # Regular placement
                message = f"**{level_name}** has been placed at **#{position}**"
                if below_level and above_level:
                    message += f" below **{above_level}** and above **{below_level}**"
                elif below_level:
                    message += f" above **{below_level}**"
                elif above_level:
                    message += f" below **{above_level}**"
                message += "."
                
                # Check if this placement pushed something to legacy
                pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
                if pushed_to_legacy:
                    message += f" This pushes **{pushed_to_legacy}** to the legacy list."
        
        elif action == "moved":
            old_position = kwargs.get('old_position', '?')
            new_position = kwargs.get('new_position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            
            message = f"**{level_name}** has been moved from **#{old_position}** to **#{new_position}**"
            if below_level and above_level:
                message += f" below **{above_level}** and above **{below_level}**"
            elif below_level:
                message += f" above **{below_level}**"
            elif above_level:
                message += f" below **{above_level}**"
            message += "."
            
            # Check if this move pushed something to legacy
            pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
            if pushed_to_legacy:
                message += f" This pushes **{pushed_to_legacy}** to the legacy list."
        
        elif action == "removed":
            old_position = kwargs.get('old_position', '?')
            reason = kwargs.get('reason', '')
            
            message = f"**{level_name}** has been removed"
            if old_position and old_position != '?':
                message += f" from **#{old_position}**"
            
            if reason:
                message += f". Reason: {reason}"
            else:
                message += "."
        
        elif action == "legacy":
            old_position = kwargs.get('old_position', '?')
            legacy_position = kwargs.get('legacy_position', '?')
            
            message = f"**{level_name}** has been moved to the legacy list"
            if legacy_position and legacy_position != '?':
                message += f" at position **#{legacy_position + 100}**"  # Legacy starts from #101
            message += "."
        
        # Send the notification
        if message:
            return notify_changelog(message, admin_username)
        
        return False
        
    except Exception as e:
        print(f"Error sending changelog notification: {e}")
        return False