import sqlite3
import json
from datetime import datetime

def export_sqlite_to_json():
    # Connect to SQLite
    conn = sqlite3.connect('instance/demonlist.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Export Users
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    
    users_data = []
    for user in users:
        user_dict = {
            "_id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "password_hash": user['password_hash'],
            "is_admin": bool(user['is_admin']),
            "points": user['points'] or 0,
            "date_joined": {"$date": user['date_joined']} if user['date_joined'] else {"$date": datetime.utcnow().isoformat() + "Z"},
            "google_id": user['google_id'] if 'google_id' in user.keys() else None
        }
        users_data.append(user_dict)
    
    with open('users_real.json', 'w') as f:
        json.dump(users_data, f, indent=2)
    
    # Export Levels
    cursor.execute("SELECT * FROM level")
    levels = cursor.fetchall()
    
    levels_data = []
    for level in levels:
        level_dict = {
            "_id": level['id'],
            "name": level['name'],
            "creator": level['creator'],
            "verifier": level['verifier'],
            "level_id": level['level_id'],
            "video_url": level['video_url'],
            "thumbnail_url": level['thumbnail_url'] if 'thumbnail_url' in level.keys() else None,
            "description": level['description'],
            "difficulty": level['difficulty'],
            "position": level['position'],
            "is_legacy": bool(level['is_legacy']),
            "date_added": {"$date": level['date_added']} if level['date_added'] else {"$date": datetime.utcnow().isoformat() + "Z"},
            "points": level['points'] or 0,
            "min_percentage": level['min_percentage'] or 100
        }
        levels_data.append(level_dict)
    
    with open('levels_real.json', 'w') as f:
        json.dump(levels_data, f, indent=2)
    
    # Export Records
    cursor.execute("SELECT * FROM record")
    records = cursor.fetchall()
    
    records_data = []
    for record in records:
        record_dict = {
            "_id": record['id'],
            "user_id": record['user_id'],
            "level_id": record['level_id'],
            "progress": record['progress'],
            "video_url": record['video_url'],
            "status": record['status'],
            "date_submitted": {"$date": record['date_submitted']} if record['date_submitted'] else {"$date": datetime.utcnow().isoformat() + "Z"}
        }
        records_data.append(record_dict)
    
    with open('records_real.json', 'w') as f:
        json.dump(records_data, f, indent=2)
    
    conn.close()
    
    print(f"Exported {len(users_data)} users to users_real.json")
    print(f"Exported {len(levels_data)} levels to levels_real.json")
    print(f"Exported {len(records_data)} records to records_real.json")

if __name__ == "__main__":
    export_sqlite_to_json()