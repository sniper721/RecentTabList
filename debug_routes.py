#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    
    print("Flask app loaded successfully!")
    print("\nAll registered routes:")
    
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append((rule.endpoint, rule.rule, list(rule.methods)))
    
    # Sort by endpoint name
    routes.sort(key=lambda x: x[0])
    
    for endpoint, rule, methods in routes:
        print(f"  {endpoint:30} {rule:30} {methods}")
        
    print(f"\nTotal routes: {len(routes)}")
        
except Exception as e:
    print(f"Error loading Flask app: {e}")
    import traceback
    traceback.print_exc()