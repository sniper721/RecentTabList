#!/usr/bin/env python3
"""
Test template rendering to see if that's causing the issue
"""

def test_template_render():
    try:
        from main import app
        
        print("🧪 Testing template rendering...")
        
        # Create a test client
        with app.test_client() as client:
            with app.app_context():
                from flask import render_template
                
                # Test data (similar to what index route would use)
                test_levels = [
                    {"_id": 1, "name": "Test Level", "creator": "Test Creator", "verifier": "Test Verifier", "position": 1, "points": 250, "level_id": "12345", "difficulty": 10}
                ]
                
                # Try to render the template
                result = render_template('index.html', 
                                       levels=test_levels,
                                       total_levels=1,
                                       april_fools_active=False)
                
                print(f"✅ Template rendered successfully! Length: {len(result)} characters")
                return True
                
    except Exception as e:
        print(f"❌ Template rendering error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_template_render()