#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    
    print("Flask app loaded successfully!")
    print("\nChecking recent_tab_roulette route specifically:")
    
    # Check specifically for recent_tab_roulette
    found = False
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'recent_tab_roulette':
            print(f"  Found route: {rule.endpoint} -> {rule.rule} {list(rule.methods)}")
            found = True
            break
    
    if found:
        print("\n[OK] recent_tab_roulette route is registered!")
    else:
        print("\n[ERROR] recent_tab_roulette route is NOT registered!")
        
    # Test if we can build the URL
    with app.test_request_context():
        try:
            from flask import url_for
            url = url_for('recent_tab_roulette')
            print(f"\n[OK] URL generation works: {url}")
        except Exception as e:
            print(f"\n[ERROR] URL generation failed: {e}")
            import traceback
            traceback.print_exc()
            
    # Test if we can access the route
    with app.test_client() as client:
        try:
            response = client.get('/recent_tab_roulette')
            print(f"\n[TEST] Route access test: {response.status_code}")
            if response.status_code == 200:
                print("[OK] Route is accessible")
            elif response.status_code == 404:
                print("[ERROR] Route returns 404 - not found")
            else:
                print(f"[INFO] Route returns {response.status_code}")
        except Exception as e:
            print(f"\n[ERROR] Route access test failed: {e}")
            import traceback
            traceback.print_exc()
        
except Exception as e:
    print(f"Error loading Flask app: {e}")
    import traceback
    traceback.print_exc()