#!/usr/bin/env python3
"""
Script to check Render environment variables
"""

import os

def check_env_vars():
    print("🔍 Checking Render environment variables...")
    
    # Check if we're running on Render
    render_env = os.environ.get('RENDER', 'Not set')
    print(f"RENDER environment: {render_env}")
    
    # Check changelog webhook variables
    webhook_enabled = os.environ.get('CHANGELOG_WEBHOOK_ENABLED', 'Not set')
    webhook_url = os.environ.get('CHANGELOG_WEBHOOK_URL', 'Not set')
    
    print(f"CHANGELOG_WEBHOOK_ENABLED: {webhook_enabled}")
    print(f"CHANGELOG_WEBHOOK_URL: {webhook_url}")
    
    # Check if they're properly set
    if webhook_enabled.lower() == 'true':
        print("✅ CHANGELOG_WEBHOOK_ENABLED is correctly set to 'true'")
    else:
        print(f"❌ CHANGELOG_WEBHOOK_ENABLED is not set correctly. Current value: '{webhook_enabled}'")
        
    if webhook_url != 'Not set' and webhook_url.startswith('https://discord.com/api/webhooks/'):
        print("✅ CHANGELOG_WEBHOOK_URL is set with a valid Discord webhook URL")
    elif webhook_url == 'Not set':
        print("❌ CHANGELOG_WEBHOOK_URL is not set")
    else:
        print(f"⚠️  CHANGELOG_WEBHOOK_URL might not be a valid Discord webhook URL. Current value: {webhook_url}")

if __name__ == "__main__":
    check_env_vars()