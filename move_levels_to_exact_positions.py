#!/usr/bin/env python3
"""
Script to move the specified levels to their exact target positions.
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
    print("🔧 Moving levels to exact target positions...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Define the exact mapping: level_name -> target_position
    target_positions = {
        'ocean wave': 121,
        'Thermal Blast': 122,
        'Nightcore Pre II': 123,
        'The Silent Calling': 124,
        'Note Conit': 125,
        'sus': 126,
        'ice world': 127,
        'its not eyse': 128,
        'Impossible 3': 129,
        'Epsidev': 130,
        'Romb': 131,
        'ez': 132,
        'demon part 3': 133,
        'lusty': 134,
        'Death Note': 135,
        'Unnamed 2': 136,
        'mitik': 137,
        'Clutterjump': 138,
        'itzbran challenge': 139,
        'Smth Blsht Easy': 140,
        'glass': 141,
        'dimension challenge': 142,
        'blind eye': 143,
        'Faces of Death': 144,
        'sparkling': 145,
        'City Hoppin': 146,
        'Seaquake': 147,
        'Dalbayob': 148,
        'D S O P Ne': 149,
        'Donkka': 150
    }
    
    print("Target positions:")
    levels_to_update = []
    for level_name, target_pos in target_positions.items():
        level = db.levels.find_one({'name': level_name})
        if level:
            current_pos = level['position']
            if current_pos != target_pos:
                levels_to_update.append((level, target_pos))
                print(f"  {level_name}: {current_pos} → {target_pos}")
            else:
                print(f"  {level_name}: already at {target_pos} ✅")
        else:
            print(f"  {level_name}: NOT FOUND ❌")
    
    if not levels_to_update:
        print("\nAll levels are already at their target positions!")
        return
    
    # Ask for confirmation
    response = input(f"\nThis will move {len(levels_to_update)} levels to their target positions. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # Update positions
    updated_count = 0
    for level, target_position in levels_to_update:
        new_points = calculate_level_points(target_position, False)
        
        result = db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {
                'position': target_position,
                'is_legacy': False,
                'points': new_points
            }}
        )
        
        if result.modified_count > 0:
            updated_count += 1
            print(f"  ✅ {level['name']}: {level['position']} → {target_position} ({new_points} points)")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully updated {updated_count} levels!")
    
    # Verify key positions
    ocean_wave = db.levels.find_one({'name': 'ocean wave'})
    donkka = db.levels.find_one({'name': 'Donkka'})
    
    if ocean_wave and ocean_wave['position'] == 121:
        print(f"✅ ocean wave is now at position 121")
    if donkka and donkka['position'] == 150:
        print(f"✅ Donkka is now at position 150")
    
    # Check final state
    main_count = db.levels.count_documents({'is_legacy': False})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nFinal state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    print("\n✅ Levels moved to exact target positions as specified!")

if __name__ == "__main__":
    main()