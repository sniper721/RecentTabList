"""
Ultra-Fast RTL Website - Minimal Version
Loads instantly with sample data
"""
from flask import Flask, render_template, jsonify
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fast-rtl-key')

# Sample data - loads instantly
SAMPLE_LEVELS = [
    {"position": 1, "name": "Slaughterhouse", "creator": "Riot", "verifier": "Riot", "points": 162.1, "difficulty": 5},
    {"position": 2, "name": "Bloodbath", "creator": "Riot", "verifier": "Riot", "points": 150.3, "difficulty": 5},
    {"position": 3, "name": "Havoc", "creator": "Riot", "verifier": "Riot", "points": 139.8, "difficulty": 5},
    {"position": 4, "name": "Cataclysm", "creator": "Riot", "verifier": "Riot", "points": 129.4, "difficulty": 5},
    {"position": 5, "name": "Deadlocked", "creator": "Riot", "verifier": "Riot", "points": 120.1, "difficulty": 5},
    {"position": 6, "name": "Fingerbang", "creator": "Riot", "verifier": "Riot", "points": 112.3, "difficulty": 5},
    {"position": 7, "name": "Theory of Everything 2", "creator": "Riot", "verifier": "Riot", "points": 104.6, "difficulty": 5},
    {"position": 8, "name": "Blast Processing", "creator": "Riot", "verifier": "Riot", "points": 97.4, "difficulty": 5},
    {"position": 9, "name": "Better Day", "creator": "MasKrime", "verifier": "Riot", "points": 90.3, "difficulty": 5},
    {"position": 10, "name": "Sweet Sonata", "creator": "Riot", "verifier": "Riot", "points": 83.7, "difficulty": 5},
    {"position": 11, "name": "Stalemate", "creator": "Riot", "verifier": "Riot", "points": 77.2, "difficulty": 5},
    {"position": 12, "name": "Acropolix", "creator": "Riot", "verifier": "Riot", "points": 71.3, "difficulty": 5},
    {"position": 13, "name": "Jawbreaker", "creator": "Riot", "verifier": "Riot", "points": 65.8, "difficulty": 5},
    {"position": 14, "name": "Speedrun", "creator": "Riot", "verifier": "Riot", "points": 60.4, "difficulty": 5},
    {"position": 15, "name": "Cadrega City", "creator": "Riot", "verifier": "Riot", "points": 55.6, "difficulty": 5},
    {"position": 16, "name": "Clubstep", "creator": "Riot", "verifier": "Riot", "points": 51.1, "difficulty": 5},
    {"position": 17, "name": "Theory of Everything", "creator": "Riot", "verifier": "Riot", "points": 46.8, "difficulty": 5},
    {"position": 18, "name": "Electroman Adventures", "creator": "Riot", "verifier": "Riot", "points": 42.7, "difficulty": 4},
    {"position": 19, "name": "Hexagon Force", "creator": "Riot", "verifier": "Riot", "points": 38.9, "difficulty": 4},
    {"position": 20, "name": "Polargeist", "creator": "Riot", "verifier": "Riot", "points": 35.3, "difficulty": 4}
]

@app.route('/')
def index():
    """Ultra-fast index - loads sample data instantly"""
    return render_template('index_simple.html', 
                         levels=SAMPLE_LEVELS,
                         total_levels=len(SAMPLE_LEVELS),
                         loading_message="⚡ Ultra-Fast Load - Sample Data",
                         mongo_db=False)

@app.route('/health')
def health():
    """Simple health check"""
    return jsonify({
        "status": "healthy",
        "database": "Not connected (using sample data)",
        "levels": len(SAMPLE_LEVELS),
        "timestamp": str(datetime.now())
    })

@app.route('/test')
def test():
    """Test page"""
    return render_template('test.html', datetime=datetime)

@app.route('/about')
def about():
    return "<h1>RTL Website - Ultra-Fast Version</h1><p>Loading instantly with sample data!</p><a href='/'>Go to Main Page</a>"

@app.route('/debug_db')
def debug_db():
    """Database debug info"""
    return """
    <h1>Database Debug Information</h1>
    <p><strong>Status:</strong> Using sample data for fast loading</p>
    <p><strong>Reason:</strong> MongoDB connection issues detected</p>
    <p><strong>Solution:</strong> Website is working with sample data while database issues are resolved</p>
    <p><a href='/'>Return to Main Page</a></p>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 Starting ULTRA-FAST RTL Server")
    print("⚡ Loading sample data instantly")
    print(f"🌐 Website: http://localhost:{port}")
    print(f"📊 Health: http://localhost:{port}/health")
    print(f"🧪 Test: http://localhost:{port}/test")
    print(f"🐛 Debug: http://localhost:{port}/debug_db")
    print("💡 This version loads instantly with sample data!")
    
    app.run(debug=False, host='0.0.0.0', port=port)