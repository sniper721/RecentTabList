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
            "color": 10181046,  # Purple color (0x9b59b6)
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
        
        # Add comments if available
        if record_data.get('comments') and record_data['comments'].strip():
            embed["fields"].append({
                "name": "💬 Comments",
                "value": record_data['comments'][:500] + ("..." if len(record_data['comments']) > 500 else ""),
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
    
    def send_admin_action_notification(self, admin_username, action, details=""):
        """Send notification for admin actions"""
        # Determine color based on action type
        color = 3447003  # Default blue
        
        # RED - Dangerous/Critical actions
        if ("DELETE" in action.upper() or "BAN" in action.upper() or 
            "LOGIN AS USER" in action.upper() or "ADMIN LOGIN AS" in action.upper() or
            "RESET POINTS" in action.upper() or "DEMOTE" in action.upper() or
            "REMOVE HEAD ADMIN" in action.upper() or "IP BAN" in action.upper() or
            "RTL DANGEROUS COMMAND" in action.upper() or "DANGEROUS" in action.upper() or
            "UNBAN" in action.upper()):
            color = 15548997  # Red
        # GREEN - Positive actions
        elif ("APPROVE" in action.upper() or "ADD" in action.upper() or 
              "PROMOTE" in action.upper() or "MAKE HEAD ADMIN" in action.upper()):
            color = 1096065  # Green
        # YELLOW/ORANGE - Console actions
        elif ("CONSOLE" in action.upper() or "COMMAND" in action.upper() or 
              "RTL COMMAND" in action.upper()):
            color = 16766020  # Yellow/Orange
        
        embed = {
            "title": "🔧 Admin Action",
            "description": f"Admin activity detected",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "👤 Admin",
                    "value": admin_username,
                    "inline": True
                },
                {
                    "name": "⚡ Action",
                    "value": action,
                    "inline": True
                }
            ],
            "footer": {
                "text": "RTL Admin Tracking System"
            }
        }
        
        # Add details if provided
        if details:
            embed["fields"].append({
                "name": "📝 Details",
                "value": details[:1000],  # Limit to 1000 chars
                "inline": False
            })
        
        # Add admin panel link
        website_url = os.environ.get('WEBSITE_URL', 'http://localhost:10000')
        embed["fields"].append({
            "name": "⚙️ Admin Panel",
            "value": f"[View Admin Panel]({website_url}/admin)",
            "inline": False
        })
        
        # Send webhook directly
        try:
            self.send_webhook(embed)
        except Exception as e:
            print(f"❌ Error in Discord admin action notification: {e}")

# Global notifier instance
discord_notifier = DiscordNotifier()

def notify_record_submitted(username, level_name, progress, video_url, comments=None):
    """Convenience function to notify about new record submission"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress,
        'video_url': video_url,
        'comments': comments
    }
    
    print(f"🔔 notify_record_submitted called for {username}")
    
    # Send directly instead of using threads (more reliable)
    try:
        discord_notifier.send_record_notification(record_data)
    except Exception as e:
        print(f"❌ Error in notify_record_submitted: {e}")
        import traceback
        traceback.print_exc()

def notify_record_approved(username, level_name, progress, points_earned):
    """Convenience function to notify about approved record"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress,
        'points_earned': points_earned
    }
    
    print(f"🔔 notify_record_approved called for {username}")
    
    # Send directly instead of using threads (more reliable)
    try:
        discord_notifier.send_record_approved_notification(record_data)
    except Exception as e:
        print(f"❌ Error in notify_record_approved: {e}")
        import traceback
        traceback.print_exc()

def notify_record_rejected(username, level_name, progress, reason=None):
    """Convenience function to notify about rejected record"""
    record_data = {
        'username': username,
        'level_name': level_name,
        'progress': progress
    }
    
    print(f"🔔 notify_record_rejected called for {username}")
    
    # Send directly instead of using threads (more reliable)
    try:
        discord_notifier.send_record_rejected_notification(record_data, reason)
    except Exception as e:
        print(f"❌ Error in notify_record_rejected: {e}")
        import traceback
        traceback.print_exc()

def notify_admin_action(admin_username, action, details=""):
    """Convenience function to notify about admin actions"""
    print(f"🔔 notify_admin_action called: {admin_username} - {action}")
    
    # Send directly instead of using threads (more reliable)
    try:
        discord_notifier.send_admin_action_notification(admin_username, action, details)
    except Exception as e:
        print(f"❌ Error in notify_admin_action: {e}")
        import traceback
        traceback.print_exc()