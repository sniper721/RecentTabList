#!/usr/bin/env python3
"""Test script to check if all routes are properly registered"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    
    print("Testing route registration...")
    
    # Get all registered routes
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append((rule.rule, rule.endpoint))
    
    # Sort routes for easier reading
    routes.sort()
    
    print(f"\nFound {len(routes)} registered routes:")
    
    # Look for future_list specifically
    future_routes = [r for r in routes if 'future' in r[1]]
    
    print("\nFuture-related routes:")
    for route, endpoint in future_routes:
        print(f"  {route} -> {endpoint}")
    
    # Check if future_list exists
    future_list_exists = any(endpoint == 'future_list' for route, endpoint in routes)
    print(f"\nfuture_list route exists: {future_list_exists}")
    
    if not future_list_exists:
        print("\nAll routes:")
        for route, endpoint in routes:
            print(f"  {route} -> {endpoint}")
    
except Exception as e:
    print(f"Error loading routes: {e}")
    import traceback
    traceback.print_exc()