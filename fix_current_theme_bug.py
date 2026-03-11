"""
Quick fix for current_theme undefined error
Run this to patch main.py
"""
import re

print("🔧 Fixing current_theme bug in main.py...")

# Read main.py
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the utility_processor function and ensure current_theme is always set safely
# Look for the current_theme definition
old_code = """    # Get current theme from session (with error handling)
    try:
        current_theme = session.get('theme', 'light')
    except RuntimeError:
        # No request context available
        current_theme = 'light'"""

new_code = """    # Get current theme from session (with robust error handling)
    try:
        current_theme = session.get('theme', 'light') if session else 'light'
    except (RuntimeError, AttributeError):
        # No request context or session not available
        current_theme = 'light'"""

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ Updated current_theme error handling")
else:
    print("⚠️ Could not find exact current_theme code, trying alternative...")
    
    # Try a more flexible replacement
    pattern = r"# Get current theme from session.*?current_theme = 'light'"
    replacement = """# Get current theme from session (with robust error handling)
    try:
        current_theme = session.get('theme', 'light') if session else 'light'
    except (RuntimeError, AttributeError):
        # No request context or session not available
        current_theme = 'light'"""
    
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    print("✅ Applied regex-based fix for current_theme")

# Write back
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✨ current_theme bug fixed!")
print("💡 Run: python main.py")
