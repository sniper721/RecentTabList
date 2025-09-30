#!/usr/bin/env python3
"""
Show all possible Discord OAuth redirect URIs that need to be added
"""

import os
from dotenv import load_dotenv

load_dotenv()

def show_redirect_uris():
    print("🔧 Discord OAuth Redirect URI Setup")
    print("=" * 50)
    
    website_url = os.environ.get('WEBSITE_URL', '').rstrip('/')
    port = os.environ.get('PORT', '10000')
    
    print("📋 Add ALL of these redirect URIs to your Discord application:")
    print("   https://discord.com/developers/applications/1421837492524683374/oauth2/general")
    print()
    
    redirect_uris = [
        # Local development
        f"http://localhost:{port}/auth/discord/callback",
        f"https://localhost:{port}/auth/discord/callback",
        f"http://127.0.0.1:{port}/auth/discord/callback",
        f"https://127.0.0.1:{port}/auth/discord/callback",
    ]
    
    # Production
    if website_url:
        redirect_uris.extend([
            f"{website_url}/auth/discord/callback",
            # Also add HTTP version just in case
            f"{website_url.replace('https://', 'http://')}/auth/discord/callback"
        ])
    
    for i, uri in enumerate(redirect_uris, 1):
        print(f"{i}. {uri}")
    
    print()
    print("🎯 Instructions:")
    print("1. Go to the Discord Developer Portal link above")
    print("2. Scroll down to 'Redirects' section")
    print("3. Add each URI listed above")
    print("4. Click 'Save Changes'")
    print("5. Try connecting Discord again!")
    
    print()
    print("💡 Pro tip: Copy and paste each URI exactly as shown above")

if __name__ == "__main__":
    show_redirect_uris()