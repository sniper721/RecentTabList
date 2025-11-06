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
        """Send a changelog message via webhook - ensures only one message is sent"""
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
        
        # Prevent empty messages
        if not message or not message.strip():
            print("❌ Cannot send empty changelog message")
            return False
        
        print(f"🔔 Sending changelog message: {message}")
        
        try:
            # Prepare payload - simple text message without formatting
            payload = {
                "content": message.strip(),
                "username": "Changelog Bot",
                # Avatar removed - using default Discord bot appearance
            }
            
            # Send via webhook - single request only
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"📡 Changelog Discord API response: {response.status_code}")
            
            if response.status_code in [200, 204]:
                print("✅ Changelog message sent successfully via webhook")
                return True
            else:
                print(f"❌ Failed to send changelog message: {response.status_code} - {response.text}")
                return False
                        
        except requests.exceptions.Timeout:
            print("❌ Webhook request timed out")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error sending changelog message: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error sending changelog message: {e}")
            import traceback
            traceback.print_exc()
            return False

# Global notifier instance
changelog_notifier = ChangelogDiscordNotifier()

def notify_changelog(message, admin_username=None):
    """Convenience function to send changelog notifications"""
    return changelog_notifier.send_changelog_message(message, admin_username)

def send_changelog_notification(action, level_name, admin_username=None, **kwargs):
    """Send changelog notification with enhanced formatting matching user requirements"""
    try:
        message = ""
        
        if action == "placed":
            position = kwargs.get('position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            list_type = kwargs.get('list_type', 'main')  # main, legacy, future
            
            # Enhanced message format: "X has been placed at #place above X2 and below X3. This pushes X4 to the legacy list"
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            message = f"{level_name} has been placed at #{position}"
            
            # Add positioning context
            if above_level and below_level:
                message += f" above {below_level} and below {above_level}"
            elif below_level:
                message += f" above {below_level}"
            elif above_level:
                message += f" below {above_level}"
            
            # Add list type suffix
            message += list_suffix + "."
            
            # Check if this placement pushed something to legacy
            pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
            if pushed_to_legacy:
                message += f" This pushes {pushed_to_legacy} to the legacy list."
            
            # Check if this placement pushed something out of top 10
            pushed_out_of_top10 = kwargs.get('pushed_out_of_top10', '')
            if pushed_out_of_top10 and position <= 10:
                message += f" This pushes {pushed_out_of_top10} out of the top 10."
        
        elif action == "moved":
            old_position = kwargs.get('old_position', '?')
            new_position = kwargs.get('new_position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            list_type = kwargs.get('list_type', 'main')
            
            # Enhanced message format for moves
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            message = f"{level_name} has been moved from #{old_position} to #{new_position}"
            
            # Add positioning context
            if above_level and below_level:
                message += f" above {below_level} and below {above_level}"
            elif below_level:
                message += f" above {below_level}"
            elif above_level:
                message += f" below {above_level}"
            
            # Add list type suffix
            message += list_suffix + "."
            
            # Check if this move pushed something to legacy
            pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
            if pushed_to_legacy:
                message += f" This pushes {pushed_to_legacy} to the legacy list."
            
            # Check if this move pushed something out of top 10
            pushed_out_of_top10 = kwargs.get('pushed_out_of_top10', '')
            if pushed_out_of_top10 and new_position <= 10:
                message += f" This pushes {pushed_out_of_top10} out of the top 10."
        
        elif action == "removed":
            old_position = kwargs.get('old_position', '?')
            reason = kwargs.get('reason', '')
            list_type = kwargs.get('list_type', 'main')
            
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            message = f"{level_name} has been removed"
            if old_position and old_position != '?':
                message += f" from #{old_position}"
            
            message += list_suffix
            
            if reason:
                message += f". Reason: {reason}"
            else:
                message += "."
        
        elif action == "legacy":
            old_position = kwargs.get('old_position', '?')
            legacy_position = kwargs.get('legacy_position', '?')
            
            message = f"{level_name} has been moved to the legacy list"
            if legacy_position and legacy_position != '?':
                message += f" at position #{legacy_position + 100}"  # Legacy starts from #101
            message += "."
        
        # Send message only via webhook to prevent duplicates
        if message:
            return notify_changelog(message, admin_username)
        
        return False
        
    except Exception as e:
        print(f"Error sending changelog notification: {e}")
        return False