#!/usr/bin/env python3
"""
Discord OAuth Setup Helper
This script helps you set up Discord OAuth for account linking
"""

import os
from dotenv import load_dotenv

def setup_discord_oauth():
    print("🔧 Discord OAuth Setup Helper")
    print("=" * 50)
    
    # Load current .env
    load_dotenv()
    
    bot_token = os.environ.get('DISCORD_BOT_TOKEN')
    if bot_token:
        # Extract application ID from bot token
        app_id = bot_token.split('.')[0]
        print(f"✅ Found Discord Application ID: {app_id}")
        print(f"   (This is your DISCORD_CLIENT_ID)")
    else:
        print("❌ No Discord bot token found")
        return
    
    print("\n📋 Steps to get your Discord OAuth credentials:")
    print("1. Go to: https://discord.com/developers/applications")
    print(f"2. Select your application (ID: {app_id})")
    print("3. Go to 'OAuth2' → 'General'")
    print("4. Copy the 'Client Secret'")
    print("5. Add these redirect URIs:")
    print("   - http://localhost:10000/auth/discord/callback")
    print("   - https://recenttablist.onrender.com/auth/discord/callback")
    
    print("\n🔑 Add this to your .env file:")
    print(f"DISCORD_CLIENT_ID={app_id}")
    print("DISCORD_CLIENT_SECRET=your_client_secret_here")
    
    print("\n⚠️  Important:")
    print("- Keep your Client Secret private!")
    print("- Don't share it in public repositories")
    print("- The Client ID can be public")
    
    # Try to update .env automatically
    try:
        with open('.env', 'r') as f:
            content = f.read()
        
        if 'DISCORD_CLIENT_ID=' not in content:
            with open('.env', 'a') as f:
                f.write(f"\nDISCORD_CLIENT_ID={app_id}\n")
            print(f"\n✅ Added DISCORD_CLIENT_ID={app_id} to .env file")
        else:
            # Update existing CLIENT_ID
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('DISCORD_CLIENT_ID='):
                    lines[i] = f'DISCORD_CLIENT_ID={app_id}'
                    break
            
            with open('.env', 'w') as f:
                f.write('\n'.join(lines))
            print(f"\n✅ Updated DISCORD_CLIENT_ID={app_id} in .env file")
        
        print("🔧 You still need to add your DISCORD_CLIENT_SECRET manually")
        
    except Exception as e:
        print(f"\n❌ Could not update .env file: {e}")
    
    print("\n🎯 After adding the Client Secret, restart your app and try linking Discord!")

if __name__ == "__main__":
    setup_discord_oauth()