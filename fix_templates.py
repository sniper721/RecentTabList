import re

# Fix admin levels template
with open('templates/admin/levels.html', 'r') as f:
    content = f.read()

# Replace all level.id with level._id
content = content.replace('{{ level.id }}', '{{ level._id }}')
content = content.replace('data-level-id="{{ level.level_id }}"', 'data-level-game-id="{{ level.level_id }}"')
content = content.replace('data-level-id', 'data-level-game-id')

with open('templates/admin/levels.html', 'w') as f:
    f.write(content)

# Fix index template
with open('templates/index.html', 'r') as f:
    content = f.read()

content = content.replace('{{ level.id if level is not mapping else level[\'id\'] }}', '{{ level._id if level is not mapping else level[\'_id\'] }}')

with open('templates/index.html', 'w') as f:
    f.write(content)

print("Templates fixed!")