#!/usr/bin/env python3
"""Fix the index route to load top 100 levels from database"""

# Read the main.py file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the @app.route('/') section
import re

# Pattern to find the index route
pattern = r"(@app\.route\('/'\)[^\n]*\ndef [^\(]+\([^\)]*\):.*?)(?=@app\.route|$)"

match = re.search(pattern, content, re.DOTALL)

if match:
    route_content = match.group(1)
    print("Found index route!")
    print("First 500 chars:")
    print(route_content[:500])
    print("\n" + "="*50 + "\n")
    
    # Check if it's loading levels properly
    if 'mongo_db.levels.find' in route_content:
        print("✓ Route is querying database")
    else:
        print("✗ Route is NOT querying database - needs fix!")
        
    if '.limit(100)' in route_content:
        print("✓ Route is limiting to 100 levels")
    else:
        print("✗ Route is NOT limiting to 100 levels - needs fix!")
else:
    print("Could not find index route!")
