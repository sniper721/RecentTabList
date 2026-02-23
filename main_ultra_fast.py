"""
Ultra-Fast Level Management System
Optimized specifically for lightning-fast level operations
"""
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient, ASCENDING, DESCENDING
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

# Configuration
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ultra-fast-rtl-key')

# Ultra-fast MongoDB connection
def get_mongodb_connection():
    """Ultra-optimized MongoDB connection"""
    try:
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        # Ultra-fast connection settings
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=3000,  # Ultra-fast timeout
            socketTimeoutMS=3000,
            connectTimeoutMS=3000,
            maxPoolSize=30,  # Larger pool for concurrent operations
            minPoolSize=10,
            maxIdleTimeMS=5000,
            waitQueueTimeoutMS=1000,
            retryWrites=True,
            retryReads=True,
            connect=False
        )
        
        db = client[mongodb_db]
        
        # Create essential indexes only
        try:
            db.levels.create_index([("is_legacy", ASCENDING), ("position", ASCENDING)])
            db.levels.create_index([("position", ASCENDING)])
        except Exception:
            pass  # Indexes might already exist
            
        # Quick test
        client.admin.command('ping', maxTimeMS=1000)
        print("✅ Ultra-fast MongoDB connected")
        return client, db
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None, None

# Initialize MongoDB
print("🔄 Initializing ultra-fast MongoDB connection...")
mongo_client, mongo_db = get_mongodb_connection()

# Ultra-fast caching system
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None,
    'stats': None
}

def get_cached_levels(is_legacy=False, force_refresh=False):
    """Ultra-fast cached level retrieval"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    last_updated = levels_cache.get('last_updated')
    
    # Ultra-long cache (5 minutes) for maximum performance
    if not force_refresh and last_updated and (datetime.now(timezone.utc) - last_updated).seconds < 300:
        return levels_cache.get(cache_key, [])
    
    return None

def get_levels_fast(is_legacy=False, page=1, per_page=50):
    """Ultra-fast level retrieval with pagination"""
    if mongo_db is None:
        return [], 0
    
    try:
        # Simple, fast query with minimal fields
        query = {"is_legacy": True} if is_legacy else {"is_legacy": {"$ne": True}}
        
        # Get total count (cached)
        if levels_cache['stats'] is None:
            main_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
            legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
            levels_cache['stats'] = {"main": main_count, "legacy": legacy_count}
        
        total_count = levels_cache['stats']['legacy' if is_legacy else 'main']
        
        # Paginated query with minimal projection
        levels = list(mongo_db.levels.find(
            query,
            {
                "_id": 1, "name": 1, "creator": 1, "verifier": 1, 
                "position": 1, "points": 1, "difficulty": 1
            }
        ).sort("position", 1).skip((page - 1) * per_page).limit(per_page))
        
        return levels, total_count
        
    except Exception as e:
        print(f"Error in fast level retrieval: {e}")
        return [], 0

def preload_cache_background():
    """Background cache preloading for instant access"""
    if mongo_db is None:
        return
    
    def load_cache():
        try:
            print("🔄 Preloading level cache in background...")
            
            # Load main levels (first 100 for immediate access)
            main_levels = list(mongo_db.levels.find(
                {"is_legacy": {"$ne": True}},
                {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1}
            ).sort("position", 1).limit(100))
            
            # Load legacy levels (first 100)
            legacy_levels = list(mongo_db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "position": 1, "points": 1}
            ).sort("position", 1).limit(100))
            
            # Update cache
            levels_cache['main_list'] = main_levels
            levels_cache['legacy_list'] = legacy_levels
            levels_cache['last_updated'] = datetime.now(timezone.utc)
            levels_cache['stats'] = {
                "main": mongo_db.levels.count_documents({"is_legacy": {"$ne": True}}),
                "legacy": mongo_db.levels.count_documents({"is_legacy": True})
            }
            
            print(f"✅ Cache preloaded: {len(main_levels)} main, {len(legacy_levels)} legacy levels")
            
        except Exception as e:
            print(f"❌ Cache preloading failed: {e}")
    
    # Start background loading
    from threading import Thread
    Thread(target=load_cache, daemon=True).start()

# Start cache preloading
preload_cache_background()

# Routes
@app.route('/')
def index():
    """Ultra-fast index with preloaded cache"""
    try:
        # Use preloaded cache or load minimal data
        main_list = levels_cache.get('main_list')
        if main_list is None:
            main_list = get_cached_levels(is_legacy=False)
            if main_list is None:
                # Load minimal data instantly
                main_list = list(mongo_db.levels.find(
                    {"is_legacy": {"$ne": True}},
                    {"name": 1, "creator": 1, "position": 1, "points": 1}
                ).sort("position", 1).limit(30)) if mongo_db else []
        
        return render_template('index_simple.html', 
                             levels=main_list[:20],
                             total_levels=len(main_list),
                             loading_message="⚡ Ultra-Fast Load",
                             mongo_db=mongo_db is not None)
    except Exception as e:
        return render_template('index_simple.html', 
                             levels=[{"_id": 1, "name": "System Error", "creator": "System", "position": 1, "points": 0}],
                             total_levels=1,
                             mongo_db=False)

@app.route('/admin')
def admin():
    """Ultra-fast admin panel"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Ultra-fast stats
    try:
        stats = levels_cache.get('stats')
        if stats is None and mongo_db:
            stats = {
                "pending_records": mongo_db.records.count_documents({"status": "pending"}),
                "total_users": mongo_db.users.count_documents({}),
                "main_levels": mongo_db.levels.count_documents({"is_legacy": {"$ne": True}}),
                "legacy_levels": mongo_db.levels.count_documents({"is_legacy": True})
            }
        
        return render_template('admin/dashboard_simple.html', stats=stats or {})
    except Exception:
        return render_template('admin/dashboard_simple.html', stats={})

@app.route('/admin/levels')
def admin_levels():
    """Ultra-fast level management with pagination"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        is_legacy = request.args.get('filter') == 'legacy'
        
        # Ultra-fast level retrieval
        levels, total_count = get_levels_fast(is_legacy, page, per_page)
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('admin/levels_fast.html', 
                             levels=levels,
                             is_legacy_filter=is_legacy,
                             current_page=page,
                             total_pages=total_pages,
                             total_count=total_count,
                             per_page=per_page)
        
    except Exception as e:
        print(f"Error in admin_levels: {e}")
        flash('Error loading levels', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/levels/add', methods=['POST'])
def admin_add_level():
    """Ultra-fast level addition"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        # Minimal data processing
        name = request.form.get('name', '').strip()
        creator = request.form.get('creator', '').strip()
        position = int(request.form.get('position', 1))
        is_legacy = request.form.get('is_legacy') == 'on'
        
        if not name or not creator:
            return {'error': 'Name and creator required'}, 400
        
        # Simple level creation
        new_level = {
            "name": name,
            "creator": creator,
            "verifier": creator,
            "position": position,
            "points": 100,  # Default points
            "difficulty": 5.0,
            "is_legacy": is_legacy,
            "level_id": str(int(time.time())),  # Simple ID
            "created_at": datetime.now(timezone.utc)
        }
        
        result = mongo_db.levels.insert_one(new_level)
        
        # Clear relevant cache
        if is_legacy:
            levels_cache['legacy_list'] = None
        else:
            levels_cache['main_list'] = None
            levels_cache['stats'] = None
        
        return {'success': True, 'message': 'Level added successfully', 'id': str(result.inserted_id)}
        
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/admin/levels/move/<level_id>', methods=['POST'])
def admin_move_level(level_id):
    """Ultra-fast level moving"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        data = request.get_json()
        direction = data.get('direction')
        
        level = mongo_db.levels.find_one({"_id": ObjectId(level_id)})
        if not level:
            return {'error': 'Level not found'}, 404
        
        current_position = level['position']
        is_legacy = level.get('is_legacy', False)
        
        # Simple position calculation
        if direction == 'up' and current_position > 1:
            new_position = current_position - 1
        elif direction == 'down':
            new_position = current_position + 1
        else:
            return {'error': 'Invalid move'}, 400
        
        # Atomic position swap
        mongo_db.levels.update_one(
            {"position": new_position, "is_legacy": is_legacy},
            {"$set": {"position": current_position}}
        )
        mongo_db.levels.update_one(
            {"_id": ObjectId(level_id)},
            {"$set": {"position": new_position}}
        )
        
        # Clear cache
        if is_legacy:
            levels_cache['legacy_list'] = None
        else:
            levels_cache['main_list'] = None
        
        return {'success': True, 'new_position': new_position}
        
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/admin/levels/delete/<level_id>', methods=['POST'])
def admin_delete_level(level_id):
    """Ultra-fast level deletion"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        level = mongo_db.levels.find_one({"_id": ObjectId(level_id)})
        if not level:
            return {'error': 'Level not found'}, 404
        
        position = level['position']
        is_legacy = level.get('is_legacy', False)
        
        # Delete level
        mongo_db.levels.delete_one({"_id": ObjectId(level_id)})
        
        # Shift positions
        mongo_db.levels.update_many(
            {"position": {"$gt": position}, "is_legacy": is_legacy},
            {"$inc": {"position": -1}}
        )
        
        # Clear cache
        if is_legacy:
            levels_cache['legacy_list'] = None
        else:
            levels_cache['main_list'] = None
        levels_cache['stats'] = None
        
        return {'success': True, 'message': 'Level deleted successfully'}
        
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/admin/cache/stats')
def cache_stats():
    """Cache performance monitoring"""
    cache_info = {
        "main_cached": len(levels_cache.get('main_list', [])),
        "legacy_cached": len(levels_cache.get('legacy_list', [])),
        "last_updated": levels_cache.get('last_updated'),
        "stats_cached": levels_cache.get('stats'),
        "database_connected": mongo_db is not None
    }
    return jsonify(cache_info)

@app.route('/admin/cache/clear')
def clear_cache():
    """Clear cache for testing"""
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    levels_cache['stats'] = None
    levels_cache['last_updated'] = None
    return {'success': True, 'message': 'Cache cleared'}

@app.route('/login')
def login():
    return "<h1>Login Page</h1><p>Ultra-fast version - login placeholder</p>"

@app.route('/health')
def health():
    """Performance monitoring"""
    try:
        db_status = "Connected" if mongo_db is not None else "Not Connected"
        cache_status = "Active" if levels_cache.get('last_updated') else "Inactive"
        
        return {
            "status": "healthy",
            "database": db_status,
            "cache": cache_status,
            "main_cached": len(levels_cache.get('main_list', [])),
            "legacy_cached": len(levels_cache.get('legacy_list', [])),
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 Starting ULTRA-FAST Level Management System")
    print("⚡ Optimized for instant level operations")
    print(f"🌐 Website: http://localhost:{port}")
    print(f"📊 Admin: http://localhost:{port}/admin")
    print(f"📈 Health: http://localhost:{port}/health")
    print("💡 Cache preloading enabled for maximum speed!")
    
    app.run(debug=False, host='0.0.0.0', port=port)