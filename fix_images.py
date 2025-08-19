#!/usr/bin/env python3
"""
Quick fix script to add missing video URLs for image thumbnails
"""

from main import mongo_db

def fix_missing_video_urls():
    """Add missing video URLs for levels that should have images"""
    
    # Video URLs for levels that are showing "Image Error"
    video_urls = {
        'the light circles': 'https://youtu.be/s82TlWCh-V4',
        'old memories': 'https://youtu.be/vVDeEQuQ_pM',
        'ochiru 2': 'https://www.youtube.com/watch?v=sImN3-3e5u0',
        'the ringer': 'https://www.youtube.com/watch?v=3CwTD5RtFDk',
        'los pollos tv 3': 'https://streamable.com/wzux7b',
    }
    
    print("🔧 Fixing missing video URLs...")
    
    for level_name, video_url in video_urls.items():
        # Try exact match first
        result = mongo_db.levels.update_one(
            {"name": level_name, "is_legacy": False},
            {"$set": {"video_url": video_url}}
        )
        
        if result.matched_count > 0:
            if result.modified_count > 0:
                print(f"✅ UPDATED: '{level_name}' → {video_url}")
            else:
                print(f"⚪ UNCHANGED: '{level_name}' (already had URL)")
        else:
            # Try case-insensitive match
            result = mongo_db.levels.update_one(
                {"name": {"$regex": f"^{level_name}$", "$options": "i"}, "is_legacy": False},
                {"$set": {"video_url": video_url}}
            )
            
            if result.matched_count > 0:
                if result.modified_count > 0:
                    print(f"✅ UPDATED (case-insensitive): '{level_name}' → {video_url}")
                else:
                    print(f"⚪ UNCHANGED (case-insensitive): '{level_name}' (already had URL)")
            else:
                print(f"❌ NOT FOUND: '{level_name}'")
    
    print("\n🔍 Checking current state of top 10 levels...")
    
    # Check the current state
    levels = list(mongo_db.levels.find(
        {"is_legacy": False}, 
        {"name": 1, "video_url": 1, "position": 1}
    ).sort("position", 1).limit(10))
    
    for level in levels:
        name = level.get('name', 'Unknown')
        url = level.get('video_url', 'NO URL')
        pos = level.get('position', '?')
        
        # Check if it will have a thumbnail
        has_thumbnail = False
        if url and url != 'NO URL':
            if 'youtube.com' in url or 'youtu.be' in url:
                has_thumbnail = True
                thumbnail_type = "YouTube"
            elif 'streamable.com' in url:
                has_thumbnail = True
                thumbnail_type = "Streamable"
            else:
                thumbnail_type = "Other"
        
        status = f"✅ {thumbnail_type}" if has_thumbnail else "❌ No thumbnail"
        print(f"{pos}. {name}: {status}")
    
    print("\n🎉 Fix complete! Images should now load properly.")

if __name__ == "__main__":
    fix_missing_video_urls()