import re

# Fix admin levels template
with open('templates/admin/levels.html', 'r') as f:
    content = f.read()

# Add thumbnail data attribute to all edit buttons
content = re.sub(
    r'data-level-game-id="{{ level\.level_id }}" data-level-points="{{ level\.points }}"',
    r'data-level-game-id="{{ level.level_id }}" data-level-points="{{ level.points }}" data-level-thumbnail="{{ level.thumbnail_url or \'\' }}"',
    content
)

# Fix JavaScript to populate thumbnail field
content = content.replace(
    "document.getElementById('edit_level_id').value = levelGameId || '';",
    "document.getElementById('edit_level_id').value = levelGameId || '';\n            document.getElementById('edit_thumbnail_url').value = this.getAttribute('data-level-thumbnail') || '';"
)

with open('templates/admin/levels.html', 'w') as f:
    f.write(content)

print("Admin levels template fixed!")