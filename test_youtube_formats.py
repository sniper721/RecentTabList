#!/usr/bin/env python3
"""
Test different YouTube thumbnail formats to see which ones work
"""

import requests

def test_youtube_formats():
    """Test different YouTube thumbnail formats"""
    
    # Test with a known working YouTube video
    test_video_id = "dQw4w9WgXcQ"  # Rick Roll - always available
    
    formats = [
        ('hqdefault.jpg', 'HQ Default (480x360)'),
        ('mqdefault.jpg', 'MQ Default (320x180)'),
        ('maxresdefault.jpg', 'Max Res (1280x720)'),
        ('sddefault.jpg', 'SD Default (640x480)'),
        ('default.jpg', 'Default (120x90)')
    ]
    
    print(f"🧪 Testing YouTube thumbnail formats for video: {test_video_id}")
    print("=" * 60)
    
    for format_name, description in formats:
        url = f"https://img.youtube.com/vi/{test_video_id}/{format_name}"
        
        try:
            response = requests.head(url, timeout=5)
            content_length = response.headers.get('content-length', '0')
            
            if response.status_code == 200:
                if int(content_length) > 1000:
                    print(f"✅ {format_name}: {description} - {content_length} bytes")
                else:
                    print(f"⚠️ {format_name}: {description} - Too small ({content_length} bytes)")
            else:
                print(f"❌ {format_name}: {description} - HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {format_name}: {description} - Error: {e}")
    
    print("\n🎯 RECOMMENDATION:")
    print("Use 'hqdefault.jpg' as primary, with 'maxresdefault.jpg' as fallback")
    print("This gives the best balance of quality and availability.")

if __name__ == "__main__":
    test_youtube_formats()