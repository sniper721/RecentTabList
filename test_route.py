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
        
except Exception as e:
    print(f"Error loading Flask app: {e}")
    import traceback
    traceback.print_exc()