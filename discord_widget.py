#!/usr/bin/env python3
"""
Discord Widget Integration for RTL Website
Provides live Discord server information including online members and voice channels
"""

import requests
import os
from datetime import datetime, timedelta
import json

# Discord server ID
DISCORD_SERVER_ID = "1386176113448845322"
DISCORD_WIDGET_API = f"https://discord.com/api/guilds/{DISCORD_SERVER_ID}/widget.json"

# Cache for Discord data (to avoid rate limiting)
discord_cache = {
    'data': None,
    'last_updated': None,
    'cache_duration': 300  # 5 minutes
}

def get_discord_widget_data():
    """Get Discord server widget data with caching"""
    try:
        now = datetime.now()
        
        # Check if we have cached data that's still valid
        if (discord_cache['data'] is not None and 
            discord_cache['last_updated'] is not None and
            now - discord_cache['last_updated'] < timedelta(seconds=discord_cache['cache_duration'])):
            return discord_cache['data']
        
        # Fetch fresh data from Discord API
        response = requests.get(DISCORD_WIDGET_API, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Update cache
            discord_cache['data'] = data
            discord_cache['last_updated'] = now
            
            print(f"✅ Discord widget data updated: {len(data.get('members', []))} members online")
            return data
        elif response.status_code == 403:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            if error_data.get('code') == 50004:
                print(f"❌ Discord widget is disabled for server {DISCORD_SERVER_ID}")
                print("   To enable: Server Settings → Widget → Enable Server Widget")
            else:
                print(f"❌ Discord API access denied: {response.status_code}")
            return None
        else:
            print(f"❌ Discord API error: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                print(f"   Response: {response.json()}")
            return discord_cache['data']
            
    except requests.exceptions.Timeout:
        print("❌ Discord API timeout")
        return discord_cache['data']
    except requests.exceptions.RequestException as e:
        print(f"❌ Discord API request error: {e}")
        return discord_cache['data']
    except Exception as e:
        print(f"❌ Discord widget error: {e}")
        return discord_cache['data']

def format_discord_widget_data(data):
    """Format Discord widget data for template use"""
    if not data:
        return {
            'online': False,
            'name': 'RTL Discord Server',
            'member_count': 0,
            'online_count': 0,
            'channels': [],
            'members': [],
            'invite_url': 'https://discord.gg/TSjXSecuaz',
            'error': 'widget_disabled'
        }
    
    # Extract voice channels (exclude private channels)
    channels = []
    for channel in data.get('channels', []):
        if channel.get('name') and not channel.get('name', '').startswith('Private'):
            channels.append({
                'id': channel.get('id'),
                'name': channel.get('name'),
                'position': channel.get('position', 0)
            })
    
    # Sort channels by position
    channels.sort(key=lambda x: x['position'])
    
    # Extract online members
    members = []
    for member in data.get('members', []):
        # Skip bots and members without proper data
        if member.get('bot') or not member.get('username'):
            continue
            
        member_data = {
            'id': member.get('id'),
            'username': member.get('username'),
            'discriminator': member.get('discriminator', ''),
            'avatar': '',  # Avatar functionality removed
            'status': member.get('status', 'online'),
            'game': member.get('game', {}).get('name', '') if member.get('game') else '',
            'channel_id': member.get('channel_id'),
            'channel_name': ''
        }
        
        # Find channel name if member is in voice
        if member_data['channel_id']:
            for channel in channels:
                if channel['id'] == member_data['channel_id']:
                    member_data['channel_name'] = channel['name']
                    break
        
        members.append(member_data)
    
    # Sort members: voice channel members first, then by username
    members.sort(key=lambda x: (not bool(x['channel_id']), x['username'].lower()))
    
    return {
        'online': True,
        'name': data.get('name', 'RTL Discord Server'),
        'member_count': data.get('presence_count', 0),
        'online_count': len(members),
        'channels': channels,
        'members': members,
        'invite_url': data.get('instant_invite', 'https://discord.gg/TSjXSecuaz')
    }

def get_formatted_discord_data():
    """Get formatted Discord data for templates"""
    raw_data = get_discord_widget_data()
    return format_discord_widget_data(raw_data)

# Test function
if __name__ == "__main__":
    print("Testing Discord widget...")
    data = get_formatted_discord_data()
    print(f"Server: {data['name']}")
    print(f"Online: {data['online_count']}/{data['member_count']} members")
    print(f"Channels: {len(data['channels'])}")
    print(f"Voice channels: {[c['name'] for c in data['channels']]}")
    print(f"Sample members: {[m['username'] for m in data['members'][:5]]}")