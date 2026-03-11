with open(r'c:\RTL\main.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find("@app.route('/')\ndef index():")
next_route = content.find("\n@app.route(", start + 10)

# Ultra-fast version - just return cached data
new_index = """@app.route('/')
def index():
    main_list = levels_cache.get('main_list') or []
    return render_template('index.html', levels=main_list, total_levels=len(main_list), april_fools_active=False)

"""

new_content = content[:start] + new_index + content[next_route+1:]

with open(r'c:\RTL\main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Created ultra-fast index route")
