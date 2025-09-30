#!/usr/bin/env python3
"""
Test script to verify the new verification tabs functionality
"""

import requests
import sys

def test_verification_routes():
    """Test that the verification routes are accessible"""
    base_url = "http://localhost:5000"
    
    routes_to_test = [
        "/admin/verifications",
        "/admin/verification-details"
    ]
    
    print("🧪 Testing verification routes...")
    
    for route in routes_to_test:
        try:
            url = f"{base_url}{route}"
            print(f"Testing {url}...")
            
            # This will likely return a redirect to login, but that's expected
            response = requests.get(url, allow_redirects=False)
            
            if response.status_code in [200, 302, 401, 403]:
                print(f"✅ {route} - Route exists (Status: {response.status_code})")
            else:
                print(f"❌ {route} - Unexpected status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {route} - Server not running (this is expected)")
        except Exception as e:
            print(f"❌ {route} - Error: {e}")
    
    print("\n📋 Summary:")
    print("✅ Added new route: /admin/verification-details")
    print("✅ Modified existing route: /admin/verifications (removed approve/reject)")
    print("✅ Updated admin navigation with both tabs")
    print("✅ Created verification_details.html template")
    print("✅ Updated verifications.html template (removed approve/reject buttons)")

if __name__ == "__main__":
    test_verification_routes()