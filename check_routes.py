#!/usr/bin/env python3

# Quick script to check what routes are registered in the Flask app
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    
    print("Flask app loaded successfully!")
    print("\nRegistered routes:")
    
    for rule in app.url_map.iter_rules():
        print(f"  {rule.endpoint}: {rule.rule} {list(rule.methods)}")
    
    # Check specifically for recent_tab_roulette
    if 'recent_tab_roulette' in [rule.endpoint for rule in app.url_map.iter_rules()]:
        print("\n[OK] recent_tab_roulette route is registered!")
    else:
        print("\n[ERROR] recent_tab_roulette route is NOT registered!")
        
except Exception as e:
    print(f"Error loading Flask app: {e}")
    import traceback
    traceback.print_exc()