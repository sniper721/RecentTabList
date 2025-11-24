#!/usr/bin/env python3
"""
Regular maintenance script for level images
Run this periodically to keep images working
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
import base64
from io import BytesIO
from PIL import Image
import time
from datetime import datetime

load_dotenv()
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def test_image_url(url):
    """Test if an image URL is accessible"""
    try:
        response = requests.head(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        return response.status_code == 200
    except:
        return False

def download_and_convert_to_base64(url):
    """Download image and convert to base64 data URL"""
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if response.status_code != 200:
            return None
            
        # Check file size (max 5MB)
        if len(response.content) > 5 * 1024 * 1024:
            return None
            
        # Verify it's actually an image
        try:
            img = Image.open(BytesIO(response.content))
            img.verify()
        except:
            return None
            
        # Get content type
        content_type = response.headers.get('content-type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'
            
        # Convert to base64
        encoded_data = base64.b64encode(response.content).decode('utf-8')
        data_url = f"data:{content_type};base64,{encoded_data}"
        
        return data_url
        
    except Exception as e:
        return None

def get_youtube_thumbnail(video_url):
    """Extract YouTube video ID and generate thumbnail URL"""
    try:
        if 'youtube.com' in video_url and 'v=' in video_url:
            video_id = video_url.split('v=')[1].split('&')[0]
        elif 'youtu.be' in video_url:
            video_id = video_url.split('/')[-1].split('?')[0]
        else:
            return None
            
        # Try different YouTube thumbnail formats
        formats = [
            f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
            f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            f'https://img.youtube.com/vi/{video_id}/sddefault.jpg',
            f'https://img.youtube.com/vi/{video_id}/default.jpg'
        ]
        
        for thumb_url in formats:
            if test_image_url(thumb_url):
                return download_and_convert_to_base64(thumb_url)
                
        return None
        
    except Exception as e:
        return None

def run_maintenance():
    """Run regular image maintenance"""
    try:
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        print(f"🔧 Starting image maintenance - {datetime.now()}")
        
        total_fixed = 0
        
        # 1. Check Discord CDN URLs (they expire frequently)
        discord_levels = list(db.levels.find({
            'thumbnail_url': {'$regex': 'cdn.discordapp.com|media.discordapp.net'}
        }))
        
        if discord_levels:
            print(f"\n📱 Checking {len(discord_levels)} Discord CDN URLs...")
            for level in discord_levels:
                name = level.get('name', 'Unknown')
                pos = level.get('position', '?')
                thumb_url = level.get('thumbnail_url', '')
                
                if not test_image_url(thumb_url):
                    print(f"  ❌ #{pos} {name} - Discord URL expired")
                    
                    # Try to download and convert to base64
                    new_thumb = download_and_convert_to_base64(thumb_url)
                    if new_thumb:
                        db.levels.update_one(
                            {'_id': level['_id']},
                            {'$set': {'thumbnail_url': new_thumb}}
                        )
                        print(f"    ✅ Converted to base64")
                        total_fixed += 1
                    else:
                        # Try YouTube fallback
                        video_url = level.get('video_url', '')
                        if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                            youtube_thumb = get_youtube_thumbnail(video_url)
                            if youtube_thumb:
                                db.levels.update_one(
                                    {'_id': level['_id']},
                                    {'$set': {'thumbnail_url': youtube_thumb}}
                                )
                                print(f"    ✅ Used YouTube thumbnail")
                                total_fixed += 1
                            else:
                                db.levels.update_one(
                                    {'_id': level['_id']},
                                    {'$set': {'thumbnail_url': ''}}
                                )
                                print(f"    🧹 Cleared broken URL")
                                total_fixed += 1
                        else:
                            db.levels.update_one(
                                {'_id': level['_id']},
                                {'$set': {'thumbnail_url': ''}}
                            )
                            print(f"    🧹 Cleared broken URL")
                            total_fixed += 1
                else:
                    print(f"  ✅ #{pos} {name} - Discord URL working")
        
        # 2. Check other external URLs
        external_levels = list(db.levels.find({
            'thumbnail_url': {'$regex': '^https?://'},
            'thumbnail_url': {'$not': {'$regex': 'discord'}}
        }))
        
        if external_levels:
            print(f"\n🌐 Checking {len(external_levels)} external URLs...")
            for level in external_levels:
                name = level.get('name', 'Unknown')
                pos = level.get('position', '?')
                thumb_url = level.get('thumbnail_url', '')
                
                if not test_image_url(thumb_url):
                    print(f"  ❌ #{pos} {name} - External URL not accessible")
                    
                    # Try YouTube fallback
                    video_url = level.get('video_url', '')
                    if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                        youtube_thumb = get_youtube_thumbnail(video_url)
                        if youtube_thumb:
                            db.levels.update_one(
                                {'_id': level['_id']},
                                {'$set': {'thumbnail_url': youtube_thumb}}
                            )
                            print(f"    ✅ Used YouTube thumbnail")
                            total_fixed += 1
                        else:
                            db.levels.update_one(
                                {'_id': level['_id']},
                                {'$set': {'thumbnail_url': ''}}
                            )
                            print(f"    🧹 Cleared broken URL")
                            total_fixed += 1
                    else:
                        db.levels.update_one(
                            {'_id': level['_id']},
                            {'$set': {'thumbnail_url': ''}}
                        )
                        print(f"    🧹 Cleared broken URL")
                        total_fixed += 1
                else:
                    print(f"  ✅ #{pos} {name} - External URL working")
        
        # 3. Add thumbnails for YouTube videos without images (limit to avoid rate limiting)
        no_image_levels = list(db.levels.find({
            'video_url': {'$regex': 'youtu'},
            '$or': [
                {'thumbnail_url': {'$exists': False}},
                {'thumbnail_url': ''},
                {'thumbnail_url': None}
            ]
        }).limit(5))  # Only process 5 at a time
        
        if no_image_levels:
            print(f"\n📺 Adding thumbnails for {len(no_image_levels)} YouTube videos...")
            for level in no_image_levels:
                name = level.get('name', 'Unknown')
                pos = level.get('position', '?')
                video_url = level.get('video_url', '')
                
                youtube_thumb = get_youtube_thumbnail(video_url)
                if youtube_thumb:
                    db.levels.update_one(
                        {'_id': level['_id']},
                        {'$set': {'thumbnail_url': youtube_thumb}}
                    )
                    print(f"  ✅ #{pos} {name} - Added YouTube thumbnail")
                    total_fixed += 1
                else:
                    print(f"  ❌ #{pos} {name} - Could not get YouTube thumbnail")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
        
        print(f"\n🎉 Maintenance completed!")
        print(f"   Total fixes applied: {total_fixed}")
        
        if total_fixed == 0:
            print("   All images are working properly! 👍")
        
    except Exception as e:
        print(f'❌ Maintenance error: {e}')

if __name__ == "__main__":
    run_maintenance()