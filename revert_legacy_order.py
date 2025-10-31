#!/usr/bin/env python3
"""
Script to revert legacy levels back to original order
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    client = MongoClient(mongodb_uri, tls=True)
    db = client[mongodb_db]
    
    # Revert the changes - reverse the order back
    legacy_levels = list(db.levels.find({'is_legacy': True}).sort('position', 1))
    print(f'Reverting {len(legacy_levels)} legacy levels back to original order...')
    
    # Reverse the order back
    reversed_legacy = list(reversed(legacy_levels))
    
    for i, level in enumerate(reversed_legacy):
        new_position = 151 + i
        db.levels.update_one(
            {'_id': level['_id']},
            {'$set': {'position': new_position}}
        )
        print(f"  {level['name']}: {level['position']} → {new_position}")
    
    print('✅ Reverted legacy levels to original positions')

if __name__ == "__main__":
    main()