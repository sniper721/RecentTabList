#!/usr/bin/env python3
"""
Migration script to add Google authentication support
"""

import sqlite3
import os

def add_google_id_column():
    """Add google_id column to user table if it doesn't exist"""
    db_path = os.path.join('instance', 'demonlist.db')
    
    # Create instance directory if it doesn't exist
    os.makedirs('instance', exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if google_id column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'google_id' not in columns:
            print("Adding google_id column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN google_id TEXT")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_google_id ON user(google_id)")
            conn.commit()
            print("Successfully added google_id column!")
        else:
            print("google_id column already exists.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error adding google_id column: {e}")
        return False

if __name__ == '__main__':
    add_google_id_column()