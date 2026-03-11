with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find where to add the preload code (after app initialization)
insert_point = content.find("# Initialize Flask app\napp = Flask(__name__)")
if insert_point == -1:
    print("Could not find app initialization")
    exit(1)

# Find the end of that section
insert_point = content.find("\n\n", insert_point + 100)

# Add preload code
preload_code = """

# PRELOAD CACHE ON STARTUP FOR INSTANT LOADING
print("Preloading cache for instant page loads...")
try:
    with open('cache_main_levels.json', 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
        levels_cache['main_list'] = cache_data.get('levels', [])
        print(f"Preloaded {len(levels_cache['main_list'])} levels into memory")
except Exception as e:
    print(f"Cache preload failed: {e}")
    levels_cache['main_list'] = []
"""

new_content = content[:insert_point] + preload_code + content[insert_point:]

with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Added cache preloading on startup")
