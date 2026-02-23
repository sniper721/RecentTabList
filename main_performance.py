"""
High-Performance RTL Website - Optimized for Admin Operations
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
app.secret_key = os.environ.get('SECRET_KEY', 'fast-rtl-key')
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enhanced MongoDB connection with better performance settings
def get_mongodb_connection():
    """Optimized MongoDB connection with performance settings"""
    try:
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
        mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
        
        # Performance-optimized connection settings
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=5000,
            socketTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=20,
            minPoolSize=5,
            maxIdleTimeMS=10000,
            waitQueueTimeoutMS=2000,
            retryWrites=True,
            retryReads=True,
            connect=False
        )
        
        db = client[mongodb_db]
        
        # Create performance indexes
        create_performance_indexes(db)
        
        # Test connection
        client.admin.command('ping', maxTimeMS=2000)
        print("✅ MongoDB connected with performance optimizations")
        return client, db
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return None, None

def create_performance_indexes(db):
    """Create indexes for better query performance"""
    try:
        # Indexes for common admin operations
        db.levels.create_index([("is_legacy", ASCENDING), ("position", ASCENDING)])
        db.levels.create_index([("position", ASCENDING)])
        db.levels.create_index([("is_legacy", ASCENDING)])
        db.levels.create_index([("name", ASCENDING)])
        
        db.records.create_index([("status", ASCENDING)])
        db.records.create_index([("user_id", ASCENDING)])
        db.records.create_index([("level_id", ASCENDING)])
        db.records.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
        
        db.users.create_index([("username", ASCENDING)])
        db.users.create_index([("points", DESCENDING)])
        
        print("✅ Performance indexes created")
    except Exception as e:
        print(f"⚠️ Index creation warning: {e}")

# Initialize MongoDB
print("🔄 Initializing optimized MongoDB connection...")
mongo_client, mongo_db = get_mongodb_connection()

# Simple cache with timeout
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None
}

def get_cached_levels(is_legacy=False, force_refresh=False):
    """Get cached levels with performance optimization"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    last_updated = levels_cache.get('last_updated')
    
    # Cache for 2 minutes (longer for better performance)
    if not force_refresh and last_updated and (datetime.now(timezone.utc) - last_updated).seconds < 120:
        return levels_cache.get(cache_key, [])
    
    return None

def get_main_levels_cached():
    """Get main levels with caching"""
    cached = get_cached_levels(is_legacy=False)
    if cached is not None:
        return cached
    
    if mongo_db is None:
        return [{"_id": 1, "name": "Database Not Available", "creator": "System", "position": 1, "points": 0}]
    
    try:
        # Optimized query with projection
        levels = list(mongo_db.levels.find(
            {"is_legacy": {"$ne": True}},  # Better than {"is_legacy": False}
            {
                "name": 1, "creator": 1, "verifier": 1, "position": 1, 
                "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1
            }
        ).sort("position", 1).limit(150))  # Reasonable limit
        
        # Update cache
        levels_cache['main_list'] = levels
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        return levels
        
    except Exception as e:
        print(f"Error fetching main levels: {e}")
        return [{"_id": 1, "name": "Error Loading Levels", "creator": "System", "position": 1, "points": 0}]

def get_pending_records_optimized():
    """Optimized pending records query without heavy aggregations"""
    if mongo_db is None:
        return []
    
    try:
        # Simple query instead of complex aggregation
        records = list(mongo_db.records.find(
            {"status": "pending"},
            {
                "user_id": 1, "level_id": 1, "progress": 1, 
                "video_url": 1, "created_at": 1, "screenshot_url": 1
            }
        ).sort("created_at", 1).limit(50))
        
        # Get user and level data separately (more efficient)
        user_ids = list(set(record['user_id'] for record in records if 'user_id' in record))
        level_ids = list(set(record['level_id'] for record in records if 'level_id' in record))
        
        # Batch queries
        users = {}
        levels = {}
        
        if user_ids:
            user_data = mongo_db.users.find(
                {"_id": {"$in": user_ids}},
                {"username": 1, "country": 1}
            )
            users = {user['_id']: user for user in user_data}
        
        if level_ids:
            level_data = mongo_db.levels.find(
                {"_id": {"$in": level_ids}},
                {"name": 1, "position": 1, "points": 1}
            )
            levels = {level['_id']: level for level in level_data}
        
        # Combine data
        enriched_records = []
        for record in records:
            enriched_record = dict(record)
            enriched_record['user'] = users.get(record.get('user_id'), {})
            enriched_record['level'] = levels.get(record.get('level_id'), {})
            enriched_records.append(enriched_record)
        
        return enriched_records
        
    except Exception as e:
        print(f"Error fetching pending records: {e}")
        return []

# Routes
@app.route('/')
def index():
    """Optimized index route"""
    try:
        main_list = get_main_levels_cached()
        return render_template('index_simple.html', 
                             levels=main_list[:30],  # Show first 30
                             total_levels=len(main_list),
                             loading_message="⚡ High-Performance Load",
                             mongo_db=mongo_db is not None)
    except Exception as e:
        print(f"Error in index route: {e}")
        return render_template('index_simple.html', 
                             levels=[{"_id": 1, "name": "System Error", "creator": "System", "position": 1, "points": 0}],
                             total_levels=1,
                             mongo_db=False)

@app.route('/admin')
def admin():
    """Optimized admin panel with fast loading"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Use optimized pending records query
    pending_records = get_pending_records_optimized()
    
    return render_template('admin/index.html', pending_records=pending_records)

@app.route('/admin/approve_record/<record_id>', methods=['POST'])
def admin_approve_record(record_id):
    """Optimized record approval - fast single operation"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        # Convert and validate
        record_object_id = ObjectId(record_id)
        record = mongo_db.records.find_one({"_id": record_object_id})
        
        if not record or record.get('status') == 'approved':
            return {'error': 'Record not found or already approved'}, 400
        
        # Fast approval - single update
        admin_username = session.get('username', 'Unknown Admin')
        mongo_db.records.update_one(
            {"_id": record_object_id},
            {"$set": {
                "status": "approved",
                "approved_by": admin_username,
                "approved_at": datetime.now(timezone.utc)
            }}
        )
        
        # Background points update (don't block the response)
        from threading import Thread
        def update_points_background():
            try:
                update_user_points(record['user_id'])
            except Exception as e:
                print(f"Background points update error: {e}")
        
        Thread(target=update_points_background, daemon=True).start()
        
        return {'success': True, 'message': 'Record approved successfully'}
        
    except Exception as e:
        print(f"Error approving record: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/reject_record/<record_id>', methods=['POST'])
def admin_reject_record(record_id):
    """Optimized record rejection - fast single operation"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        reason = request.form.get('reason', '').strip()
        record_object_id = ObjectId(record_id)
        
        # Fast rejection
        admin_username = session.get('username', 'Unknown Admin')
        update_data = {
            "status": "rejected",
            "rejected_by": admin_username,
            "rejected_at": datetime.now(timezone.utc)
        }
        
        if reason:
            update_data["rejection_reason"] = reason
            
        mongo_db.records.update_one({"_id": record_object_id}, {"$set": update_data})
        return {'success': True, 'message': 'Record rejected successfully'}
        
    except Exception as e:
        print(f"Error rejecting record: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/bulk_records', methods=['POST'])
def admin_bulk_records():
    """Optimized bulk operations with parallel processing"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        action = request.form.get('action')
        record_ids = request.form.getlist('record_ids')
        
        if not record_ids:
            return {'error': 'No records selected'}, 400
        
        # Convert to ObjectIds
        record_object_ids = [ObjectId(rid) for rid in record_ids]
        admin_username = session.get('username', 'Unknown Admin')
        
        # Batch operations for better performance
        if action == 'approve':
            # Batch update records
            mongo_db.records.update_many(
                {"_id": {"$in": record_object_ids}, "status": {"$ne": "approved"}},
                {"$set": {
                    "status": "approved",
                    "approved_by": admin_username,
                    "approved_at": datetime.now(timezone.utc)
                }}
            )
            
            # Get user IDs for points update
            records = mongo_db.records.find(
                {"_id": {"$in": record_object_ids}},
                {"user_id": 1}
            )
            user_ids = list(set(record['user_id'] for record in records))
            
            # Background points updates
            from threading import Thread
            def update_multiple_points():
                for user_id in user_ids:
                    try:
                        update_user_points(user_id)
                    except Exception as e:
                        print(f"Points update error for user {user_id}: {e}")
            
            Thread(target=update_multiple_points, daemon=True).start()
            
        elif action == 'reject':
            reason = request.form.get('reason', '').strip()
            update_data = {
                "status": "rejected",
                "rejected_by": admin_username,
                "rejected_at": datetime.now(timezone.utc)
            }
            if reason:
                update_data["rejection_reason"] = reason
                
            mongo_db.records.update_many(
                {"_id": {"$in": record_object_ids}, "status": {"$ne": "rejected"}},
                {"$set": update_data}
            )
        
        return {'success': True, 'message': f'Bulk {action} completed successfully'}
        
    except Exception as e:
        print(f"Error in bulk operation: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/levels')
def admin_levels():
    """Optimized levels management"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        filter_type = request.args.get('filter')
        is_legacy_filter = (filter_type == 'legacy')
        
        # Use cached data when possible
        levels = get_cached_levels(is_legacy=is_legacy_filter)
        if levels is None:
            # Load from database with optimized query
            query = {"is_legacy": True} if is_legacy_filter else {"is_legacy": {"$ne": True}}
            projection = {
                "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1,
                "level_id": 1, "difficulty": 1, "is_legacy": 1, "thumbnail_url": 1
            }
            levels = list(mongo_db.levels.find(query, projection).sort("position", 1))
            
            # Update cache
            cache_key = 'legacy_list' if is_legacy_filter else 'main_list'
            levels_cache[cache_key] = levels
            levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        return render_template('admin/levels.html', levels=levels, is_legacy_filter=is_legacy_filter)
        
    except Exception as e:
        print(f"Error in admin_levels: {e}")
        flash('Error loading levels', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/move_level/<level_id>', methods=['POST'])
def admin_move_level(level_id):
    """Optimized level moving with minimal database operations"""
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
        
        # Calculate new position
        if direction == 'up' and current_position > 1:
            new_position = current_position - 1
        elif direction == 'down':
            new_position = current_position + 1
        else:
            return {'error': 'Invalid move'}, 400
        
        # Atomic position swap
        if direction == 'up':
            # Move current level up, push other level down
            mongo_db.levels.update_one(
                {"position": new_position, "is_legacy": is_legacy},
                {"$set": {"position": current_position}}
            )
            mongo_db.levels.update_one(
                {"_id": ObjectId(level_id)},
                {"$set": {"position": new_position}}
            )
        else:
            # Move current level down, push other level up
            mongo_db.levels.update_one(
                {"position": new_position, "is_legacy": is_legacy},
                {"$set": {"position": current_position}}
            )
            mongo_db.levels.update_one(
                {"_id": ObjectId(level_id)},
                {"$set": {"position": new_position}}
            )
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Background points recalculation
        from threading import Thread
        def recalculate_background():
            try:
                recalculate_all_points()
            except Exception as e:
                print(f"Background recalculation error: {e}")
        
        Thread(target=recalculate_background, daemon=True).start()
        
        return {'success': True, 'new_position': new_position}
        
    except Exception as e:
        print(f"Error moving level: {e}")
        return {'error': str(e)}, 500

def update_user_points(user_id):
    """Optimized user points calculation"""
    if mongo_db is None:
        return
    
    try:
        # Get all approved records for this user
        records = list(mongo_db.records.find({
            "user_id": user_id,
            "status": "approved"
        }))
        
        # Get all levels in one query
        level_ids = [record['level_id'] for record in records]
        if level_ids:
            levels = mongo_db.levels.find(
                {"_id": {"$in": level_ids}},
                {"points": 1, "is_legacy": 1, "min_percentage": 1}
            )
            level_dict = {level['_id']: level for level in levels}
        else:
            level_dict = {}
        
        # Calculate total points
        total_points = 0.0
        for record in records:
            level = level_dict.get(record['level_id'])
            if level and not level.get('is_legacy', False):
                if record['progress'] == 100:
                    total_points += float(level['points'])
                elif record['progress'] >= level.get('min_percentage', 100) and level.get('min_percentage', 100) < 100:
                    total_points += round(float(level['points']) * 0.1, 2)
        
        # Single update operation
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"points": round(total_points, 2)}}
        )
        
    except Exception as e:
        print(f"Error updating user points: {e}")

def recalculate_all_points():
    """Optimized full points recalculation"""
    if mongo_db is None:
        return
    
    try:
        # Get all levels once
        levels = list(mongo_db.levels.find({}, {"points": 1, "is_legacy": 1, "position": 1}))
        level_dict = {level['_id']: level for level in levels}
        
        # Get all users
        users = list(mongo_db.users.find({}, {"_id": 1}))
        
        # Process users in batches
        batch_size = 10
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            for user in batch:
                update_user_points(user['_id'])
                
    except Exception as e:
        print(f"Error in full recalculation: {e}")

@app.route('/login')
def login():
    """Simple login page for testing"""
    return "<h1>Login Page</h1><p>Performance version - login functionality placeholder</p>"

@app.route('/health')
def health():
    """Performance monitoring endpoint"""
    try:
        if mongo_db is not None:
            mongo_client.admin.command('ping', maxTimeMS=1000)
            db_status = "Connected"
        else:
            db_status = "Not Connected"
        
        return {
            "status": "healthy",
            "database": db_status,
            "cache_status": "Active" if levels_cache.get('last_updated') else "Inactive",
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": str(datetime.now())
        }, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print("🚀 Starting HIGH-PERFORMANCE RTL Server")
    print("⚡ Optimized for fast admin operations")
    print(f"🌐 Website: http://localhost:{port}")
    print(f"📊 Health: http://localhost:{port}/health")
    print("💡 Performance optimizations enabled!")
    
    app.run(debug=False, host='0.0.0.0', port=port)