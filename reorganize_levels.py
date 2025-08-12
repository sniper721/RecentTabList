#!/usr/bin/env python3
"""
Script to reorganize levels to their actual placements and move some to legacy
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    return int(250 * (0.9475 ** (position - 1)))

def connect_to_db():
    """Connect to MongoDB"""
    client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=5000
    )
    db = client[mongodb_db]
    client.admin.command('ping')
    return client, db

def reorganize_levels(db):
    """Reorganize levels to match Google Sheets order and move some to legacy"""
    
    # Define the correct order from your Google Sheets (top 100)
    correct_order = [
        "deimonx",
        "fommy txt do verify", 
        "the light circles",
        "old memories",
        "los pollos tv 3",
        "Beans and Onion",
        "FIVE CIRCLES",
        "alone",
        "Golden",
        "every mod",
        "come with me",
        "challenge 10",
        "skeletal v2",
        "Driftaway Challenge",
        "Femboy Temple",
        "The Three Immortals",
        "Clickazor",
        "Rooms",
        "Kokmok Unlid Beta",
        "Wave Challenge I",
        "saMkopL",
        "Can You RIP",
        "hard but possible",
        "Sigma challenge",
        "CloudForm v2",
        "losing my mind pre2",
        "Multi Wave",
        "The Complex 0s",
        "Ice Cave",
        "Drop",
        "The Seven Seas",
        "Stranger",
        "Crazy Hell",
        "Blue Layout buff",
        "The Void 2",
        "Splash",
        "noSheiSatDevat",
        "Destruccion",
        "ocean wave",
        "spam",
        "Dima Loh",
        "my ordinary life",
        "Avernus Challenge",
        "Nightcore Pre II",
        "The Silent Calling",
        "Note Conit",
        "sus",
        "ice world",
        "its not eyse",
        "Impossible 3",
        "demon part 3",
        "lusty",
        "Death Note",
        "Unnamed 2",
        "Kills4 1 part",
        "mitik",
        "Clutterjump",
        "itzbran challenge",
        "Smth Blsht Easy",
        "glass",
        "dimension challenge",
        "blind eye",
        "Faces of Death",
        "sparkling",
        "City Hoppin",
        "Seaquake",
        "Dalbayob",
        "Donkka",
        "Wedro",
        "Bauti 1",
        "Bowsergd Level",
        "Make Your Clubstep",
        "Preview",
        "Tidal Fly",
        "juxaposition",
        "Crazy Year",
        "limbo 3",
        "xaoc",
        "wondahoy",
        "Ajde izazov",
        "blood",
        "Straight Fly",
        "Unnamed 1",
        "The 4 spike jumpbuf",
        "trick to death",
        "Insane",
        "Time To Machine",
        "Black Hole",
        "Knowday",
        "Venomaner",
        "zstep",
        "Deamonic Power",
        "Lox",
        "Insane Challenge",
        "Insane Tsunami",
        "Stereo Madness Wave",
        "Geometry Preview 3"
    ]
    
    # Levels to move to legacy (these are not in the current top 100)
    legacy_levels = [
        "555",
        "Monsters Atack 6", 
        "Challenge",
        "Level"
    ]
    
    print("Reorganizing levels...")
    
    # First, move specified levels to legacy
    legacy_position = 1
    for level_name in legacy_levels:
        level = db.levels.find_one({"name": {"$regex": f"^{level_name}$", "$options": "i"}})
        if level:
            print(f"Moving to legacy: {level['name']}")
            db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {
                    "is_legacy": True,
                    "position": legacy_position,
                    "points": 0
                }}
            )
            legacy_position += 1
    
    # Now reorganize the main list according to Google Sheets order
    updates = []
    for new_position, level_name in enumerate(correct_order, 1):
        # Find level by name (case insensitive)
        level = db.levels.find_one({
            "name": {"$regex": f"^{level_name}$", "$options": "i"},
            "is_legacy": {"$ne": True}
        })
        
        if level:
            new_points = calculate_level_points(new_position, False)
            old_position = level.get('position', 0)
            
            if old_position != new_position:
                updates.append({
                    'name': level['name'],
                    'old_position': old_position,
                    'new_position': new_position,
                    'new_points': new_points,
                    'has_thumbnail': bool(level.get('thumbnail_url', '').strip())
                })
                
                # Update in database
                db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {
                        "position": new_position,
                        "points": new_points,
                        "is_legacy": False
                    }}
                )
        else:
            print(f"Warning: Level '{level_name}' not found in database")
    
    print(f"\nUpdated {len(updates)} levels:")
    for update in updates:
        thumbnail_info = "📷" if update['has_thumbnail'] else "❌"
        print(f"  {update['new_position']:3d}. {update['name']} (was #{update['old_position']}) - {update['new_points']} pts {thumbnail_info}")
    
    return len(updates)

def show_final_state(db):
    """Show the final state of levels"""
    print("\n" + "="*80)
    print("FINAL LEVEL ORGANIZATION")
    print("="*80)
    
    # Main list
    main_levels = list(db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
    print(f"\nMAIN LIST ({len(main_levels)} levels):")
    for level in main_levels:
        has_thumbnail = bool(level.get('thumbnail_url', '').strip())
        thumbnail_info = "📷" if has_thumbnail else "❌"
        print(f"  {level['position']:3d}. {level['name']} ({level['points']} pts) {thumbnail_info}")
    
    # Legacy list
    legacy_levels = list(db.levels.find({"is_legacy": True}).sort("position", 1))
    print(f"\nLEGACY LIST ({len(legacy_levels)} levels):")
    for level in legacy_levels:
        has_thumbnail = bool(level.get('thumbnail_url', '').strip())
        thumbnail_info = "📷" if has_thumbnail else "❌"
        print(f"  {level['position']:3d}. {level['name']} (0 pts) {thumbnail_info}")

def main():
    """Main function"""
    print("Connecting to database...")
    client, db = connect_to_db()
    
    try:
        print("✓ Connected to MongoDB")
        
        # Reorganize levels
        updated_count = reorganize_levels(db)
        
        print(f"\n✓ Reorganized {updated_count} levels")
        
        # Show final state
        show_final_state(db)
        
    finally:
        client.close()

if __name__ == "__main__":
    main()