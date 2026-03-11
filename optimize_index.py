import re

# Read the file
with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the index route with optimized version
old_start = "@app.route('/')\ndef index():"
old_end = "auto_refresh=False)"

start_idx = content.find(old_start)
if start_idx != -1:
    end_idx = content.find(old_end, start_idx)
    if end_idx != -1:
        end_idx += len(old_end)
        
        # Optimized version with faster loading
        new_code = '''@app.route('/')
def index():
    """Main list page - optimized for fast loading"""
    try:
        # Try cache first (instant)
        main_list = levels_cache.get('main_list')
        
        # If cache empty, load from database with minimal fields
        if not main_list:
            print("Loading from database...")
            # Only load essential fields for speed
            cursor = mongo_db.levels.find(
                {"is_legacy": False},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
                 "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1, 
                 "thumbnail_url": 1, "min_percentage": 1}
            ).sort("position", 1).limit(150)
            
            main_list = list(cursor)
            
            # Cache it
            if main_list:
                levels_cache['main_list'] = main_list
                print(f"Loaded {len(main_list)} levels")
        
        # APRIL FOOLS MODE
        if is_april_fools_active() and main_list:
            main_list = randomize_level_positions(main_list.copy())
        
        return render_template('index.html', 
                             levels=main_list or [],
                             total_levels=len(main_list) if main_list else 0,
                             april_fools_active=is_april_fools_active(),
                             auto_refresh=False)'''
        
        # Replace the section
        new_content = content[:start_idx] + new_code + content[end_idx:]
        
        # Write back
        with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("Successfully optimized index route for faster loading!")
    else:
        print("Could not find end marker")
else:
    print("Could not find start marker")
