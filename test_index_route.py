#!/usr/bin/env python3
"""
Test the index route to see what's causing the error
"""

def test_index_route():
    try:
        from main import app, mongo_db, levels_cache, get_cached_levels, is_april_fools_active
        from datetime import datetime, timezone
        
        print("🧪 Testing index route components...")
        
        # Test 1: get_cached_levels
        print("1. Testing get_cached_levels...")
        cached = get_cached_levels(is_legacy=False)
        print(f"   Cached levels: {len(cached) if cached else 'None'}")
        
        # Test 2: Database query (the auto-load part)
        print("2. Testing database auto-load query...")
        main_list = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1).limit(200))
        print(f"   Query result: {len(main_list)} levels")
        
        # Test 3: Cache update
        print("3. Testing cache update...")
        levels_cache['main_list'] = main_list
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        print(f"   Cache updated successfully")
        
        # Test 4: April fools check
        print("4. Testing April fools check...")
        april_fools = is_april_fools_active()
        print(f"   April fools active: {april_fools}")
        
        # Test 5: Template rendering (simulate)
        print("5. Testing template data preparation...")
        total_levels = len(main_list)
        template_data = {
            'levels': main_list,
            'total_levels': total_levels,
            'april_fools_active': april_fools
        }
        print(f"   Template data prepared: {len(template_data['levels'])} levels, total: {template_data['total_levels']}")
        
        print("✅ All index route components working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error in index route test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_index_route()