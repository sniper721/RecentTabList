import sys

# Read the file
with open(r'c:\RTL\main.py', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Find the index route (around line 6147)
for i, line in enumerate(lines):
    if line.strip() == "@app.route('/')":
        # Found it, now replace the next ~50 lines
        start_idx = i
        
        # Find the end of the function (next @app.route or end of try block)
        end_idx = start_idx + 1
        indent_count = 0
        for j in range(start_idx + 1, min(start_idx + 100, len(lines))):
            if lines[j].strip().startswith('@app.route'):
                end_idx = j
                break
            if 'except Exception as e:' in lines[j] and indent_count == 0:
                # Find the end of this except block
                for k in range(j, min(j + 20, len(lines))):
                    if lines[k].strip() and not lines[k].startswith(' ') and not lines[k].startswith('\t'):
                        end_idx = k
                        break
                    if k == j + 19:
                        end_idx = k + 1
                break
        
        # Create the new index function
        new_function = '''@app.route('/')
def index():
    """Main list page - instant load"""
    # Get from cache (instant)
    main_list = levels_cache.get('main_list', [])
    
    # APRIL FOOLS MODE
    if is_april_fools_active() and main_list:
        main_list = randomize_level_positions(main_list.copy())
    
    return render_template('index.html', 
                         levels=main_list,
                         total_levels=len(main_list),
                         april_fools_active=is_april_fools_active(),
                         auto_refresh=False)

'''
        
        # Replace the lines
        new_lines = lines[:start_idx] + [new_function] + lines[end_idx:]
        
        # Write back
        with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"Successfully replaced index route (lines {start_idx+1} to {end_idx})")
        sys.exit(0)

print("Could not find @app.route('/') in file")
sys.exit(1)
