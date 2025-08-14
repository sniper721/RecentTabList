#!/usr/bin/env python3
"""
Discord integration for Flask app
Sends notifications without blocking the main app
"""

import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

class DiscordNotifier:
    """Discord notification handler using webhooks (non-blocking)"""
    
    def __init__(self):
        self.webhook_url = DISCORD_WEBHOOK_URL
        
    def send_webhook(self, embed_data):
        """Send webhook notification to Discord"""
        if not self.webhook_url:
            print("❌ No Discord webhook URL configured")
            return False
            
        print(f"🔔 Sending Discord webhook to: {self.webhook_url[:50]}...")
        print(f"📝 Embed title: {embed_data.get('title', 'No title')}")
            
        try:
            payload = {
                "embeds": [embed_data]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"📡 Discord API response: {response.status_code}")
            
            if response.status_code == 204:
                print("✅ Discord notification sent successfully")
                return True
            else:
                print(f"❌ Discord webhook failed with status {response.status_code}")
                print(f"Response text: {response.text}")
                return False
                        
        except Exception as e:
            print(f"❌ Error sending Discord webhook: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_record_notification(self, record_data):
        """Send notification for new record submission (non-blocking)"""
        embed = {
            "title": "📝 New Record Submission",
            "description": "A new record has been submitted for review",
            "color": 16766020,  # Yellow color (0xfbbf24)
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "👤 Player",
                    "value": record_data.get('username', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "🎮 Level",
                    "value": record_data.get('level_name', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "📊 Progress",
                    "value": f"{record_data.get('progress', 0)}%",
                    "inline": True
                }
            ],
            "footer": {
                "text": "RTL Admin Notification System"
            }
        }
        
        # Add video link if available
        if record_data.get('video_url'):
            embed["fields"].append({
                "name": "🎥 Video",
                "value": f"[Watch Video]({record_data['video_url']})",
                "inline": False
            })
        
        # Add admin panel link
        website_url = os.environ.get('WEBSITE_URL', 'http://localhost:10000')
        embed["fields"].append({
            "name": "⚙️ Admin Panel",
            "value": f"[Review Submission]({website_url}/admin)",
            "inline": False
        })
        
        # Send webhook directly (no async needed)
        try:
            self.send_webhook(embed)
        except Exception as e:
            print(f"❌ Error in Discord notification: {e}")
    
    def send_record_approved_notification(self, record_data):
        """Send notification for approved record (non-blocking)"""
        embed = {
            "title": "✅ Record Approved",
            "description": "A record has been approved and added to the leaderboard",
            "color": 1096065,  # Green color (0x10b981)
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "👤 Player",
                    "value": record_data.get('username', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "🎮 Level",
                    "value": record_data.get('level_name', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "📊 Progress",
                    "value": f"{record_data.get('progress', 0)}%",
                    "inline": True
                },
                {
                    "name": "🏆 Points Earned",
                    "value": f"{record_data.get('points_earned', 0)} pts",
                    "inline": True
                }
            ],
            "footer": {
                "text": "RTL Admin Notification System"
            }
        }
        
        # Send webhook directly (no async needed)
        try:
            self.send_webhook(embed)
        except Exception as e:
            print(f"❌ Error in Discord approval notification: {e}")
    
    def send_record_rejected_notification(self, record_data, reason=None):
        """Send notification for rejected record"""
        embed = {
            "title": "❌ Record Rejected",
            "description": "A record submission has been rejected",
            "color": 15548997,  # Red color (0xef4444)
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "👤 Player",
                    "value": record_data.get('username', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "🎮 Level",
                    "value": record_data.get('level_name', 'Unknown'),
                    "inline": True
                },
                {
                    "name": "📊 Progress",
                    "value": f"{record_data.get('progress', 0)}%",
                    "inline": True
                }
            ],
            "footer": {
                "text": "RTL Admin Notification System"
            }
        }
        
        if reason:
            embed["fields"].append({
                "name": "📝 Reason",
                "value": reason,
                "inline": False
            })
        
        # Send webhook directly (no async needed)
        try:
            self.send_webhook(embed)
        except Exception as e:
            print(f"❌ Error in Discord rejection notification: {e}")

# Global notifier instance
discord_notifier = DiscordNotifier()

def notify_record_submitted(username, level_name, progress, video_url):
    """Convenience function to notify about new record submission"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress,
        'video_url': video_url
    }
    
    # Run in background thread to avoid blocking Flask
    import threading
    thread = threading.Thread(
        target=discord_notifier.send_record_notification,
        args=(record_data,)
    )
    thread.daemon = True
    thread.start()

def notify_record_approved(username, level_name, progress, points_earned):
    """Convenience function to notify about approved record"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress,
        'points_earned': points_earned
    }
    
    # Run in background thread to avoid blocking Flask
    import threading
    thread = threading.Thread(
        target=discord_notifier.send_record_approved_notification,
        args=(record_data,)
    )
    thread.daemon = True
    thread.start()

def notify_record_rejected(username, level_name, progress, reason=None):
    """Convenience function to notify about rejected record"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress
    }
    
    # Run in background thread to avoid blocking Flask
    import threading
    thread = threading.Thread(
        target=discord_notifier.send_record_rejected_notification,
        args=(record_data, reason)
    )
    thread.daemon = True
    thread.start()