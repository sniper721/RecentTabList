import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Checking Google OAuth configuration...")
print(f"GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID', 'NOT SET')}")
print(f"GOOGLE_CLIENT_SECRET: {'SET' if os.environ.get('GOOGLE_CLIENT_SECRET') else 'NOT SET'}")

# Test the OpenID configuration URL
import requests
try:
    response = requests.get('https://accounts.google.com/.well-known/openid_configuration')
    print(f"OpenID config URL status: {response.status_code}")
    if response.status_code == 200:
        print("✓ Google OpenID configuration is accessible")
    else:
        print("✗ Google OpenID configuration is not accessible")
except Exception as e:
    print(f"✗ Error accessing OpenID config: {e}")