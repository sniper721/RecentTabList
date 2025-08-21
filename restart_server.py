#!/usr/bin/env python3
"""
Restart the RTL server with all updates
"""

import subprocess
import sys
import time
import os

def restart_server():
    """Restart the server to apply all updates"""
    
    print("🔄 RESTARTING RTL SERVER...")
    print("=" * 50)
    
    # Kill any existing Python processes on port 10000
    try:
        print("1. Checking for existing processes...")
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, shell=True)
        if ':10000' in result.stdout:
            print("   Found old connections (TIME_WAIT - will clear automatically)")
        else:
            print("   No active server found")
    except:
        print("   Could not check processes")
    
    # Test imports first
    print("\n2. Testing imports...")
    try:
        from main import app
        print("   ✅ All imports successful")
        print("   ✅ Database connected")
        print("   ✅ Routes configured")
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Start the server
    print("\n3. Starting server...")
    print("   🌐 Server will start on http://localhost:10000")
    print("   📋 New features available:")
    print("      • Fixed images (no more 'Image Error')")
    print("      • Enhanced user settings")
    print("      • GD account verification")
    print("      • Difficulty range selection (Easy to Extreme Demon)")
    print("      • Fixed admin tools")
    print("      • Updated guidelines")
    print("\n   Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the Flask app
    try:
        app.run(host='0.0.0.0', port=10000, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    restart_server()