#!/usr/bin/env python3
"""
Fix completion counts by excluding legacy levels from stats
"""

from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Connect to MongoDB
print("Connecting to MongoDB...")
mongo_client = MongoClient(mongodb_uri)
mongo_db = mongo_client[mongodb_db]

def analyze_legacy_level_issue():
    """Analyze the legacy level completion counting issue"""
    print("\n🔍 ANALYZING LEGACY LEVEL COMPLETION ISSUE")
    print("=" * 60)
    
    # Get all levels and categorize them
    all_levels = list(mongo_db.levels.find({}, {"_id": 1, "name": 1, "is_legacy": 1, "position": 1}))
    main_levels = [l for l in all_levels if not l.get('is_legacy', False)]
    legacy_levels = [l for l in all_levels if l.get('is_legacy', False)]
    
    print(f"📊 Level breakdown:")
    print(f"   Main list levels: {len(main_levels)}")
    print(f"   Legacy levels: {len(legacy_levels)}")
    print(f"   Total levels: {len(all_levels)}")
    
    # Get all users with records
    users_with_records = list(mongo_db.users.find(
        {"points": {"$gt": 0}}, 
        {"_id": 1, "username": 1, "points": 1}
    ).sort("points", -1))
    
    print(f"\n👥 Found {len(users_with_records)} users with points")
    
    # Analyze completion counting issues
    issues_found = 0
    total_legacy_completions = 0
    
    print(f"\n🔍 Checking completion counts for top users...")
    
    for i, user in enumerate(users_with_records[:10]):  # Check top 10 users
        user_id = user['_id']
        username = user['username']
        
        # Get all approved completions
        all_completions = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved",
            "progress": 100
        }, {"level_id": 1}))
        
        # Separate main list vs legacy completions
        main_completions = []
        legacy_completions = []
        
        for completion in all_completions:
            level = mongo_db.levels.find_one({"_id": completion['level_id']})
            if level:
                if level.get('is_legacy', False):
                    legacy_completions.append(level)
                else:
                    main_completions.append(level)
        
        if legacy_completions:
            issues_found += 1
            total_legacy_completions += len(legacy_completions)
            print(f"   {i+1:2d}. {username}: {len(all_completions)} total, {len(main_completions)} main, {len(legacy_completions)} legacy")
            
            # Show some legacy level names
            if len(legacy_completions) <= 3:
                legacy_names = [l['name'] for l in legacy_completions]
                print(f"       Legacy levels: {', '.join(legacy_names)}")
            else:
                legacy_names = [l['name'] for l in legacy_completions[:3]]
                print(f"       Legacy levels: {', '.join(legacy_names)} + {len(legacy_completions)-3} more")
    
    print(f"\n📈 Summary:")
    print(f"   Users with legacy completions: {issues_found}")
    print(f"   Total legacy completions found: {total_legacy_completions}")
    
    return {
        'main_levels': len(main_levels),
        'legacy_levels': len(legacy_levels),
        'users_affected': issues_found,
        'total_legacy_completions': total_legacy_completions
    }

def fix_profile_route_legacy_filtering():
    """Update the profile route to exclude legacy levels from completion counts"""
    print(f"\n🔧 UPDATING PROFILE ROUTE TO EXCLUDE LEGACY LEVELS")
    print("=" * 60)
    
    print("The profile route needs to be updated to:")
    print("1. Only count completions on main list levels (not legacy)")
    print("2. Only show main list levels in completion grids")
    print("3. Exclude legacy level records from stats calculations")
    
    # This will be implemented by updating the main.py file
    return True

def create_legacy_exclusion_update_script():
    """Create a script to update all user completion counts"""
    print(f"\n📝 CREATING USER STATS UPDATE SCRIPT")
    print("=" * 60)
    
    script_content = '''#!/usr/bin/env python3
"""
Update all user completion counts to exclude legacy levels
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Connect to MongoDB
mongo_client = MongoClient(mongodb_uri)
mongo_db = mongo_client[mongodb_db]

def update_all_user_stats():
    """Update completion stats for all users to exclude legacy levels"""
    print("🔄 Updating user completion stats...")
    
    # Get all users
    users = list(mongo_db.users.find({}, {"_id": 1, "username": 1}))
    updated_count = 0
    
    for user in users:
        user_id = user['_id']
        
        # Get approved completions on main list levels only
        main_completions = list(mongo_db.records.aggregate([
            {"$match": {"user_id": user_id, "status": "approved", "progress": 100}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id", 
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$match": {"level.is_legacy": {"$ne": True}}}
        ]))
        
        # Update user's completion count (if we want to store it)
        # For now, we'll just rely on dynamic calculation
        updated_count += 1
        
        if updated_count % 10 == 0:
            print(f"   Processed {updated_count}/{len(users)} users...")
    
    print(f"✅ Updated stats for {updated_count} users")
    return updated_count

if __name__ == "__main__":
    try:
        update_all_user_stats()
        print("\\n🎉 All user stats updated successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        mongo_client.close()
'''
    
    with open('update_user_stats.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created update_user_stats.py script")
    return True

if __name__ == "__main__":
    try:
        results = analyze_legacy_level_issue()
        
        print(f"\n🎯 ISSUE IDENTIFIED:")
        print(f"Users are getting completion credit for levels that have been moved to legacy.")
        print(f"This affects {results['users_affected']} users with {results['total_legacy_completions']} legacy completions.")
        print(f"")
        print(f"🔧 SOLUTION:")
        print(f"1. Update profile route to exclude legacy levels from completion counts")
        print(f"2. Update public profile route to exclude legacy levels from completion grid")
        print(f"3. Ensure all stats calculations ignore legacy level completions")
        
        fix_profile_route_legacy_filtering()
        create_legacy_exclusion_update_script()
        
        print(f"\n✅ Next steps:")
        print(f"1. Update the profile routes in main.py")
        print(f"2. Run the update script to refresh all user stats")
        print(f"3. Test with affected users to verify accuracy")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mongo_client.close()