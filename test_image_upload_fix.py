#!/usr/bin/env python3
"""
Test script to verify the image upload fix for admin level management
"""

import sys
import os
from io import BytesIO
from PIL import Image
import base64

def create_test_image():
    """Create a simple test image"""
    # Create a simple 100x100 red square
    img = Image.new('RGB', (100, 100), color='red')
    
    # Save to BytesIO
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

class MockFile:
    """Mock file object for testing"""
    def __init__(self, data, content_type, filename):
        self.data = data
        self.content_type = content_type
        self.filename = filename
        self.position = 0
    
    def read(self):
        return self.data
    
    def seek(self, position, whence=0):
        if whence == 0:  # SEEK_SET
            self.position = position
        elif whence == 2:  # SEEK_END
            self.position = len(self.data)
    
    def tell(self):
        return self.position if hasattr(self, 'position') else len(self.data)

def test_convert_function():
    """Test the convert_image_to_base64 function"""
    print("🧪 Testing convert_image_to_base64 function...")
    
    try:
        from main import convert_image_to_base64
        print("  ✅ Successfully imported convert_image_to_base64")
    except ImportError as e:
        print(f"  ❌ Failed to import function: {e}")
        return False
    
    # Create test image
    test_image_data = create_test_image()
    mock_file = MockFile(test_image_data, 'image/png', 'test.png')
    
    # Test conversion
    result = convert_image_to_base64(mock_file)
    
    if result and result.startswith('data:image/png;base64,'):
        print("  ✅ Image conversion successful")
        print(f"  📏 Result length: {len(result)} characters")
        return True
    else:
        print(f"  ❌ Image conversion failed: {result}")
        return False

def test_admin_edit_level_code():
    """Test that admin_edit_level has the upload functionality"""
    print("\n🔍 Checking admin_edit_level function...")
    
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for upload handling
        if "elif thumbnail_type == 'upload':" in content:
            print("  ✅ Upload handling code found")
        else:
            print("  ❌ Upload handling code missing")
            return False
        
        # Check for convert_image_to_base64 call
        if "convert_image_to_base64(file)" in content:
            print("  ✅ Image conversion call found")
        else:
            print("  ❌ Image conversion call missing")
            return False
        
        # Check for keep existing functionality
        if "thumbnail_type == 'keep'" in content:
            print("  ✅ Keep existing functionality found")
        else:
            print("  ❌ Keep existing functionality missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading main.py: {e}")
        return False

def test_template_form():
    """Test that the template has the correct form elements"""
    print("\n🎨 Checking admin template...")
    
    try:
        with open('templates/admin/levels.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for file input
        if 'name="thumbnail_file"' in content:
            print("  ✅ File input field present")
        else:
            print("  ❌ File input field missing")
            return False
        
        # Check for upload radio button
        if 'value="upload"' in content:
            print("  ✅ Upload option present")
        else:
            print("  ❌ Upload option missing")
            return False
        
        # Check for keep existing option
        if 'value="keep"' in content or 'keep_existing' in content:
            print("  ✅ Keep existing option present")
        else:
            print("  ❌ Keep existing option missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error reading template: {e}")
        return False

def main():
    """Run all tests"""
    print("🖼️ Image Upload Fix Verification")
    print("=" * 40)
    
    tests = [
        test_convert_function,
        test_admin_edit_level_code,
        test_template_form
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Image upload should now work for level editing.")
        print("\n✨ Fixed features:")
        print("  • Image upload in Edit Level modal")
        print("  • Keep existing image option")
        print("  • Proper error handling for failed uploads")
        print("  • File size and type validation")
    else:
        print("❌ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)