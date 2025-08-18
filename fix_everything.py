#!/usr/bin/env python3
"""
Comprehensive fix script for the Geometry Dash Demon List
Fixes thumbnails, record acceptance, and other issues
"""

import os
import sys
import shutil
import json
from datetime import datetime, timezone

def fix_thumbnails():
    """Fix thumbnail system issues"""
    print("🔧 Fixing thumbnail system...")
    
    try:
        # Clear thumbnail cache
        cache_dir = 'static/thumbs'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            print("✅ Cleared old thumbnail cache")
        
        os.makedirs(cache_dir, exist_ok=True)
        print("✅ Created fresh thumbnail cache directory")
        
        # Create placeholder thumbnail
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (320, 180), color='#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            text = "No Thumbnail"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (320 - text_width) // 2
            y = (180 - text_height) // 2
            
            draw.text((x, y), text, fill='#6c757d', font=font)
            
            placeholder_path = os.path.join(cache_dir, 'placeholder.jpg')
            img.save(placeholder_path, 'JPEG', quality=85)
            print("✅ Created placeholder thumbnail")
            
        except Exception as e:
            print(f"⚠️ Could not create placeholder: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing thumbnails: {e}")
        return False

def fix_database_issues():
    """Fix database-related issues"""
    print("🔧 Fixing database issues...")
    
    try:
        # Import MongoDB connection
        from pymongo import MongoClient
        
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['gd_demon_list']
        
        # Remove Base64 thumbnails (performance killers)
        base64_count = db.levels.count_documents({"thumbnail_url": {"$regex": "^data:"}})
        if base64_count > 0:
            result = db.levels.update_many(
                {"thumbnail_url": {"$regex": "^data:"}},
                {"$set": {"thumbnail_url": ""}}
            )
            print(f"✅ Removed {result.modified_count} Base64 thumbnails")
        
        # Fix YouTube thumbnails
        youtube_levels = list(db.levels.find({
            "video_url": {"$regex": "youtube|youtu.be", "$options": "i"},
            "thumbnail_url": {"$in": ["", None]}
        }))
        
        fixed_youtube = 0
        for level in youtube_levels:
            video_url = level.get('video_url', '')
            if video_url:
                # Extract video ID
                video_id = None
                if 'watch?v=' in video_url:
                    video_id = video_url.split('watch?v=')[1].split('&')[0]
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                
                if video_id:
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                    db.levels.update_one(
                        {"_id": level["_id"]},
                        {"$set": {"thumbnail_url": thumbnail_url}}
                    )
                    fixed_youtube += 1
        
        if fixed_youtube > 0:
            print(f"✅ Fixed {fixed_youtube} YouTube thumbnails")
        
        # Ensure all records have proper timestamps
        records_without_timestamps = db.records.count_documents({
            "date_submitted": {"$exists": False}
        })
        
        if records_without_timestamps > 0:
            db.records.update_many(
                {"date_submitted": {"$exists": False}},
                {"$set": {"date_submitted": datetime.now(timezone.utc)}}
            )
            print(f"✅ Fixed {records_without_timestamps} records without timestamps")
        
        # Ensure all users have points field
        users_without_points = db.users.count_documents({
            "points": {"$exists": False}
        })
        
        if users_without_points > 0:
            db.users.update_many(
                {"points": {"$exists": False}},
                {"$set": {"points": 0}}
            )
            print(f"✅ Fixed {users_without_points} users without points")
        
        # Fix levels without points
        levels_without_points = db.levels.count_documents({
            "points": {"$exists": False}
        })
        
        if levels_without_points > 0:
            # Import the calculate function
            sys.path.append('.')
            try:
                from main import calculate_level_points
                
                for level in db.levels.find({"points": {"$exists": False}}):
                    position = level.get('position', 1)
                    is_legacy = level.get('is_legacy', False)
                    level_type = level.get('level_type', 'Level')
                    points = calculate_level_points(position, is_legacy, level_type)
                    
                    db.levels.update_one(
                        {"_id": level["_id"]},
                        {"$set": {"points": points}}
                    )
                
                print(f"✅ Fixed {levels_without_points} levels without points")
            except ImportError:
                print(f"⚠️ Could not import calculate_level_points, skipping level points fix")
        
        # Fix levels without min_percentage
        levels_without_min_pct = db.levels.count_documents({
            "min_percentage": {"$exists": False}
        })
        
        if levels_without_min_pct > 0:
            db.levels.update_many(
                {"min_percentage": {"$exists": False}},
                {"$set": {"min_percentage": 100}}
            )
            print(f"✅ Fixed {levels_without_min_pct} levels without min_percentage")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False

def fix_static_files():
    """Ensure static directories exist"""
    print("🔧 Fixing static file structure...")
    
    try:
        directories = [
            'static',
            'static/css',
            'static/js',
            'static/images',
            'static/thumbs',
            'instance'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Ensured directory exists: {directory}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing static files: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔧 Checking dependencies...")
    
    required_packages = [
        'flask',
        'pymongo',
        'pillow',
        'requests',
        'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def main():
    """Main fix function"""
    print("🚀 Starting comprehensive fix...")
    print("=" * 50)
    
    success_count = 0
    total_fixes = 4
    
    # Check dependencies first
    if check_dependencies():
        success_count += 1
    
    # Fix static files
    if fix_static_files():
        success_count += 1
    
    # Fix thumbnails
    if fix_thumbnails():
        success_count += 1
    
    # Fix database issues
    if fix_database_issues():
        success_count += 1
    
    print("=" * 50)
    print(f"🎉 Fix complete! {success_count}/{total_fixes} fixes successful")
    
    if success_count == total_fixes:
        print("✅ All systems fixed! You can now:")
        print("   1. Start the application: python main.py")
        print("   2. Visit /fix_thumbnails for additional thumbnail fixes")
        print("   3. Visit /admin for record management")
        print("   4. Visit /test_thumbnails to test the thumbnail system")
    else:
        print("⚠️ Some fixes failed. Check the errors above.")
    
    return success_count == total_fixes

if __name__ == "__main__":
    main()