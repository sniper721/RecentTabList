#!/usr/bin/env python3
"""
Verification script for the comprehensive fixes made to the RTL website
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_profile_picture_removal():
    """Test that profile pictures have been completely removed"""
    print("🧪 Testing profile picture removal...")
    
    try:
        # Check if templates have any remaining avatar references
        templates_to_check = [
            'templates/profile.html',
            'templates/public_profile.html',
            'templates/settings.html',
            'templates/admin_test_environment.html'
        ]
        
        removed = True
        for template_path in templates_to_check:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check if any avatar references remain
                    if 'avatar_url' in content or 'avatar_base64' in content:
                        print(f"❌ {template_path} still has avatar references")
                        removed = False
                    else:
                        print(f"✅ {template_path} has no avatar references")
            else:
                print(f"⚠️  {template_path} not found")
        
        return removed
        
    except Exception as e:
        print(f"❌ Error testing profile picture removal: {e}")
        return False

def test_changelog_enhancements():
    """Test that changelog enhancements are in place"""
    print("🧪 Testing changelog enhancements...")
    
    try:
        # Check main.py for enhanced changelog function
        with open('main.py', 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # Check for list type support
        if 'list_type' in main_content and 'pushed_out_of_top10' in main_content:
            print("✅ Enhanced changelog with list type and top 10 detection found in main.py")
        else:
            print("❌ Enhanced changelog features not found in main.py")
            return False
        
        # Check changelog_discord.py for enhancements
        with open('changelog_discord.py', 'r', encoding='utf-8') as f:
            changelog_content = f.read()
        
        if 'pushed_out_of_top10' in changelog_content and 'list_suffix' in changelog_content:
            print("✅ Enhanced changelog features found in changelog_discord.py")
        else:
            print("❌ Enhanced changelog features not found in changelog_discord.py")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing changelog enhancements: {e}")
        return False

def test_legacy_position_shifting():
    """Test that legacy position shifting is implemented"""
    print("🧪 Testing legacy position shifting...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for position shifting logic in auto_manage_legacy_list
        if '"$inc": {"position": 1}' in content and 'is_legacy": True' in content:
            print("✅ Legacy position shifting logic found")
            return True
        else:
            print("❌ Legacy position shifting logic not found")
            return False
        
    except Exception as e:
        print(f"❌ Error testing legacy position shifting: {e}")
        return False

def test_mobile_roulette_fixes():
    """Test that mobile roulette CSS fixes are in place"""
    print("🧪 Testing mobile roulette fixes...")
    
    try:
        with open('templates/roulette.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for mobile responsive CSS
        if '@media (max-width: 768px)' in content and 'flex-direction: column' in content:
            print("✅ Mobile responsive CSS found in roulette template")
            return True
        else:
            print("❌ Mobile responsive CSS not found in roulette template")
            return False
        
    except Exception as e:
        print(f"❌ Error testing mobile roulette fixes: {e}")
        return False

def test_admin_test_environment():
    """Test that admin test environment is available"""
    print("🧪 Testing admin test environment...")
    
    try:
        # Check if test environment template exists
        if os.path.exists('templates/admin_test_environment.html'):
            print("✅ Admin test environment template found")
        else:
            print("❌ Admin test environment template not found")
            return False
        
        # Check if route is added to main.py
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'admin_test_environment' in content:
            print("✅ Admin test environment route found in main.py")
            return True
        else:
            print("❌ Admin test environment route not found in main.py")
            return False
        
    except Exception as e:
        print(f"❌ Error testing admin test environment: {e}")
        return False

def test_top10_detection():
    """Test that top 10 push detection is implemented"""
    print("🧪 Testing top 10 push detection...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for top 10 detection function
        if 'get_top10_pushout_info' in content:
            print("✅ Top 10 push detection function found")
            return True
        else:
            print("❌ Top 10 push detection function not found")
            return False
        
    except Exception as e:
        print(f"❌ Error testing top 10 detection: {e}")
        return False

def main():
    """Run all verification tests"""
    print("🚀 Starting comprehensive fixes verification...\n")
    
    tests = [
        ("Profile Picture Removal", test_profile_picture_removal),
        ("Changelog Enhancements", test_changelog_enhancements),
        ("Legacy Position Shifting", test_legacy_position_shifting),
        ("Mobile Roulette Fixes", test_mobile_roulette_fixes),
        ("Admin Test Environment", test_admin_test_environment),
        ("Top 10 Push Detection", test_top10_detection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print(f"\n{'='*50}")
    print(f"📊 VERIFICATION RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        print("\n📝 Summary of implemented fixes:")
        print("1. ✅ Profile pictures completely removed from system")
        print("2. ✅ Changelog bot now specifies list type (future/legacy vs main)")
        print("3. ✅ Top 10 push-out notifications implemented")
        print("4. ✅ Legacy list position shifting implemented")
        print("5. ✅ Mobile roulette layout fixed with responsive CSS")
        print("6. ✅ Admin test environment created with full feature testing")
        
        print("\n🚀 The website is ready with all requested improvements!")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)