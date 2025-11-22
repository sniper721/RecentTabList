#!/usr/bin/env python3
"""
Test script to identify form submission issues
"""

import sys
sys.path.append('.')

def test_form_functions():
    """Test the form handling functions"""
    try:
        from main import app, mongo_db
        
        print("🧪 Testing form handling functions...")
        
        # Test if we can create a test client
        with app.test_client() as client:
            print("✅ Flask test client created successfully")
            
            # Test GET requests to form pages
            print("\n📝 Testing GET requests...")
            
            # Test submit_record GET
            response = client.get('/submit_record')
            print(f"Submit Record GET: {response.status_code}")
            if response.status_code == 302:
                print("  → Redirected (likely to login or instant_load)")
            
            # Test submit_verification GET  
            response = client.get('/submit_verification')
            print(f"Submit Verification GET: {response.status_code}")
            if response.status_code == 302:
                print("  → Redirected (likely to login)")
            
            print("\n🔍 Testing database queries...")
            
            # Test level count
            level_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
            print(f"✅ Main list levels: {level_count}")
            
            # Test if we can get cached levels
            from main import get_cached_levels
            levels = get_cached_levels(is_legacy=False)
            print(f"✅ Cached levels: {len(levels)} levels")
            
            # Test verification submissions collection
            verification_count = mongo_db.verification_submissions.count_documents({})
            print(f"✅ Verification submissions: {verification_count}")
            
            # Test records collection
            record_count = mongo_db.records.count_documents({})
            print(f"✅ Records: {record_count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_functions():
    """Test admin functions"""
    try:
        from main import get_level_neighbors, auto_manage_legacy_list, log_level_change
        
        print("\n🔧 Testing admin functions...")
        
        # Test get_level_neighbors
        above, below = get_level_neighbors(50, False)
        print(f"✅ get_level_neighbors(50): above='{above}', below='{below}'")
        
        print("✅ All admin functions accessible")
        return True
        
    except Exception as e:
        print(f"❌ Admin function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting form issue diagnosis...")
    
    success = True
    success &= test_form_functions()
    success &= test_admin_functions()
    
    if success:
        print("\n✅ All tests passed! The forms should be working.")
        print("\n💡 If you're still having issues, it might be:")
        print("   - JavaScript errors in the browser")
        print("   - Session/authentication issues")
        print("   - Network connectivity problems")
        print("   - Browser cache issues")
    else:
        print("\n❌ Some tests failed. Check the errors above.")