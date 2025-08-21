#!/usr/bin/env python3
"""
Test the simplified image system
"""

import requests

def test_image_urls():
    """Test the YouTube thumbnail URLs we're using"""
    
    test_video_ids = [
        's82TlWCh-V4',  # the light circles
        'vVDeEQuQ_pM',  # old memories
        'sImN3-3e5u0',  # ochiru 2
        '3CwTD5RtFDk',  # the ringer
    ]
    
    print("🧪 Testing simplified image system...")
    print("=" * 50)
    
    for video_id in test_video_ids:
        # Test primary format (hqdefault)
        primary_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        fallback_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        
        try:
            response = requests.head(primary_url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {video_id}: Primary (hqdefault) works")
            else:
                # Test fallback
                response = requests.head(fallback_url, timeout=5)
                if response.status_code == 200:
                    print(f"⚠️ {video_id}: Fallback (mqdefault) works")
                else:
                    print(f"❌ {video_id}: Both formats failed")
                    
        except Exception as e:
            print(f"❌ {video_id}: Network error - {e}")
    
    print("\n🎯 RESULT:")
    print("The simplified system should work much better!")
    print("No more complex JavaScript fallbacks causing issues.")

if __name__ == "__main__":
    test_image_urls()