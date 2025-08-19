#!/usr/bin/env python3
"""
Test script to verify image extraction logic
"""

def test_video_id_extraction():
    """Test the video ID extraction logic"""
    
    test_urls = [
        'https://youtu.be/s82TlWCh-V4',
        'https://youtu.be/vVDeEQuQ_pM',
        'https://www.youtube.com/watch?v=sImN3-3e5u0',
        'https://www.youtube.com/watch?v=3CwTD5RtFDk',
        'https://streamable.com/wzux7b',
    ]
    
    print("🧪 Testing video ID extraction...")
    
    for url in test_urls:
        print(f"\nURL: {url}")
        
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            print(f"  ✅ YouTube (youtu.be) ID: {video_id}")
            print(f"  📷 Thumbnail: {thumbnail_url}")
            
        elif 'youtube.com' in url and 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            print(f"  ✅ YouTube (youtube.com) ID: {video_id}")
            print(f"  📷 Thumbnail: {thumbnail_url}")
            
        elif 'streamable.com' in url:
            video_id = url.split('/')[-1]
            thumbnail_url = f"https://cdn-cf-east.streamable.com/image/{video_id}.jpg"
            print(f"  ✅ Streamable ID: {video_id}")
            print(f"  📷 Thumbnail: {thumbnail_url}")
            
        else:
            print(f"  ❌ Unknown platform")

if __name__ == "__main__":
    test_video_id_extraction()