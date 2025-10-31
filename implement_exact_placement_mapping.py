#!/usr/bin/env python3
"""
Script to implement the exact placement mapping specified by the user.
Move levels from legacy positions 155-184 to main list positions 121-150.
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0.0
    return round(250 * (0.9475 ** (position - 1)), 2)

def main():
    print("🔧 Implementing exact placement mapping...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Define the exact mapping as specified by the user
    placement_mapping = {
        184: 121,  # ocean wave
        183: 122,  # Thermal Blast
        182: 123,  # Nightcore Pre II
        181: 124,  # The Silent Calling
        180: 125,  # Note Conit
        179: 126,  # sus
        178: 127,  # ice world
        177: 128,  # its not eyse
        176: 129,  # Impossible 3
        175: 130,  # Epsidev
        174: 131,  # Romb
        173: 132,  # ez
        172: 133,  # demon part 3
        171: 134,  # lusty
        170: 135,  # Death Note
        169: 136,  # Unnamed 2
        168: 137,  # mitik
        167: 138,  # Clutterjump
        166: 139,  # itzbran challenge
        165: 140,  # Smth Blsht Easy
        164: 141,  # glass
        163: 142,  # dimension challenge
        162: 143,  # blind eye
        161: 144,  # Faces of Death
        160: 145,  # sparkling
        159: 146,  # City Hoppin
        158: 147,  # Seaquake
        157: 148,  # Dalbayob
        156: 149,  # D S O P Ne
        155: 150   # Donkka
    }
    
    print("Placement mapping:")
    for old_pos, new_pos in placement_mapping.items():
        level = db.levels.find_one({'position': old_pos})
        if level:
            print(f"  {level['name']} (position {old_pos}) → position {new_pos}")
        else:
            print(f"  Position {old_pos} → position {new_pos} (level not found)")
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(placement_mapping)} levels according to the exact mapping. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Apply the mapping
    updated_count = 0
    for old_position, new_position in placement_mapping.items():
        level = db.levels.find_one({'position': old_position})
        
        if level:
            # Calculate points for the new main list position
            new_points = calculate_level_points(new_position, False)
            
            result = db.levels.update_one(
                {'_id': level['_id']},
                {'$set': {
                    'position': new_position,
                    'is_legacy': False,
                    'points': new_points
                }}
            )
            
            if result.modified_count > 0:
                updated_count += 1
                print(f"  ✅ {level['name']}: {old_position} → {new_position} ({new_points} points)")
            else:
                print(f"  ❌ Failed to update {level['name']}")
        else:
            print(f"  ⚠️  No level found at position {old_position}")
    
    print(f"\n🎉 Successfully updated {updated_count} levels!")
    
    # Verify the changes
    new_main_count = db.levels.count_documents({'is_legacy': False})
    new_legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nNew state:")
    print(f"  Main list: {new_main_count} levels")
    print(f"  Legacy list: {new_legacy_count} levels")
    
    # Check specific positions mentioned
    ocean_wave = db.levels.find_one({'position': 121, 'name': 'ocean wave'})
    donkka = db.levels.find_one({'position': 150, 'name': 'Donkka'})
    
    if ocean_wave:
        print(f"✅ ocean wave is now at position 121")
    if donkka:
        print(f"✅ Donkka is now at position 150")
    
    print("\n✅ Exact placement mapping implemented successfully!")

if __name__ == "__main__":
    main()