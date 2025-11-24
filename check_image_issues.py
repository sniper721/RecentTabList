#!/usr/bin/env python3
"""
Check for image issues in levels database
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def check_image_issues():
    try:
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        # Get levels with image issues
        levels = list(db.levels.find({}, {
            'name': 1, 
            'thumbnail_url': 1, 
            'video_url': 1, 
            'position': 1
        }).sort('position', 1).limit(30))
        
        print('=== LEVEL IMAGE STATUS ===')
        broken_count = 0
        no_image_count = 0
        
        for level in levels:
            name = level.get('name', 'Unknown')
            pos = level.get('position', '?')
            thumb = level.get('thumbnail_url', '')
            video = level.get('video_url', '')
            
            # Check image status
            if not thumb or thumb == '':
                if video and ('youtube.com' in video or 'youtu.be' in video):
                    status = 'YouTube Auto'
                else:
                    status = 'NO IMAGE'
                    no_image_count += 1
            elif thumb.startswith('data:image'):
                status = 'Base64 OK'
            elif thumb.startswith('http'):
                status = 'External URL'
            elif thumb.startswith('/static/'):
                status = 'BROKEN LOCAL'
                broken_count += 1
            else:
                status = 'UNKNOWN'
            
            thumb_display = thumb[:30] + '...' if len(thumb) > 30 else thumb
            print(f'{pos:3}. {name:25} | {status:15} | {thumb_display}')
            
            # Check for 'loud clubstep' specifically
            if 'loud' in name.lower() and 'clubstep' in name.lower():
                print(f'    *** FOUND LOUD CLUBSTEP: {name} ***')
        
        print(f'\n=== SUMMARY ===')
        print(f'Broken local images: {broken_count}')
        print(f'No images: {no_image_count}')
        
        # Search for any level with 'loud' in the name
        loud_levels = list(db.levels.find({
            'name': {'$regex': 'loud', '$options': 'i'}
        }, {
            'name': 1, 
            'thumbnail_url': 1, 
            'video_url': 1, 
            'position': 1
        }))
        
        if loud_levels:
            print('\n=== LEVELS WITH "LOUD" IN NAME ===')
            for level in loud_levels:
                pos = level.get('position', '?')
                name = level.get('name', 'Unknown')
                thumb = level.get('thumbnail_url', 'None')
                print(f'{pos:3}. {name} | Thumb: {thumb}')
        
        # Check for levels with broken thumbnail URLs
        broken_levels = list(db.levels.find({
            'thumbnail_url': {'$regex': '^/static/thumbnails/'}
        }, {
            'name': 1, 
            'thumbnail_url': 1, 
            'position': 1
        }))
        
        if broken_levels:
            print('\n=== LEVELS WITH BROKEN LOCAL THUMBNAILS ===')
            for level in broken_levels:
                pos = level.get('position', '?')
                name = level.get('name', 'Unknown')
                thumb = level.get('thumbnail_url', '')
                print(f'{pos:3}. {name} | {thumb}')
        
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    check_image_issues()