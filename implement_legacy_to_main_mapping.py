#!/usr/bin/env python3
"""
Script to move specific levels from legacy positions to main list positions 121-150.
This implements the exact mapping specified by the user.
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
    print("🔧 Moving legacy levels to main list positions 121-150...")
    
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Define the exact mapping: level_name -> target_main_position
    target_mapping = {
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
    
    print("Finding levels to move from legacy to main list:")
    levels_to_move = []
    levels_to_displace = []
    
    for level_name, target_position in target_mapping.items():
        # Find the level by name
        level = db.levels.find_one({'name': level_name})
        if level:
            current_pos = level['position']
            is_legacy = level.get('is_legacy', False)
            print(f"  {level_name}: position {current_pos} (legacy: {is_legacy}) → {target_position}")
            levels_to_move.append((level, target_position))
            
            # Check if there's already a level at the target position
            existing_level = db.levels.find_one({'position': target_position, 'is_legacy': False})
            if existing_level and existing_level['_id'] != level['_id']:
                levels_to_displace.append(existing_level)
                print(f"    Will displace: {existing_level['name']} from position {target_position}")
        else:
            print(f"  {level_name}: NOT FOUND ❌")
    
    if not levels_to_move:
        print("No levels found to move!")
        return
    
    print(f"\nThis will:")
    print(f"  - Move {len(levels_to_move)} levels from legacy to main list positions 121-150")
    print(f"  - Displace {len(levels_to_displace)} existing levels to legacy")
    
    # Ask for confirmation
    response = input(f"\nContinue with this mapping? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    # First, move displaced levels to legacy
    next_legacy_pos = 185  # Start after current legacy levels
    displaced_count = 0
    
    for displaced_level in levels_to_displace:
        result = db.levels.update_one(
            {'_id': displaced_level['_id']},
            {'$set': {
                'position': next_legacy_pos,
                'is_legacy': True,
                'points': 0
            }}
        )
        
        if result.modified_count > 0:
            displaced_count += 1
            print(f"  ✅ Displaced {displaced_level['name']}: {displaced_level['position']} → {next_legacy_pos} (legacy)")
            next_legacy_pos += 1
    
    # Now move the target levels to main list
    moved_count = 0
    for level, target_position in levels_to_move:
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
            moved_count += 1
            print(f"  ✅ {level['name']}: {level['position']} → {target_position} ({new_points} points)")
        else:
            print(f"  ❌ Failed to update {level['name']}")
    
    print(f"\n🎉 Successfully moved {moved_count} levels to main list!")
    print(f"🎉 Successfully displaced {displaced_count} levels to legacy!")
    
    # Verify key positions
    ocean_wave = db.levels.find_one({'name': 'ocean wave'})
    donkka = db.levels.find_one({'name': 'Donkka'})
    
    if ocean_wave and ocean_wave['position'] == 121 and not ocean_wave.get('is_legacy', False):
        print(f"✅ ocean wave is now at position 121 (main list)")
    if donkka and donkka['position'] == 150 and not donkka.get('is_legacy', False):
        print(f"✅ Donkka is now at position 150 (main list)")
    
    # Check final state
    main_count = db.levels.count_documents({'is_legacy': False})
    legacy_count = db.levels.count_documents({'is_legacy': True})
    
    print(f"\nFinal state:")
    print(f"  Main list: {main_count} levels")
    print(f"  Legacy list: {legacy_count} levels")
    
    print("\n✅ Legacy to main list mapping completed!")

if __name__ == "__main__":
    main()