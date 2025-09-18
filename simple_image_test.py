#!/usr/bin/env python3
"""
Simple test to verify the image system works
"""

def test_youtube_extraction():
    """Test YouTube ID extraction"""
    
    test_urls = [
        'https://youtu.be/s82TlWCh-V4',
        'https://youtu.be/vVDeEQuQ_pM', 
        'https://www.youtube.com/watch?v=sImN3-3e5u0',
        'https://www.youtube.com/watch?v=3CwTD5RtFDk',
    ]
    
    print("🧪 Testing YouTube ID extraction...")
    
    for url in test_urls:
        youtube_id = ''
        
        if 'youtu.be/' in url:
            youtube_id = url.split('youtu.be/')[1].split('?')[0].split('&')[0]
        elif 'youtube.com/watch?v=' in url:
            youtube_id = url.split('v=')[1].split('&')[0]
        
        if youtube_id:
            thumbnail_url = f"https://img.youtube.com/vi/{youtube_id}/mqdefault.jpg"
            print(f"✅ {url}")
            print(f"   ID: {youtube_id}")
            print(f"   Thumbnail: {thumbnail_url}")
        else:
            print(f"❌ {url} - No ID extracted")
        print()

if __name__ == "__main__":
    test_youtube_extraction()
    print("🎯 This is the exact logic used in the template!")
    print("If this works, the website images should work too.")