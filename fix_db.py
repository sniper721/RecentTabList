import sqlite3
import os
import sys

def fix_database():
    """
    Fix the database schema by adding missing columns directly using SQLite commands
    """
    print("Starting database fix...")
    
    # Connect to the database
    db_path = os.path.join('instance', 'demonlist.db')
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get table info for level table
        cursor.execute("PRAGMA table_info(level)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add points column to level table if it doesn't exist
        if 'points' not in columns:
            print("Adding points column to level table...")
            cursor.execute("ALTER TABLE level ADD COLUMN points FLOAT DEFAULT 0.0")
            cursor.execute("UPDATE level SET points = (100 - position + 1) / 10.0 WHERE is_legacy = 0")
        
        # Add min_percentage column to level table if it doesn't exist
        if 'min_percentage' not in columns:
            print("Adding min_percentage column to level table...")
            cursor.execute("ALTER TABLE level ADD COLUMN min_percentage INTEGER DEFAULT 100")
        
        # Get table info for user table
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add points column to user table if it doesn't exist
        if 'points' not in columns:
            print("Adding points column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN points FLOAT DEFAULT 0.0")
        
        # Add google_id column to user table if it doesn't exist
        if 'google_id' not in columns:
            print("Adding google_id column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN google_id TEXT")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_google_id ON user(google_id)")
        
        # Get table info for record table
        cursor.execute("PRAGMA table_info(record)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add points column to record table if it doesn't exist
        if 'points' not in columns:
            print("Adding points column to record table...")
            cursor.execute("ALTER TABLE record ADD COLUMN points FLOAT DEFAULT 0.0")
        
        # Calculate points for records based on level points and progress
        print("Calculating points for records...")
        cursor.execute("""
            UPDATE record 
            SET points = (
                SELECT (level.points * record.progress / 100.0)
                FROM level 
                WHERE level.id = record.level_id
                AND record.progress >= level.min_percentage
                AND record.status = 'approved'
            )
            WHERE record.points = 0.0
        """)
        
        # Calculate total points for users based on their records
        print("Calculating total points for users...")
        cursor.execute("""
            UPDATE user
            SET points = (
                SELECT COALESCE(SUM(record.points), 0)
                FROM record
                WHERE record.user_id = user.id
                AND record.status = 'approved'
            )
        """)
        
        # Commit the changes
        conn.commit()
        print("Database fix completed successfully!")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error during database fix: {e}")
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    success = fix_database()
    if success:
        print("Database has been fixed successfully!")
        sys.exit(0)
    else:
        print("Failed to fix database.")
        sys.exit(1)