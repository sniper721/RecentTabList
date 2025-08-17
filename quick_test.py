import requests
import time

print("Testing local server connection...")

try:
    # Test if the server is responding
    response = requests.get('http://localhost:10000/', timeout=10)
    print(f"✅ Server responded with status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        if 'level-card' in content:
            level_count = content.count('level-card')
            print(f"✅ Found {level_count} levels on the page")
        else:
            print("❌ No levels found on the page")
            print("First 500 chars of response:")
            print(content[:500])
    else:
        print(f"❌ Server error: {response.status_code}")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("❌ Request timed out - server is taking too long to respond")
except requests.exceptions.ConnectionError:
    print("❌ Connection error - server might not be running")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nTesting legacy route...")
try:
    response = requests.get('http://localhost:10000/legacy', timeout=10)
    print(f"Legacy route status: {response.status_code}")
except Exception as e:
    print(f"Legacy route error: {e}")