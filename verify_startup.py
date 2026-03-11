"""
RTL Startup Verification
Run this AFTER starting your Flask app to verify it's working
"""

import requests
import time

print("=" * 70)
print("RTL STARTUP VERIFICATION")
print("=" * 70)
print()
print("Make sure your Flask app is running first!")
print("Then this script will verify the main list is loading correctly.")
print()
input("Press ENTER when your Flask app is running...")

print("\nTesting main list endpoint...")
print()

try:
    # Test the main page
    response = requests.get('http://localhost:5000/', timeout=10)
    
    if response.status_code == 200:
        print("[OK] Main page loads successfully!")
        
        # Check if levels are in the response
        if 'Ocean of stars' in response.text:
            print("[OK] Levels are being displayed!")
            print("[OK] Found 'Ocean of stars' (level #1)")
        else:
            print("[ERROR] Levels not found in page!")
            print("       The page loads but no levels are showing")
        
        # Count level cards
        level_count = response.text.count('level-card')
        print(f"[INFO] Found {level_count} level cards in HTML")
        
        if level_count >= 90:
            print("[OK] All 100 levels are loading!")
        elif level_count > 0:
            print(f"[WARNING] Only {level_count} levels found (expected 100)")
        else:
            print("[ERROR] No level cards found!")
        
    else:
        print(f"[ERROR] Page returned status code: {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("[ERROR] Could not connect to Flask app!")
    print("       Make sure it's running on http://localhost:5000")
except Exception as e:
    print(f"[ERROR] {e}")

print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print()
print("If you see errors:")
print("1. Make sure Flask app is running: python main.py")
print("2. Check the Flask console for error messages")
print("3. Try restarting the Flask app")
print()
