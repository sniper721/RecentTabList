import sqlite3

conn = sqlite3.connect('instance/demonlist.db')
cursor = conn.cursor()

# Check total levels
cursor.execute('SELECT COUNT(*) FROM level')
total = cursor.fetchone()[0]
print(f'Total levels: {total}')

# Show first 20 levels
cursor.execute('SELECT id, name, position, is_legacy FROM level ORDER BY position LIMIT 20')
levels = cursor.fetchall()
print('\nFirst 20 levels:')
for level in levels:
    legacy_status = " (LEGACY)" if level[3] else ""
    print(f'{level[0]}: {level[1]} - Position {level[2]}{legacy_status}')

# Check if there are legacy levels
cursor.execute('SELECT COUNT(*) FROM level WHERE is_legacy = 1')
legacy_count = cursor.fetchone()[0]
print(f'\nLegacy levels: {legacy_count}')

# Check if there are main levels
cursor.execute('SELECT COUNT(*) FROM level WHERE is_legacy = 0')
main_count = cursor.fetchone()[0]
print(f'Main levels: {main_count}')

conn.close()