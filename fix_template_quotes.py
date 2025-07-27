import re

# Fix admin levels template
with open('templates/admin/levels.html', 'r') as f:
    content = f.read()

# Fix escaped quotes
content = content.replace("\\'", "'")

with open('templates/admin/levels.html', 'w') as f:
    f.write(content)

print("Template quotes fixed!")