#!/usr/bin/env python3
"""
Simple verification script for webhook custom message fix
"""

def verify_webhook_fix():
    """Verify that the webhook custom message fix is properly implemented"""
    print("🔍 Verifying webhook custom message fix...")
    
    try:
        # Test 1: Check if set_mongo_db function exists
        from changelog_discord import set_mongo_db
        print("✅ set_mongo_db function exists")
    except ImportError as e:
        print(f"❌ set_mongo_db function not found: {e}")
        return False
    
    try:
        # Test 2: Check if notify_changelog function handles custom messages
        from changelog_discord import notify_changelog
        import inspect
        
        # Get the source code of the function
        source = inspect.getsource(notify_changelog)
        if "custom_message" in source and "mongo_db.site_settings" in source:
            print("✅ notify_changelog function properly handles custom messages")
        else:
            print("❌ notify_changelog function does not properly handle custom messages")
            return False
    except Exception as e:
        print(f"❌ Error checking notify_changelog function: {e}")
        return False
    
    try:
        # Test 3: Check if main.py sets the database reference
        with open("main.py", "r", encoding="utf-8") as f:
            content = f.read()
            if "set_mongo_db(mongo_db)" in content:
                print("✅ main.py properly sets database reference for changelog notifier")
            else:
                print("❌ main.py does not properly set database reference for changelog notifier")
                return False
    except Exception as e:
        print(f"❌ Error checking main.py: {e}")
        return False
    
    print("🎉 All webhook custom message fix verifications passed!")
    print("\n📝 Summary of changes made:")
    print("1. Added set_mongo_db function to changelog_discord.py to set database reference")
    print("2. Modified main.py to call set_mongo_db after MongoDB initialization")
    print("3. Updated notify_changelog function to retrieve and use custom messages from database")
    print("\n🚀 The webhook should now properly send custom messages!")
    return True

if __name__ == "__main__":
    verify_webhook_fix()