import re

# Read the file
with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the index route with instant loading version
old_start = "@app.route('/')\ndef index():"
old_end = "auto_refresh=False)"

start_idx = content.find(old_start)
if start_idx != -1:
    end_idx = content.find(old_end, start_idx)
    if end_idx != -1:
        end_idx += len(old_end)
        
        # Ultra-fast version - cache only, no database blocking
        new_code = '''@app.route('/')
def index():
    """Main list page - instant load from cache"""
    # Get from cache immediately (no database wait)
    main_list = levels_cache.get('main_list', [])
    
    # If empty, return empty list (page loads instantly)
    if not main_list:
        main_list = []
    
    # APRIL FOOLS MODE
    if is_april_fools_active() and main_list:
        main_list = randomize_level_positions(main_list.copy())
    
    return render_template('index.html', 
                         levels=main_list,
                         total_levels=len(main_list),
                         april_fools_active=is_april_fools_active(),
                         auto_refresh=False)'''
        
        # Replace the section
        new_content = content[:start_idx] + new_code + content[end_idx:]
        
        # Write back
        with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("Successfully made index route instant load!")
    else:
        print("Could not find end marker")
else:
    print("Could not find start marker")
