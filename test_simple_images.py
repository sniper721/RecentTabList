#!/usr/bin/env python3
"""
Test the simplest possible YouTube thumbnail approach
"""

import requests

def test_simple_thumbnails():
    """Test the default.jpg format which should always work"""
    
    # Test with actual video IDs from your database
    test_videos = [
        's82TlWCh-V4',  # the light circles
        'vVDeEQuQ_pM',  # old memories
        'sImN3-3e5u0',  # ochiru 2
        '3CwTD5RtFDk',  # the ringer
        'dQw4w9WgXcQ',  # Rick Roll (known working)
    ]
    
    print("🧪 Testing default.jpg format (most reliable)...")
    print("=" * 50)
    
    for video_id in test_videos:
        url = f"https://img.youtube.com/vi/{video_id}/default.jpg"
        
        try:
            response = requests.head(url, timeout=5)
            content_length = response.headers.get('content-length', '0')
            
            if response.status_code == 200:
                print(f"✅ {video_id}: OK ({content_length} bytes)")
            else:
                print(f"❌ {video_id}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {video_id}: Error - {e}")
    
    print("\n🎯 RESULT:")
    print("If all show ✅, then the template should work!")
    print("The template uses the exact same URLs.")

if __name__ == "__main__":
    test_simple_thumbnails()