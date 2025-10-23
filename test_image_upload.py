#!/usr/bin/env python3
"""
Test script to verify image upload functionality
"""

import os
import sys
import base64
from io import BytesIO

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image():
    """Create a small test image in memory"""
    try:
        from PIL import Image
        
        # Create a small 100x100 red image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Save to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
    except ImportError:
        # Fallback: create a minimal PNG manually
        # This is a 1x1 transparent PNG
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        return png_data

def test_convert_image_to_base64():
    """Test the convert_image_to_base64 function"""
    print("🧪 Testing image conversion function...")
    
    # Import the function from main.py
    try:
        from main import convert_image_to_base64
        print("  ✅ Successfully imported convert_image_to_base64 function")
    except ImportError as e:
        print(f"  ❌ Failed to import function: {e}")
        return False
    
    # Create a mock file object
    class MockFile:
        def __init__(self, data, content_type='image/png', filename='test.png'):
            self.data = data
            self.content_type = content_type
            self.filename = filename
            self.position = 0
        
        def read(self, size=-1):
            if size == -1:
                result = self.data[self.position:]
                self.position = len(self.data)
            else:
                result = self.data[self.position:self.position + size]
                self.position += len(result)
            return result
        
        def seek(self, position, whence=0):
            if whence == 0:  # SEEK_SET
                self.position = position
            elif whence == 1:  # SEEK_CUR
                self.position += position
            elif whence == 2:  # SEEK_END
                self.position = len(self.data) + position
        
        def tell(self):
            return self.position
    
    # Test with valid PNG
    test_image_data = create_test_image()
    mock_file = MockFile(test_image_data, 'image/png', 'test.png')
    
    result = convert_image_to_base64(mock_file)
    
    if result and result.startswith('data:image/png;base64,'):
        print("  ✅ Successfully converted PNG to base64")
        print(f"  📏 Result length: {len(result)} characters")
        return True
    else:
        print(f"  ❌ Conversion failed. Result: {result}")
        return False

def test_file_size_limit():
    """Test file size limit enforcement"""
    print("\n🔒 Testing file size limits...")
    
    try:
        from main import convert_image_to_base64
        
        # Create a large fake file (6MB)
        large_data = b'x' * (6 * 1024 * 1024)
        
        class MockLargeFile:
            def __init__(self):
                self.content_type = 'image/png'
                self.filename = 'large.png'
                self.position = 0
                self.size = len(large_data)
            
            def seek(self, position, whence=0):
                if whence == 2:  # SEEK_END
                    self.position = self.size
                else:
                    self.position = position
            
            def tell(self):
                return self.position
            
            def read(self):
                return large_data
        
        mock_large_file = MockLargeFile()
        result = convert_image_to_base64(mock_large_file)
        
        if result is None:
            print("  ✅ Large file correctly rejected (>5MB)")
            return True
        else:
            print("  ❌ Large file was not rejected")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing file size limit: {e}")
        return False

def test_invalid_file_types():
    """Test invalid file type rejection"""
    print("\n🚫 Testing invalid file type rejection...")
    
    try:
        from main import convert_image_to_base64
        
        class MockInvalidFile:
            def __init__(self, content_type):
                self.content_type = content_type
                self.filename = 'test.txt'
                self.position = 0
                self.data = b'not an image'
            
            def seek(self, position, whence=0):
                if whence == 2:
                    self.position = len(self.data)
                else:
                    self.position = position
            
            def tell(self):
                return self.position
            
            def read(self):
                return self.data
        
        # Test with text file
        mock_text_file = MockInvalidFile('text/plain')
        result = convert_image_to_base64(mock_text_file)
        
        if result is None:
            print("  ✅ Text file correctly rejected")
            return True
        else:
            print("  ❌ Text file was not rejected")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing invalid file types: {e}")
        return False

def check_template_upload_enabled():
    """Check that upload is enabled in templates"""
    print("\n🎨 Checking template upload status...")
    
    try:
        with open('templates/admin/levels.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that upload is not disabled
        if 'id="edit_thumb_upload" value="upload" disabled' in content:
            print("  ❌ Upload is still disabled in edit modal")
            return False
        elif 'id="edit_thumb_upload" value="upload"' in content:
            print("  ✅ Upload enabled in edit modal")
        else:
            print("  ⚠️ Upload option not found in edit modal")
            return False
        
        # Check for file input
        if 'name="thumbnail_file"' in content:
            print("  ✅ File input field present")
        else:
            print("  ❌ File input field missing")
            return False
        
        # Check for proper help text
        if 'JPG, PNG, GIF, WebP' in content:
            print("  ✅ Proper help text present")
        else:
            print("  ❌ Help text missing or incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error checking template: {e}")
        return False

def main():
    """Run all tests"""
    print("🖼️ Image Upload Functionality Test")
    print("=" * 50)
    
    tests = [
        test_convert_image_to_base64,
        test_file_size_limit,
        test_invalid_file_types,
        check_template_upload_enabled
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Image upload should work correctly.")
        print("\n✨ Features enabled:")
        print("  • File upload in Add Level modal")
        print("  • File upload in Edit Level modal")
        print("  • Base64 conversion with size limits")
        print("  • File type validation")
        print("  • Smart thumbnail type detection")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main()