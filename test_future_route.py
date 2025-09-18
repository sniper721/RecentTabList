import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from main import app
    
    with app.test_request_context():
        url = app.url_for('future_list')
        print(f"future_list URL: {url}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()