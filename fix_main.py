#!/usr/bin/env python3
"""
Quick fix script to remove broken world leaderboard code from main.py
"""

def fix_main_py():
    # Read the file
    with open('main.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find where the broken code starts
    fixed_lines = []
    in_broken_section = False
    
    for i, line in enumerate(lines):
        # Check if we're at the broken section
        if "# Remove all the broken world leaderboard code below" in line:
            in_broken_section = True
            fixed_lines.append("# World leaderboard functionality removed\n")
            continue
        
        # Check if we're at the API route (this is where good code resumes)
        if "@app.route('/api/live_stats')" in line:
            in_broken_section = False
        
        # Only add lines if we're not in the broken section
        if not in_broken_section:
            fixed_lines.append(line)
    
    # Write the fixed file
    with open('main.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Fixed main.py - removed broken world leaderboard code")
    print(f"Removed {len(lines) - len(fixed_lines)} lines of broken code")

if __name__ == '__main__':
    fix_main_py()