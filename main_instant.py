"""
INSTANT START VERSION - Flask loads immediately, MongoDB connects in background
This is the ULTRA-FAST version that eliminates ALL timeout issues
"""
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timezone
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-in-production-12345')

print("\n" + "="*80)
print("🚀 INSTANT START MODE - Loading Flask IMMEDIATELY")
print("="*80 + "\n")

# Initialize non-blocking MongoDB manager
from mongodb_async import get_mongo_manager, init_mongodb_async

mongo_manager = init_mongodb_async()

# Lazy MongoDB wrapper
class LazyMongoDB:
    def __init__(self, manager):
        self.manager = manager
    
    def __getattr__(self, name):
        db = self.manager.get_db()
        if db is None:
            class DummyCollection:
                def find(self, *args, **kwargs):
                    raise Exception("MongoDB not connected")
                def find_one(self, *args, **kwargs):
                    raise Exception("MongoDB not connected")
                def count_documents(self, *args, **kwargs):
                    return 0
            return DummyCollection()
        return getattr(db, name)

mongo_db = LazyMongoDB(mongo_manager)

# Cache for levels (loaded from JSON initially)
levels_cache = {
    'main_list': [],
    'legacy_list': [],
    'last_updated': None
}

# Pre-load cache from JSON files on startup
def preload_cache():
    """Load cache from JSON files immediately"""
    try:
        # Load main levels cache
        if os.path.exists('cache_main_levels.json'):
            with open('cache_main_levels.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                levels_cache['main_list'] = data.get('levels', [])
                print(f"✅ Pre-loaded {len(levels_cache['main_list'])} main levels from cache")
        
        # Load legacy levels cache
        if os.path.exists('cache_legacy_levels.json'):
            with open('cache_legacy_levels.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                levels_cache['legacy_list'] = data.get('levels', [])
                print(f"✅ Pre-loaded {len(levels_cache['legacy_list'])} legacy levels from cache")
                
    except Exception as e:
        print(f"⚠️ Cache preload failed: {e}")

# Preload cache before starting server
preload_cache()

@app.route('/')
def index():
    """INSTANT LOAD - Uses cache first, database second"""
    try:
        # Always use cache for instant loading
        main_list = levels_cache.get('main_list', [])
        
        # If cache is empty, show message to refresh
        if not main_list or len(main_list) == 0:
            if mongo_manager.is_connected():
                # Connected but empty - try reload
                print("🔄 Cache empty, attempting database reload...")
                try:
                    db = mongo_manager.get_db()
                    if db:
                        cursor = db.levels.find(
                            {"is_legacy": {"$ne": True}},
                            {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1, "difficulty": 1}
                        ).sort("position", 1)
                        cursor.max_time_ms(30000)
                        main_list = list(cursor)
                        levels_cache['main_list'] = main_list
                except Exception as e:
                    print(f"⚠️ Database reload failed: {e}")
            
            if not main_list:
                # Still empty - show waiting message
                main_list = [{
                    "_id": 0,
                    "name": "⏳ Loading levels... Please wait and refresh",
                    "creator": "System",
                    "verifier": "System",
                    "position": 1,
                    "points": 0,
                    "level_id": "loading",
                    "difficulty": 1
                }]
        
        return render_template('index.html', 
                             levels=main_list,
                             total_levels=len(main_list),
                             april_fools_active=False)
                             
    except Exception as e:
        print(f"❌ Index route error: {e}")
        # Fallback to empty state
        return render_template('index.html', 
                             levels=[{
                                 "_id": 0,
                                 "name": "⚠️ Error loading levels - Refresh the page",
                                 "creator": "System",
                                 "position": 1,
                                 "points": 0,
                                 "level_id": "error",
                                 "difficulty": 1
                             }],
                             total_levels=1,
                             april_fools_active=False)

@app.route('/legacy')
def legacy():
    """INSTANT LOAD - Legacy levels"""
    try:
        legacy_list = levels_cache.get('legacy_list', [])
        
        if not legacy_list:
            legacy_list = [{
                "_id": 0,
                "name": "⏳ Loading legacy levels... Please wait and refresh",
                "creator": "System",
                "position": 1,
                "points": 0,
                "level_id": "loading",
                "difficulty": 1
            }]
        
        return render_template('legacy.html', 
                             levels=legacy_list,
                             total_levels=len(legacy_list))
                             
    except Exception as e:
        print(f"❌ Legacy route error: {e}")
        return render_template('legacy.html', 
                             levels=[],
                             total_levels=0)

@app.route('/api/connection-status')
def connection_status():
    """API endpoint to check MongoDB connection status"""
    return jsonify({
        'connected': mongo_manager.is_connected(),
        'cache_loaded': len(levels_cache['main_list']) > 0,
        'main_levels_count': len(levels_cache['main_list']),
        'legacy_levels_count': len(levels_cache['legacy_list'])
    })

@app.route('/admin/refresh-cache', methods=['POST'])
def admin_refresh_cache():
    """Force refresh cache from database (admin only)"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        if not mongo_manager.is_connected():
            return jsonify({'error': 'MongoDB not connected yet'}), 503
        
        db = mongo_manager.get_db()
        
        # Refresh main levels
        cursor = db.levels.find(
            {"is_legacy": {"$ne": True}},
            {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1, "difficulty": 1}
        ).sort("position", 1)
        cursor.max_time_ms(60000)
        levels_cache['main_list'] = list(cursor)
        
        # Refresh legacy levels
        cursor = db.levels.find(
            {"is_legacy": True},
            {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1, "difficulty": 1}
        ).sort("position", 1)
        cursor.max_time_ms(60000)
        levels_cache['legacy_list'] = list(cursor)
        
        levels_cache['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        return jsonify({
            'success': True,
            'main_count': len(levels_cache['main_list']),
            'legacy_count': len(levels_cache['legacy_list']),
            'updated': levels_cache['last_updated']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Start background task to monitor connection and update cache
def background_monitor():
    """Monitor MongoDB connection and update cache when connected"""
    print("\n📡 Starting background MongoDB monitor...")
    
    while True:
        time.sleep(10)  # Check every 10 seconds
        
        if mongo_manager.is_connected() and levels_cache['last_updated'] is None:
            print("\n✨ MongoDB connected! Attempting to refresh cache...")
            try:
                db = mongo_manager.get_db()
                if db:
                    # Auto-refresh cache once connected
                    cursor = db.levels.find(
                        {"is_legacy": {"$ne": True}},
                        {"_id": 1, "name": 1, "creator": 1, "position": 1}
                    ).sort("position", 1)
                    cursor.max_time_ms(60000)
                    levels_cache['main_list'] = list(cursor)
                    
                    cursor = db.levels.find(
                        {"is_legacy": True},
                        {"_id": 1, "name": 1, "creator": 1, "position": 1}
                    ).sort("position", 1)
                    cursor.max_time_ms(60000)
                    levels_cache['legacy_list'] = list(cursor)
                    
                    levels_cache['last_updated'] = datetime.now(timezone.utc).isoformat()
                    
                    print(f"✅ Cache refreshed! Main: {len(levels_cache['main_list'])}, Legacy: {len(levels_cache['legacy_list'])}")
                    
            except Exception as e:
                print(f"⚠️ Cache refresh failed: {e}")

# Start monitor thread
import threading
monitor_thread = threading.Thread(target=background_monitor, daemon=True)
monitor_thread.start()

if __name__ == '__main__':
    print("\n" + "="*80)
    print("✅ SERVER READY - Access at http://localhost:10000")
    print("="*80)
    print("\n📊 Initial Status:")
    print(f"   • Main levels cached: {len(levels_cache['main_list'])}")
    print(f"   • Legacy levels cached: {len(levels_cache['legacy_list'])}")
    print(f"   • MongoDB connected: {mongo_manager.is_connected()}")
    print("\n⏳ MongoDB will connect in background...")
    print("="*80 + "\n")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)
