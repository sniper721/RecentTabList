#!/usr/bin/env python3
"""
Test script to verify the fixes for the reported issues
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    print("🧪 Testing imports...")
    
    try:
        # Test main app imports
        from main import app, mongo_db
        print("✅ Main app imports successful")
        
        # Test changelog discord imports
        from changelog_discord import notify_changelog
        print("✅ Changelog Discord imports successful")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("🧪 Testing database connection...")
    
    try:
        from main import mongo_client
        # Test ping
        mongo_client.admin.command('ping')
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_routes_exist():
    """Test that key routes exist"""
    print("🧪 Testing route definitions...")
    
    try:
        from main import app
        
        # Check if key routes exist
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        required_routes = [
            '/',  # index
            '/level/<level_id>',  # level_detail
            '/admin/levels',  # admin_levels
            '/admin/tools',  # admin_tools
            '/admin/temp_ban',  # new temp_ban route
            '/submit_record'  # submit_record
        ]
        
        missing_routes = []
        for route in required_routes:
            if route not in routes:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ Missing routes: {missing_routes}")
            return False
        else:
            print("✅ All required routes exist")
            return True
            
    except Exception as e:
        print(f"❌ Route test error: {e}")
        return False

def test_temp_ban_function():
    """Test temp ban helper function"""
    print("🧪 Testing temp ban function...")
    
    try:
        from main import is_user_temp_banned
        from bson.objectid import ObjectId
        
        # Test with fake user ID (should return False, None)
        fake_id = ObjectId()
        is_banned, ban_info = is_user_temp_banned(fake_id)
        
        if is_banned == False and ban_info is None:
            print("✅ Temp ban function works correctly")
            return True
        else:
            print(f"❌ Temp ban function returned unexpected result: {is_banned}, {ban_info}")
            return False
            
    except Exception as e:
        print(f"❌ Temp ban function error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting fix verification tests...\n")
    
    tests = [
        test_imports,
        test_database_connection,
        test_routes_exist,
        test_temp_ban_function
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"❌ Test failed with exception: {e}\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes should be working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)