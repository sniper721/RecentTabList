from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from bson.objectid import ObjectId
import functools

# Load environment variables
load_dotenv()

# Configuration
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# MongoDB Configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

print("Initializing MongoDB connection...")
try:
    mongo_client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        socketTimeoutMS=5000,
        connectTimeoutMS=5000
    )
    mongo_db = mongo_client[mongodb_db]
    # Quick test
    mongo_client.admin.command('ping')
    print("✓ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    # Fallback to in-memory data for testing
    mongo_db = None
    print("⚠️ Using fallback mode")

# Simple cache
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None
}

def get_cached_levels(is_legacy=False):
    """Get cached levels with simple timeout"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    last_updated = levels_cache.get('last_updated')
    
    # Cache for 5 minutes
    if last_updated and (datetime.now(timezone.utc) - last_updated).seconds < 300:
        return levels_cache.get(cache_key, [])
    
    return None

def get_main_levels():
    """Get main levels with minimal query"""
    if not mongo_db:
        return [{"_id": 1, "name": "Database Not Available", "creator": "System", "position": 1, "points": 0}]
    
    try:
        # Simple, fast query with limit
        levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"name": 1, "creator": 1, "position": 1, "points": 1}
        ).sort("position", 1).limit(50))  # Limit to 50 for performance
        return levels
    except Exception as e:
        print(f"Error fetching main levels: {e}")
        return [{"_id": 1, "name": "Error Loading Levels", "creator": "System", "position": 1, "points": 0}]

@app.route('/')
def index():
    """Lightweight index route - loads quickly"""
    try:
        # Get cached or fresh data
        main_list = get_cached_levels(is_legacy=False)
        if not main_list:
            main_list = get_main_levels()
            # Cache for next request
            levels_cache['main_list'] = main_list
            levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        return render_template('index_simple.html', 
                             levels=main_list[:20],  # Show only first 20
                             total_levels=min(len(main_list), 50),
                             loading_message="Quick Load - Showing First 20 Levels",
                             mongo_db=mongo_db)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index_simple.html', 
                             levels=[{"_id": 1, "name": "System Error", "creator": "System", "position": 1, "points": 0}],
                             total_levels=1,
                             mongo_db=mongo_db)

@app.route('/test')
def test():
    """Test page to verify server is working"""
    return render_template('test.html', datetime=datetime)

@app.route('/about')
def about():
    """Simple about page"""
    return "<h1>RTL Website - Optimized Version</h1><p>Running successfully!</p><a href='/'>Go to Main Page</a>"

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        if mongo_db:
            mongo_db.command('ping')
            db_status = "Connected"
        else:
            db_status = "Not connected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(datetime.now())
        }, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting optimized server on port {port}")
    print(f"📊 Access the website at: http://localhost:{port}")
    print(f"📈 Health check at: http://localhost:{port}/health")
    app.run(debug=False, host='0.0.0.0', port=port)  # Disable debug for better performance