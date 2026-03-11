with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the index route start
start = content.find("@app.route('/')\ndef index():")
if start == -1:
    print("Could not find index route")
    exit(1)

# Find the next route after index
next_route = content.find("\n@app.route(", start + 10)
if next_route == -1:
    print("Could not find next route")
    exit(1)

# Replace everything between start and next_route
new_index = """@app.route('/')
def index():
    main_list = levels_cache.get('main_list', [])
    if is_april_fools_active() and main_list:
        main_list = randomize_level_positions(main_list.copy())
    return render_template('index.html', levels=main_list, total_levels=len(main_list), april_fools_active=is_april_fools_active())

"""

new_content = content[:start] + new_index + content[next_route+1:]

with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed index route")
