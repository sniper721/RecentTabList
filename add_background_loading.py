import re

# Read the file
with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the preload_cache_from_files function and modify it to load in background
old_func = "def preload_cache_from_files():"
new_func = '''def preload_cache_from_files():
    """Load cache from JSON files immediately (instant, no database needed)"""
    try:
        # Load main levels cache
        if os.path.exists('cache_main_levels.json'):
            with open('cache_main_levels.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                levels_list = data.get('levels', [])
                
                if isinstance(levels_list, list):
                    levels_cache['main_list'] = levels_list
                    levels_cache['last_updated'] = data.get('last_updated')
                    count = len(levels_list)
                    print(f"Loaded {count} main levels from cache")
        
        # Load legacy levels cache
        if os.path.exists('cache_legacy_levels.json'):
            with open('cache_legacy_levels.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                levels_list = data.get('levels', [])
                
                if isinstance(levels_list, list):
                    levels_cache['legacy_list'] = levels_list
                    count = len(levels_list)
                    print(f"Loaded {count} legacy levels from cache")
        
        levels_cache['loaded'] = True
        
        # Start background refresh from database
        def refresh_cache_background():
            import time
            time.sleep(5)  # Wait 5 seconds before refreshing
            try:
                if mongo_manager.is_connected():
                    print("Refreshing cache from database in background...")
                    mongo_manager._update_cache_from_db()
            except Exception as e:
                print(f"Background cache refresh failed: {e}")
        
        import threading
        refresh_thread = threading.Thread(target=refresh_cache_background, daemon=True)
        refresh_thread.start()
        
        return True
        
    except Exception as e:
        print(f"Cache preload failed: {e}")
        levels_cache['main_list'] = []
        levels_cache['legacy_list'] = []
        levels_cache['loaded'] = True
        return False

def preload_cache_from_files_OLD():'''

if old_func in content:
    content = content.replace(old_func, new_func, 1)
    
    # Write back
    with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Successfully added background cache loading!")
else:
    print("Could not find preload_cache_from_files function")
