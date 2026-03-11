with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the index route
start = content.find("@app.route('/')\ndef index():")
next_route = content.find("\n@app.route(", start + 10)

# Replace with null-safe version
new_index = """@app.route('/')
def index():
    main_list = levels_cache.get('main_list') or []
    if is_april_fools_active() and main_list:
        main_list = randomize_level_positions(main_list.copy())
    return render_template('index.html', levels=main_list, total_levels=len(main_list), april_fools_active=is_april_fools_active())

"""

new_content = content[:start] + new_index + content[next_route+1:]

with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed NoneType error")
