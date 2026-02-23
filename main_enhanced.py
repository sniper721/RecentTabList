"""
Enhanced main.py with improved MongoDB connection handling
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from bson.objectid import ObjectId
import functools
import time

# Load environment variables
load_dotenv()

# Import enhanced MongoDB connector
try:
    from mongodb_connector import get_mongodb_connection
    print("✅ Enhanced MongoDB connector loaded")
except ImportError as e:
    print(f"❌ Failed to load MongoDB connector: {e}")
    # Fallback function
    def get_mongodb_connection():
        return None, None

# Configuration
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize MongoDB with enhanced connection
print("🔄 Initializing enhanced MongoDB connection...")
mongo_client, mongo_db = get_mongodb_connection()

if mongo_client is not None and mongo_db is not None:
    print("✅ MongoDB connected successfully")
    # Create indexes for better performance
    try:
        mongo_db.levels.create_index([("is_legacy", 1), ("position", 1)])
        print("✅ Database indexes created")
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")
else:
    print("⚠️ MongoDB connection failed - using fallback mode")

# Simple cache system
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None
}

def get_cached_levels(is_legacy=False):
    """Get cached levels with timeout"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    last_updated = levels_cache.get('last_updated')
    
    # Cache for 5 minutes
    if last_updated and (datetime.now(timezone.utc) - last_updated).seconds < 300:
        return levels_cache.get(cache_key, [])
    
    return None

def get_main_levels():
    """Get main levels with fallback options"""
    if mongo_db is None:
        # Fallback data when no database connection
        return [
            {"_id": 1, "name": "Database Connection Failed", "creator": "System", "position": 1, "points": 0, "difficulty": 5},
            {"_id": 2, "name": "Using Fallback Data", "creator": "System", "position": 2, "points": 0, "difficulty": 4},
            {"_id": 3, "name": "Please Check MongoDB", "creator": "System", "position": 3, "points": 0, "difficulty": 3}
        ]
    
    try:
        # Fast query with limit and minimal fields
        levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"name": 1, "creator": 1, "position": 1, "points": 1, "difficulty": 1}
        ).sort("position", 1).limit(30))  # Limit to 30 for performance
        
        if not levels:
            # If no levels found, return sample data
            return [
                {"_id": 1, "name": "No Levels Found", "creator": "System", "position": 1, "points": 0, "difficulty": 5}
            ]
            
        return levels
    except Exception as e:
        print(f"❌ Error fetching main levels: {e}")
        return [
            {"_id": 1, "name": "Error Loading Levels", "creator": "System", "position": 1, "points": 0, "difficulty": 5}
        ]

@app.route('/')
def index():
    """Enhanced index route with better error handling"""
    try:
        # Get cached or fresh data
        main_list = get_cached_levels(is_legacy=False)
        if not main_list:
            main_list = get_main_levels()
            # Update cache
            levels_cache['main_list'] = main_list
            levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        # Determine connection status message
        if mongo_db is not None:
            status_message = "Connected to Database"
        else:
            status_message = "Database Connection Failed - Using Fallback Data"
        
        return render_template('index_simple.html', 
                             levels=main_list[:20],  # Show only first 20
                             total_levels=min(len(main_list), 30),
                             loading_message=f"Fast Load - {status_message}",
                             mongo_db=mongo_db is not None)
    except Exception as e:
        print(f"❌ Error in index route: {e}")
        return render_template('index_simple.html', 
                             levels=[{"_id": 1, "name": "System Error", "creator": "System", "position": 1, "points": 0}],
                             total_levels=1,
                             loading_message="System Error - Please Check Console",
                             mongo_db=False)

@app.route('/health')
def health():
    """Enhanced health check with detailed information"""
    try:
        # Check MongoDB connection
        if mongo_db is not None:
            try:
                mongo_client.admin.command('ping', maxTimeMS=2000)
                db_status = "Connected"
                db_details = "MongoDB Atlas connection working"
            except Exception as e:
                db_status = "Connected but Unresponsive"
                db_details = f"Ping failed: {str(e)[:50]}..."
        else:
            db_status = "Not Connected"
            db_details = "Using fallback mode"
        
        # Check basic app functionality
        try:
            test_levels = get_main_levels()[:3]
            app_status = "Functional"
            app_details = f"Can load {len(test_levels)} test levels"
        except Exception as e:
            app_status = "Degraded"
            app_details = f"Level loading failed: {str(e)[:50]}..."
        
        return {
            "status": "healthy" if (db_status != "Not Connected" or app_status == "Functional") else "degraded",
            "database": {
                "status": db_status,
                "details": db_details
            },
            "application": {
                "status": app_status,
                "details": app_details
            },
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(datetime.now())
        }, 500

@app.route('/test')
def test():
    """Enhanced test page"""
    return render_template('test.html', datetime=datetime)

@app.route('/about')
def about():
    """Simple about page"""
    return "<h1>RTL Website - Enhanced Version</h1><p>Running with improved MongoDB connection!</p><a href='/'>Go to Main Page</a>"

@app.route('/reconnect')
def reconnect():
    """Manual reconnect endpoint"""
    global mongo_client, mongo_db
    try:
        print("🔄 Attempting manual MongoDB reconnection...")
        mongo_client, mongo_db = get_mongodb_connection()
        if mongo_client is not None and mongo_db is not None:
            return {"status": "success", "message": "MongoDB reconnected successfully"}
        else:
            return {"status": "failed", "message": "MongoDB reconnection failed"}
    except Exception as e:
        return {"status": "error", "message": f"Reconnection error: {str(e)}"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Starting enhanced RTL server on port {port}")
    print(f"📊 Main website: http://localhost:{port}")
    print(f"📈 Health check: http://localhost:{port}/health")
    print(f"🧪 Test page: http://localhost:{port}/test")
    print(f"🔄 Reconnect: http://localhost:{port}/reconnect")
    print("💡 Tip: Use /health endpoint to check connection status")
    
    app.run(debug=False, host='0.0.0.0', port=port)