#!/usr/bin/env python3
"""
Fix image errors for levels including expired Discord CDN URLs and missing images
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
import requests
import base64
from io import BytesIO
from PIL import Image
import time

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
            print(f"  ⚠️  Image too large: {len(response.content)} bytes")
            return None
            
        # Verify it's actually an image
        try:
            img = Image.open(BytesIO(response.content))
            img.verify()
        except:
            print(f"  ❌ Invalid image format")
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
        print(f"  ❌ Error downloading image: {e}")
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
        print(f"  ❌ Error getting YouTube thumbnail: {e}")
        return None

def fix_image_errors():
    """Fix various image errors in the levels database"""
    try:
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        print("🔧 Starting image error fixes...")
        
        # 1. Fix expired Discord CDN URLs
        print("\n1️⃣ Checking Discord CDN URLs...")
        discord_levels = list(db.levels.find({
            'thumbnail_url': {'$regex': 'cdn.discordapp.com|media.discordapp.net'}
        }))
        
        discord_fixed = 0
        for level in discord_levels:
            name = level.get('name', 'Unknown')
            pos = level.get('position', '?')
            thumb_url = level.get('thumbnail_url', '')
            
            print(f"  Checking #{pos} {name}...")
            
            if not test_image_url(thumb_url):
                print(f"    ❌ Discord URL expired: {thumb_url[:50]}...")
                
                # Try to download and convert to base64
                new_thumb = download_and_convert_to_base64(thumb_url)
                if new_thumb:
                    db.levels.update_one(
                        {'_id': level['_id']},
                        {'$set': {'thumbnail_url': new_thumb}}
                    )
                    print(f"    ✅ Converted to base64 ({len(new_thumb)//1024}KB)")
                    discord_fixed += 1
                else:
                    # Try YouTube fallback if available
                    video_url = level.get('video_url', '')
                    if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                        youtube_thumb = get_youtube_thumbnail(video_url)
                        if youtube_thumb:
                            db.levels.update_one(
                                {'_id': level['_id']},
                                {'$set': {'thumbnail_url': youtube_thumb}}
                            )
                            print(f"    ✅ Used YouTube thumbnail fallback")
                            discord_fixed += 1
                        else:
                            # Clear broken URL
                            db.levels.update_one(
                                {'_id': level['_id']},
                                {'$set': {'thumbnail_url': ''}}
                            )
                            print(f"    🧹 Cleared broken URL (will use YouTube auto)")
                            discord_fixed += 1
                    else:
                        # Clear broken URL
                        db.levels.update_one(
                            {'_id': level['_id']},
                            {'$set': {'thumbnail_url': ''}}
                        )
                        print(f"    🧹 Cleared broken URL")
                        discord_fixed += 1
            else:
                print(f"    ✅ Discord URL still working")
        
        # 2. Fix broken local file URLs
        print("\n2️⃣ Fixing broken local file URLs...")
        broken_local = list(db.levels.find({
            'thumbnail_url': {'$regex': '^/static/thumbnails/'}
        }))
        
        local_fixed = 0
        for level in broken_local:
            name = level.get('name', 'Unknown')
            pos = level.get('position', '?')
            
            print(f"  Fixing #{pos} {name}...")
            
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
                    local_fixed += 1
                else:
                    # Clear broken URL
                    db.levels.update_one(
                        {'_id': level['_id']},
                        {'$set': {'thumbnail_url': ''}}
                    )
                    print(f"    🧹 Cleared broken URL")
                    local_fixed += 1
            else:
                # Clear broken URL
                db.levels.update_one(
                    {'_id': level['_id']},
                    {'$set': {'thumbnail_url': ''}}
                )
                print(f"    🧹 Cleared broken URL")
                local_fixed += 1
        
        # 3. Add thumbnails for levels with YouTube videos but no images
        print("\n3️⃣ Adding thumbnails for YouTube videos without images...")
        no_image_levels = list(db.levels.find({
            'video_url': {'$regex': 'youtu'},
            '$or': [
                {'thumbnail_url': {'$exists': False}},
                {'thumbnail_url': ''},
                {'thumbnail_url': None}
            ]
        }).limit(10))  # Limit to avoid rate limiting
        
        youtube_added = 0
        for level in no_image_levels:
            name = level.get('name', 'Unknown')
            pos = level.get('position', '?')
            video_url = level.get('video_url', '')
            
            print(f"  Adding thumbnail for #{pos} {name}...")
            
            youtube_thumb = get_youtube_thumbnail(video_url)
            if youtube_thumb:
                db.levels.update_one(
                    {'_id': level['_id']},
                    {'$set': {'thumbnail_url': youtube_thumb}}
                )
                print(f"    ✅ Added YouTube thumbnail")
                youtube_added += 1
            else:
                print(f"    ❌ Could not get YouTube thumbnail")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # 4. Test external URLs for accessibility
        print("\n4️⃣ Testing external image URLs...")
        external_levels = list(db.levels.find({
            'thumbnail_url': {'$regex': '^https?://'}
        }))
        
        external_fixed = 0
        for level in external_levels:
            name = level.get('name', 'Unknown')
            pos = level.get('position', '?')
            thumb_url = level.get('thumbnail_url', '')
            
            # Skip Discord URLs (already handled)
            if 'discord' in thumb_url:
                continue
                
            print(f"  Testing #{pos} {name}...")
            
            if not test_image_url(thumb_url):
                print(f"    ❌ External URL not accessible: {thumb_url[:50]}...")
                
                # Try YouTube fallback
                video_url = level.get('video_url', '')
                if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                    youtube_thumb = get_youtube_thumbnail(video_url)
                    if youtube_thumb:
                        db.levels.update_one(
                            {'_id': level['_id']},
                            {'$set': {'thumbnail_url': youtube_thumb}}
                        )
                        print(f"    ✅ Used YouTube thumbnail fallback")
                        external_fixed += 1
                    else:
                        # Clear broken URL
                        db.levels.update_one(
                            {'_id': level['_id']},
                            {'$set': {'thumbnail_url': ''}}
                        )
                        print(f"    🧹 Cleared broken URL")
                        external_fixed += 1
                else:
                    # Clear broken URL
                    db.levels.update_one(
                        {'_id': level['_id']},
                        {'$set': {'thumbnail_url': ''}}
                    )
                    print(f"    🧹 Cleared broken URL")
                    external_fixed += 1
            else:
                print(f"    ✅ External URL working")
        
        print(f"\n🎉 Image fixes completed!")
        print(f"   Discord CDN URLs fixed: {discord_fixed}")
        print(f"   Broken local URLs fixed: {local_fixed}")
        print(f"   YouTube thumbnails added: {youtube_added}")
        print(f"   External URLs fixed: {external_fixed}")
        print(f"   Total fixes: {discord_fixed + local_fixed + youtube_added + external_fixed}")
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    fix_image_errors()