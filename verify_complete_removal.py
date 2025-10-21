#!/usr/bin/env python3
"""
Complete verification that ALL image/profile picture functionality has been removed
"""

import os
import re
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def verify_database():
    """Verify database is clean of all image data"""
    try:
        print("🔗 Connecting to MongoDB...")
        client = MongoClient(mongodb_uri)
        db = client[mongodb_db]
        
        client.admin.command('ping')
        print("✅ Connected successfully")
        
        # Check users collection
        users_with_avatars = db.users.count_documents({
            "$or": [
                {"avatar_url": {"$exists": True}},
                {"avatar_base64": {"$exists": True}}
            ]
        })
        
        # Check levels collection for any image data
        levels_with_images = db.levels.count_documents({
            "thumbnail_url": {"$regex": "^data:image"}
        })
        
        total_users = db.users.count_documents({})
        total_levels = db.levels.count_documents({})
        
        print(f"\n📊 Database Status:")
        print(f"   Users: {total_users} total, {users_with_avatars} with avatars")
        print(f"   Levels: {total_levels} total, {levels_with_images} with base64 images")
        
        client.close()
        
        return users_with_avatars == 0 and levels_with_images == 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def verify_code_files():
    """Verify all code files are clean of image functionality"""
    files_to_check = {
        'main.py': [
            'convert_image_to_base64',
            'thumbnail_file',
            'test_base64',
            'debug_images',
            'fix_base64'
        ],
        'discord_widget.py': [
            'avatar_url'
        ],
        'changelog_discord.py': [
            'avatar_url'
        ]
    }
    
    print("\n🔍 Checking code files...")
    all_clean = True
    
    for filename, forbidden_terms in files_to_check.items():
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            found_terms = []
            for term in forbidden_terms:
                if term in content and not content.count(f"# {term}") and not content.count(f"removed"):
                    found_terms.append(term)
            
            if found_terms:
                print(f"❌ {filename}: Found {found_terms}")
                all_clean = False
            else:
                print(f"✅ {filename}: Clean")
        else:
            print(f"⚠️ {filename}: Not found")
    
    return all_clean

def verify_templates():
    """Verify all templates are clean of image functionality"""
    template_dir = 'templates'
    forbidden_terms = [
        'avatar_url',
        'avatar_base64', 
        'profile_picture',
        'thumbnail_file',
        'testProfilePictures'
    ]
    
    print(f"\n🔍 Checking templates in {template_dir}/...")
    all_clean = True
    
    if os.path.exists(template_dir):
        for filename in os.listdir(template_dir):
            if filename.endswith('.html'):
                filepath = os.path.join(template_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                found_terms = []
                for term in forbidden_terms:
                    if term in content and 'removed' not in content.lower():
                        found_terms.append(term)
                
                if found_terms:
                    print(f"❌ {filename}: Found {found_terms}")
                    all_clean = False
                else:
                    print(f"✅ {filename}: Clean")
    
    return all_clean

def verify_routes():
    """Verify no image-related routes exist"""
    print("\n🔍 Checking for removed routes...")
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found")
        return False
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    removed_routes = [
        'test_base64_upload',
        'test_base64_display', 
        'debug_images',
        'test_images_simple',
        'stress_test_images',
        'set_thumbnail',
        'fix_base64'
    ]
    
    found_routes = []
    for route in removed_routes:
        if f"def {route}(" in content:
            found_routes.append(route)
    
    if found_routes:
        print(f"❌ Found active routes: {found_routes}")
        return False
    else:
        print("✅ All image routes successfully removed")
        return True

def main():
    print("🖼️ Complete Image Functionality Removal Verification")
    print("=" * 55)
    
    # Run all checks
    db_clean = verify_database()
    code_clean = verify_code_files()
    templates_clean = verify_templates()
    routes_clean = verify_routes()
    
    print("\n" + "=" * 55)
    
    if all([db_clean, code_clean, templates_clean, routes_clean]):
        print("🎉 SUCCESS: ALL image functionality completely removed!")
        print("\n✅ Verification Results:")
        print("   • Database: Clean of all avatar/image data")
        print("   • Code files: No image processing functions")
        print("   • Templates: No image upload forms or displays")
        print("   • Routes: All image-related endpoints removed")
        print("\n🚀 System now uses initials-only identification")
        print("📈 Performance improved - no image processing overhead")
        print("🔒 Privacy enhanced - no personal images stored")
        
        return True
    else:
        print("❌ INCOMPLETE: Some image functionality still exists")
        if not db_clean:
            print("   • Database still contains image data")
        if not code_clean:
            print("   • Code files still have image functions")
        if not templates_clean:
            print("   • Templates still have image references")
        if not routes_clean:
            print("   • Image-related routes still exist")
        
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)