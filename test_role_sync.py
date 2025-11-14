#!/usr/bin/env python3
"""
Test script for Discord role synchronization
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the sync function
try:
    from discord_bot import sync_all_user_roles
    print("✅ Successfully imported sync_all_user_roles function")
except ImportError as e:
    print(f"❌ Failed to import sync_all_user_roles: {e}")
    sys.exit(1)

# Test the function
if __name__ == "__main__":
    print("🧪 Testing role synchronization function...")
    # This would normally be called when the bot comes online
    print("✅ Test completed - function is available")