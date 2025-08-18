from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone, timedelta

# Try to import Discord integration, but don't fail if it's missing
try:
    from discord_integration import notify_record_submitted, notify_record_approved, notify_record_rejected
    DISCORD_AVAILABLE = True
    print("✅ Discord integration loaded successfully")
except ImportError as e:
    print(f"❌ Discord integration failed to load: {e}")
    DISCORD_AVAILABLE = False
    # Create dummy functions so the app doesn't crash
    def notify_record_submitted(*args, **kwargs):
        print("❌ Discord integration not available - notify_record_submitted")
    def notify_record_approved(*args, **kwargs):
        print("❌ Discord integration not available - notify_record_approved")  
    def notify_record_rejected(*args, **kwargs):
        print("❌ Discord integration not available - notify_record_rejected")
from dotenv import load_dotenv
from bson.objectid import ObjectId
from bson.errors import InvalidId
import functools

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Initialize MongoDB and OAuth
print("Initializing MongoDB connection...")
import time
retry_count = 0
max_retries = 3

while retry_count < max_retries:
    try:
        print(f"MongoDB URI: {mongodb_uri[:50]}... (attempt {retry_count + 1}/{max_retries})")
        print(f"MongoDB DB: {mongodb_db}")
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=10000,
            retryWrites=True,
            retryReads=True
        )
        mongo_db = mongo_client[mongodb_db]
        # Test connection with timeout
        mongo_client.admin.command('ping', maxTimeMS=30000)
        print("✓ MongoDB initialized successfully")
        break
    except Exception as e:
        retry_count += 1
        print(f"❌ MongoDB connection attempt {retry_count} failed: {e}")
        if retry_count < max_retries:
            print(f"Retrying in 5 seconds...")
            time.sleep(5)
        else:
            print("All MongoDB connection attempts failed")
            raise Exception("Failed to connect to MongoDB after all retries")

if retry_count < max_retries:
    # Create indexes for better performance
    try:
        mongo_db.levels.create_index([("is_legacy", 1), ("position", 1)])
        print("✓ Database indexes created")
    except Exception as e:
        print(f"Index creation warning: {e}")
else:
    print("MongoDB initialization error: Failed after all retries")
    print("Falling back to SQLite...")
    # Fall back to SQLite if MongoDB fails
    import subprocess
    subprocess.run(['python', 'main_sqlite_backup.py'])
    exit()
    
print("Initializing OAuth...")
oauth = OAuth(app)

# Configure Google OAuth only if credentials are provided
print("Configuring Google OAuth...")
google = None
if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
    print("Google OAuth credentials found, registering...")
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    print("✓ Google OAuth configured")
else:
    print("No Google OAuth credentials found, skipping...")

# Simple cache for levels
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'last_updated': None
}

def get_cached_levels(is_legacy=False, quick_load=False):
    """Return cached levels only - auto-loading happens in routes"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    return levels_cache.get(cache_key, [])

# Helper functions
def retry_db_operation(max_retries=3, delay=1):
    """Decorator to retry database operations on timeout"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    if ("timeout" in error_str or "network" in error_str) and attempt < max_retries - 1:
                        print(f"Database timeout/network error on attempt {attempt + 1}, retrying in {delay}s...")
                        
                        # Try to reinitialize connection on timeout
                        if attempt == 1:  # On second attempt, try reinitializing
                            print("Attempting to reinitialize database connection...")
                            reinitialize_db_connection()
                        
                        time.sleep(delay)
                        continue
                    raise e
            return None
        return wrapper
    return decorator

def get_video_embed_info(video_url):
    """Extract video platform and embed information from URL"""
    if not video_url:
        return None
    
    # YouTube support
    if 'youtube.com' in video_url or 'youtu.be' in video_url:
        if 'youtube.com' in video_url and 'v=' in video_url:
            video_id = video_url.split('v=')[1].split('&')[0]
        elif 'youtu.be' in video_url:
            video_id = video_url.split('/')[-1].split('?')[0]
        else:
            return None
        return {
            'platform': 'youtube',
            'embed_url': f'https://www.youtube.com/embed/{video_id}',
            'video_id': video_id
        }
    
    # Streamable support
    elif 'streamable.com' in video_url:
        video_id = video_url.split('/')[-1]
        return {
            'platform': 'streamable',
            'embed_url': f'https://streamable.com/e/{video_id}',
            'video_id': video_id
        }
    
    # Vimeo support
    elif 'vimeo.com' in video_url:
        video_id = video_url.split('/')[-1].split('?')[0]
        return {
            'platform': 'vimeo',
            'embed_url': f'https://player.vimeo.com/video/{video_id}',
            'video_id': video_id
        }
    
    # TikTok support
    elif 'tiktok.com' in video_url:
        # Extract video ID from TikTok URL
        if '/video/' in video_url:
            video_id = video_url.split('/video/')[1].split('?')[0]
        else:
            return None
        return {
            'platform': 'tiktok',
            'embed_url': f'https://www.tiktok.com/embed/v2/{video_id}',
            'video_id': video_id
        }
    
    return None

# Context processor
@app.context_processor
def utility_processor():
    def format_points(points):
        return int(points) if points else 0
    
    def get_active_announcements():
        """Get active announcements that haven't expired"""
        try:
            now = datetime.now(timezone.utc)
            return list(mongo_db.announcements.find({
                "active": True,
                "expires_at": {"$gt": now}
            }).sort("created_at", -1).limit(5))
        except:
            return []
    
    # Get current theme from session
    current_theme = session.get('theme', 'light')
    
    return dict(
        format_points=format_points, 
        get_video_embed_info=get_video_embed_info,
        current_theme=current_theme,
        get_active_announcements=get_active_announcements
    )

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    # Position 1 = exponent 0, Position 2 = exponent 1, etc.
    return int(250 * (0.9475 ** (position - 1)))

def check_db_connection():
    """Check if database connection is healthy"""
    try:
        mongo_client.admin.command('ping', maxTimeMS=5000)
        return True
    except Exception as e:
        print(f"Database connection check failed: {e}")
        return False

def reinitialize_db_connection():
    """Reinitialize MongoDB connection with fresh client"""
    global mongo_client, mongo_db
    try:
        print("Reinitializing MongoDB connection...")
        # Close existing connection
        if mongo_client:
            mongo_client.close()
        
        # Create new connection
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=False,
            tlsAllowInvalidHostnames=False,
            serverSelectionTimeoutMS=60000,
            socketTimeoutMS=60000,
            connectTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=1,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=10000,
            retryWrites=True,
            retryReads=True
        )
        mongo_db = mongo_client[mongodb_db]
        
        # Test new connection
        mongo_client.admin.command('ping', maxTimeMS=30000)
        print("✓ MongoDB connection reinitialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to reinitialize MongoDB connection: {e}")
        return False

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    # Handle both dict and aggregation result formats
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0
    
    # Full completion
    if record['progress'] == 100:
        return level['points']
    
    # List% completion (10% of full points for any progress >= min_percentage)
    if record['progress'] >= level.get('min_percentage', 100):
        return level['points'] * 0.1
    
    return 0

def update_user_points(user_id):
    """Recalculate and update user's total points - FIXED aggregation handling"""
    # Use aggregation to join records with levels in a single query
    pipeline = [
        {"$match": {"user_id": user_id, "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id", 
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$project": {
            "progress": 1,
            "status": 1,  # Include status field
            "level.points": 1,
            "level.is_legacy": 1,
            "level.min_percentage": 1
        }}
    ]
    
    records_with_levels = list(mongo_db.records.aggregate(pipeline))
    total_points = 0
    
    for record in records_with_levels:
        level = record['level']
        # Ensure record has status field for calculation
        record_with_status = {
            'progress': record['progress'],
            'status': record.get('status', 'approved')  # Default to approved since we filtered for it
        }
        points = calculate_record_points(record_with_status, level)
        total_points += points
        print(f"DEBUG: User {user_id} - Record progress {record['progress']}% = {points} points")
    
    print(f"DEBUG: User {user_id} total points: {total_points}")
    
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"points": total_points}}
    )
    return total_points

def shift_level_positions(position, is_legacy=False, direction=1):
    """Shift level positions up or down from a given position"""
    mongo_db.levels.update_many(
        {"position": {"$gte": position}, "is_legacy": is_legacy},
        {"$inc": {"position": direction}}
    )

def recalculate_all_points():
    """Recalculate points for all levels based on their current positions - OPTIMIZED with bulk operations"""
    from pymongo import UpdateOne
    
    levels = list(mongo_db.levels.find({}, {"_id": 1, "position": 1, "is_legacy": 1, "points": 1}))
    
    # Prepare bulk operations using proper MongoDB UpdateOne objects
    bulk_operations = []
    for level in levels:
        new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        if level.get('points') != new_points:
            bulk_operations.append(
                UpdateOne(
                    {"_id": level['_id']},
                    {"$set": {"points": new_points}}
                )
            )
    
    # Execute all updates in a single bulk operation
    if bulk_operations:
        mongo_db.levels.bulk_write(bulk_operations)
        print(f"Updated points for {len(bulk_operations)} levels")

def log_level_change(action, level_name, admin_username, **kwargs):
    """Log level placement/movement changes to changelog"""
    try:
        changelog_entry = {
            "timestamp": datetime.now(timezone.utc),
            "action": action,  # "placed", "moved", "legacy", "removed"
            "level_name": level_name,
            "admin": admin_username,
            **kwargs  # Additional data like position, above_level, below_level, etc.
        }
        
        mongo_db.level_changelog.insert_one(changelog_entry)
        print(f"📝 Logged level change: {action} - {level_name}")
        
    except Exception as e:
        print(f"Error logging level change: {e}")

def log_admin_action(admin_username, action, details=""):
    """Log admin actions to Discord"""
    try:
        import requests
        import os
        
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("No Discord webhook URL configured for admin logs")
            return
        
        embed = {
            "title": "🔧 Admin Action",
            "color": 0xff9500,  # Orange color
            "fields": [
                {
                    "name": "👤 Admin",
                    "value": admin_username,
                    "inline": True
                },
                {
                    "name": "⚡ Action",
                    "value": action,
                    "inline": True
                },
                {
                    "name": "🕒 Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "inline": True
                }
            ],
            "footer": {
                "text": "RTL Admin Logs"
            }
        }
        
        if details:
            embed["fields"].append({
                "name": "📝 Details",
                "value": details,
                "inline": False
            })
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print(f"Admin action logged: {action}")
        else:
            print(f"Failed to log admin action: {response.status_code}")
            
    except Exception as e:
        print(f"Error logging admin action: {e}")

def send_discord_notification_direct(username, level_name, progress, video_url):
    """Direct Discord notification without external file"""
    import requests
    import os
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    website_url = os.environ.get('WEBSITE_URL', 'http://localhost:10000')
    
    if not webhook_url:
        print("❌ No Discord webhook URL configured")
        return
    
    print(f"🔔 Sending direct Discord notification for {username}")
    
    embed = {
        "title": "📝 New Record Submission",
        "description": "A new record has been submitted for review",
        "color": 16766020,  # Yellow color
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fields": [
            {"name": "👤 Player", "value": username, "inline": True},
            {"name": "🎮 Level", "value": level_name, "inline": True},
            {"name": "📊 Progress", "value": f"{progress}%", "inline": True},
        ],
        "footer": {"text": "RTL Admin Notification System"}
    }
    
    if video_url:
        embed["fields"].append({
            "name": "🎥 Video",
            "value": f"[Watch Video]({video_url})",
            "inline": False
        })
    
    embed["fields"].append({
        "name": "⚙️ Admin Panel",
        "value": f"[Review Submission]({website_url}/admin)",
        "inline": False
    })
    
    try:
        response = requests.post(
            webhook_url,
            json={"embeds": [embed]},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📡 Discord API response: {response.status_code}")
        
        if response.status_code == 204:
            print("✅ Direct Discord notification sent successfully")
        else:
            print(f"❌ Discord webhook failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Direct Discord notification error: {e}")
        import traceback
        traceback.print_exc()

print("Setting up routes...")

@app.route('/thumb/<path:url>')
def thumbnail_proxy(url):
    """SIMPLE thumbnail proxy - just pass through the URL"""
    import requests
    from flask import Response
    from urllib.parse import unquote
    
    try:
        # Decode the URL
        url = unquote(url)
        
        # Simple headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Just fetch and return the image
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return Response(
                response.content,
                mimetype='image/jpeg',
                headers={'Cache-Control': 'public, max-age=3600'}
            )
        else:
            # Return 1x1 transparent pixel as fallback
            return Response(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
                mimetype='image/png'
            )
            
    except Exception as e:
        print(f"Thumbnail error: {e}")
        # Return 1x1 transparent pixel
        return Response(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
            mimetype='image/png'
        )

@app.route('/test')
def test():
    return "<h1>Test route works!</h1>"

@app.route('/test_images_simple')
def test_images_simple():
    """Simple image test with known YouTube videos"""
    test_levels = [
        {
            'name': 'Test Level 1',
            'video_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'position': 1
        },
        {
            'name': 'Test Level 2', 
            'video_url': 'https://youtu.be/9bZkp7q19f0',
            'position': 2
        },
        {
            'name': 'Test Level 3',
            'video_url': 'https://www.youtube.com/watch?v=KDjwz-Lt-Qo',
            'position': 3
        },
        {
            'name': 'Test Level 4 (No Video)',
            'video_url': '',
            'position': 4
        }
    ]
    
    html = """
    <h2>🧪 Simple Image Test</h2>
    <p>Testing the new clean image code...</p>
    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
    """
    
    for level in test_levels:
        video_url = level['video_url']
        level_name = level['name']
        
        # Same logic as template
        if video_url and 'youtube.com' in video_url and 'v=' in video_url:
            video_id = video_url.split('v=')[1].split('&')[0]
            img_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" alt="{level_name}" style="width: 206px; height: 116px; object-fit: cover; border-radius: 8px;">'
        elif video_url and 'youtu.be' in video_url:
            video_id = video_url.split('youtu.be/')[1].split('?')[0]
            img_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" alt="{level_name}" style="width: 206px; height: 116px; object-fit: cover; border-radius: 8px;">'
        else:
            img_html = '<div style="width: 206px; height: 116px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d;">📷 No Preview</div>'
        
        html += f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: white;">
            <h4>#{level['position']} - {level_name}</h4>
            <p><strong>Video URL:</strong> {video_url if video_url else 'None'}</p>
            <div style="margin: 10px 0;">
                {img_html}
            </div>
        </div>
        """
    
    html += """
    </div>
    <p style="margin-top: 20px;">
        <a href="/">← Back to main list</a> | 
        <a href="/test_images_simple">🔄 Refresh test</a>
    </p>
    """
    
    return html

@app.route('/stress_test_images')
def stress_test_images():
    """Stress test images with multiple refreshes"""
    import time
    from datetime import datetime
    
    html = f"""
    <h2>🔥 Image Stress Test</h2>
    <p><strong>Test Time:</strong> {datetime.now().strftime('%H:%M:%S')}</p>
    <p>This page will auto-refresh every 5 seconds to test image stability...</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0;">
    """
    
    # Test with real levels from database
    try:
        levels = list(mongo_db.levels.find(
            {"is_legacy": False, "video_url": {"$exists": True, "$ne": ""}},
            {"name": 1, "video_url": 1, "position": 1}
        ).limit(12))
        
        for level in levels:
            video_url = level.get('video_url', '')
            level_name = level.get('name', 'Unknown')
            position = level.get('position', 0)
            
            if video_url and 'youtube.com' in video_url and 'v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
                img_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" alt="{level_name}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 8px;" onload="this.style.border=\'2px solid green\'" onerror="this.style.border=\'2px solid red\'">'
            elif video_url and 'youtu.be' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
                img_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" alt="{level_name}" style="width: 100%; height: 120px; object-fit: cover; border-radius: 8px;" onload="this.style.border=\'2px solid green\'" onerror="this.style.border=\'2px solid red\'">'
            else:
                img_html = '<div style="width: 100%; height: 120px; background: #f8f9fa; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6c757d; border: 2px solid orange;">📷 No Preview</div>'
            
            html += f"""
            <div style="border: 1px solid #ddd; padding: 10px; border-radius: 8px; background: white;">
                <h5>#{position} - {level_name[:20]}{'...' if len(level_name) > 20 else ''}</h5>
                <div style="margin: 10px 0;">
                    {img_html}
                </div>
                <small style="color: #666; word-break: break-all;">{video_url[:50]}{'...' if len(video_url) > 50 else ''}</small>
            </div>
            """
            
    except Exception as e:
        html += f'<p style="color: red;">Database error: {e}</p>'
    
    html += """
    </div>
    
    <div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
        <h4>🎯 Test Results:</h4>
        <ul>
            <li><strong>Green border:</strong> Image loaded successfully ✅</li>
            <li><strong>Red border:</strong> Image failed to load ❌</li>
            <li><strong>Orange border:</strong> No video URL provided ⚠️</li>
        </ul>
    </div>
    
    <p>
        <a href="/">← Back to main list</a> | 
        <a href="/stress_test_images">🔄 Manual refresh</a> |
        <a href="/test_images_simple">Simple test</a>
    </p>
    
    <script>
        // Auto-refresh every 5 seconds for stress testing
        setTimeout(function() {
            window.location.reload();
        }, 5000);
        
        // Count successful/failed images
        setTimeout(function() {
            const images = document.querySelectorAll('img');
            let loaded = 0, failed = 0;
            images.forEach(img => {
                if (img.style.border.includes('green')) loaded++;
                if (img.style.border.includes('red')) failed++;
            });
            console.log(`Images: ${loaded} loaded, ${failed} failed`);
        }, 2000);
    </script>
    """
    
    return html

@app.route('/debug_images')
def debug_images():
    """Debug route to check what's actually in the database"""
    try:
        # Get ALL levels and see what we have
        levels = list(mongo_db.levels.find(
            {},
            {"name": 1, "thumbnail_url": 1, "video_url": 1, "position": 1}
        ).sort("position", 1).limit(20))
        
        html = "<h2>🔍 Debug: What's Actually in the Database</h2>"
        html += f"<p>Checking first 20 levels...</p>"
        
        for level in levels:
            thumbnail_url = level.get('thumbnail_url', '')
            video_url = level.get('video_url', '')
            
            # Build the image part separately to avoid nested f-string issues
            image_part = ""
            if thumbnail_url:
                image_part = f'<p><img src="{thumbnail_url}" style="max-width: 200px; border: 1px solid red;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'block\'"><div style="display:none; background:#f0f0f0; padding:10px;">❌ FAILED TO LOAD</div></p>'
            else:
                image_part = '<p>❌ No thumbnail URL</p>'
            
            html += f"""
            <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; background: #f9f9f9;">
                <h4>#{level.get('position', '?')} - {level.get('name', 'Unknown')}</h4>
                <p><strong>Thumbnail URL:</strong> <code>{thumbnail_url if thumbnail_url else 'EMPTY'}</code></p>
                <p><strong>Video URL:</strong> <code>{video_url if video_url else 'EMPTY'}</code></p>
                {image_part}
            </div>
            """
        
        html += '<p><a href="/">← Back to main list</a> | <a href="/fix_all_images">Fix All Images</a></p>'
        return html
        
    except Exception as e:
        return f"Error: {e}"

@app.route('/fix_all_images')
def fix_all_images():
    """Fix ALL image URLs in database - nuclear option"""
    try:
        results = []
        fixed_count = 0
        
        # Get ALL levels
        all_levels = list(mongo_db.levels.find({}))
        
        for level in all_levels:
            video_url = level.get('video_url', '')
            current_thumbnail = level.get('thumbnail_url', '')
            
            new_thumbnail = None
            
            # If it has a YouTube video, generate thumbnail
            if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                video_id = None
                if 'watch?v=' in video_url:
                    video_id = video_url.split('watch?v=')[1].split('&')[0]
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                
                if video_id:
                    new_thumbnail = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            
            # Update if we have a new thumbnail or need to clear a bad one
            if new_thumbnail and new_thumbnail != current_thumbnail:
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"thumbnail_url": new_thumbnail}}
                )
                fixed_count += 1
                results.append(f"✅ {level.get('name', 'Unknown')}: {new_thumbnail}")
            elif not video_url and current_thumbnail:
                # Clear thumbnail if no video
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"thumbnail_url": ""}}
                )
                results.append(f"🗑️ Cleared {level.get('name', 'Unknown')}: no video")
        
        # Clear cache
        global levels_cache
        levels_cache.clear()
        
        html = f"<h2>🔧 Fixed {fixed_count} images total</h2>"
        html += "<h3>Changes made:</h3><ul>"
        for result in results[:30]:  # Show first 30
            html += f"<li>{result}</li>"
        html += "</ul>"
        html += f'<p><a href="/debug_images">Check results</a> | <a href="/">Main list</a></p>'
        
        return html
        
    except Exception as e:
        return f"Error fixing all images: {e}"

@app.route('/test_images')
def test_images():
    """Test what data is actually being passed to templates"""
    try:
        # Get first 5 levels exactly like the main route does
        main_list = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1).limit(5))
        
        html = "<h2>🧪 Test: Data Being Passed to Template</h2>"
        
        for level in main_list:
            thumbnail_url = level.get('thumbnail_url', '')
            video_url = level.get('video_url', '')
            level_name = level.get('name', 'Unknown')
            
            # Test the same logic as the template
            img_src = ''
            if thumbnail_url and thumbnail_url.strip() != '':
                img_src = thumbnail_url
            elif video_url and 'youtube.com' in video_url and 'watch?v=' in video_url:
                video_id = video_url.split('watch?v=')[1].split('&')[0]
                img_src = f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg'
            elif video_url and 'youtu.be' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
                img_src = f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg'
            
            # Build image test HTML separately to avoid f-string issues
            if img_src:
                image_test = f'<p><strong>TEST IMAGE:</strong><br><img src="{img_src}" style="max-width: 200px; border: 2px solid green;" onload="this.style.border=\'2px solid green\'" onerror="this.style.border=\'2px solid red\'; this.nextElementSibling.style.display=\'block\'"><div style="display:none; color:red;">❌ FAILED TO LOAD</div></p>'
            else:
                image_test = '<p style="color: red;">❌ NO IMAGE SOURCE COMPUTED</p>'
            
            html += f"""
            <div style="border: 2px solid #007bff; margin: 15px; padding: 15px; background: #f8f9fa;">
                <h4>#{level.get('position', '?')} - {level_name}</h4>
                <p><strong>Raw thumbnail_url:</strong> <code>"{thumbnail_url}"</code></p>
                <p><strong>Raw video_url:</strong> <code>"{video_url}"</code></p>
                <p><strong>Computed img_src:</strong> <code>"{img_src}"</code></p>
                {image_test}
            </div>
            """
        
        html += '<p><a href="/">← Back to main list</a></p>'
        return html
        
    except Exception as e:
        return f"Error testing images: {e}"

@app.route('/clear_cache')
def clear_cache():
    """Clear the levels cache"""
    global levels_cache
    levels_cache = {
        'main_list': None,
        'legacy_list': None,
        'last_updated': None
    }
    return "Cache cleared! <a href='/preload_cache'>Reload cache</a> | <a href='/'>Go to main list</a>"

@app.route('/create_indexes')
def create_indexes():
    """Create database indexes for better performance"""
    try:
        # Create indexes for faster queries
        mongo_db.levels.create_index([("is_legacy", 1), ("position", 1)])
        mongo_db.levels.create_index([("position", 1)])
        mongo_db.levels.create_index([("is_legacy", 1)])
        mongo_db.records.create_index([("level_id", 1), ("status", 1)])
        mongo_db.records.create_index([("user_id", 1)])
        
        return "Database indexes created for better performance! <a href='/'>Go to main list</a>"
    except Exception as e:
        return f"Error creating indexes: {e}"

@app.route('/load_all')
def load_all():
    """Load all data immediately (may be slow)"""
    try:
        print("Loading all main levels...")
        main_levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1}
        ).sort("position", 1))
        levels_cache['main_list'] = main_levels
        
        print("Loading all legacy levels...")
        legacy_levels = list(mongo_db.levels.find(
            {"is_legacy": True},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1}
        ).sort("position", 1))
        levels_cache['legacy_list'] = legacy_levels
        
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        return f"All data loaded! Main: {len(main_levels)}, Legacy: {len(legacy_levels)}. <a href='/'>View main list</a>"
        
    except Exception as e:
        return f"Loading failed: {e}"

@app.route('/load_data')
def load_data():
    """Load data from database in background - async approach"""
    import threading
    
    def load_in_background():
        try:
            print("Starting background data load...")
            
            # Load main levels
            print("Loading main levels...")
            main_levels = list(mongo_db.levels.find(
                {"is_legacy": False},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1}
            ).sort("position", 1))
            levels_cache['main_list'] = main_levels
            print(f"Loaded {len(main_levels)} main levels")
            
            # Load legacy levels  
            print("Loading legacy levels...")
            legacy_levels = list(mongo_db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1}
            ).sort("position", 1))
            levels_cache['legacy_list'] = legacy_levels
            print(f"Loaded {len(legacy_levels)} legacy levels")
            
            levels_cache['last_updated'] = datetime.now(timezone.utc)
            print("Background loading complete!")
            
        except Exception as e:
            print(f"Background loading failed: {e}")
    
    # Start loading in background
    thread = threading.Thread(target=load_in_background)
    thread.daemon = True
    thread.start()
    
    return """
    <h2>Loading Data...</h2>
    <p>Data is loading in the background. This may take a minute.</p>
    <p><a href="/">Check Main List</a> | <a href="/legacy">Check Legacy List</a></p>
    <script>
        setTimeout(function() {
            window.location.href = '/';
        }, 10000);
    </script>
    """

@app.route('/fast')
def fast_index():
    """Ultra-fast route that bypasses database entirely"""
    sample_levels = [
        {
            "_id": 1,
            "name": "Sample Level 1",
            "creator": "Creator1",
            "verifier": "Verifier1",
            "position": 1,
            "points": 250,
            "level_id": "12345",
            "difficulty": 8.5
        },
        {
            "_id": 2, 
            "name": "Sample Level 2",
            "creator": "Creator2",
            "verifier": "Verifier2",
            "position": 2,
            "points": 237,
            "level_id": "12346",
            "difficulty": 7.2
        }
    ]
    return render_template('index.html', levels=sample_levels)

@app.route('/emergency')
def emergency_index():
    """Emergency route - completely bypasses database"""
    return """
    <h1>RTL - Emergency Mode</h1>
    <p>Database is too slow. Try these options:</p>
    <ul>
        <li><a href="/fast">Fast sample page</a></li>
        <li><a href="/debug_db">Check database status</a></li>
        <li><a href="/create_indexes">Create database indexes</a></li>
        <li><a href="/test_speed">Test optimized speed</a></li>
    </ul>
    """

@app.route('/test_speed')
def test_speed():
    """Test the speed of optimized queries"""
    import time
    
    start_time = time.time()
    try:
        # Test the optimized query
        levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1}
        ).sort("position", 1).limit(20))
        
        end_time = time.time()
        query_time = end_time - start_time
        
        return f"""
        <h2>Speed Test Results</h2>
        <p>Query time: {query_time:.3f} seconds</p>
        <p>Levels loaded: {len(levels)}</p>
        <p>First level: {levels[0]['name'] if levels else 'None'}</p>
        <p><a href="/">Try main page now</a> | <a href="/force_cache">Force load cache</a></p>
        """
    except Exception as e:
        end_time = time.time()
        query_time = end_time - start_time
        return f"Query failed after {query_time:.3f} seconds: {e}"

@app.route('/fix_base64')
def fix_base64():
    """Remove Base64 images that are killing performance"""
    try:
        # Find all Base64 images
        base64_levels = list(mongo_db.levels.find({"thumbnail_url": {"$regex": "^data:"}}))
        
        if not base64_levels:
            return "No Base64 images found! ✅"
        
        # Remove Base64 thumbnails (they're too big)
        result = mongo_db.levels.update_many(
            {"thumbnail_url": {"$regex": "^data:"}},
            {"$set": {"thumbnail_url": ""}}
        )
        
        # Clear cache so it reloads
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        return f"""
        <h2>✅ Fixed Base64 Images!</h2>
        <p>Removed {result.modified_count} Base64 images</p>
        <p>These were causing massive slowdowns (each image was several MB in the database)</p>
        <p><a href="/instant_load">Reload data</a> | <a href="/">Go to main list</a></p>
        """
        
    except Exception as e:
        return f"Error fixing Base64: {e}"

@app.route('/fix_thumbnails')
def fix_thumbnails():
    """Comprehensive thumbnail system fix"""
    try:
        import os
        import shutil
        
        results = []
        
        # 1. Clear thumbnail cache
        cache_dir = 'static/thumbs'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            results.append("✅ Cleared thumbnail cache")
        
        os.makedirs(cache_dir, exist_ok=True)
        results.append("✅ Created fresh thumbnail cache directory")
        
        # 2. Remove Base64 thumbnails
        base64_count = mongo_db.levels.count_documents({"thumbnail_url": {"$regex": "^data:"}})
        if base64_count > 0:
            mongo_db.levels.update_many(
                {"thumbnail_url": {"$regex": "^data:"}},
                {"$set": {"thumbnail_url": ""}}
            )
            results.append(f"✅ Removed {base64_count} Base64 thumbnails")
        
        # 3. Fix YouTube URLs
        youtube_levels = list(mongo_db.levels.find({
            "video_url": {"$regex": "youtube|youtu.be", "$options": "i"}
        }))
        
        fixed_youtube = 0
        for level in youtube_levels:
            video_url = level.get('video_url', '')
            if video_url and not level.get('thumbnail_url'):
                # Extract video ID and create thumbnail URL
                video_id = None
                if 'watch?v=' in video_url:
                    video_id = video_url.split('watch?v=')[1].split('&')[0]
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                
                if video_id:
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                    mongo_db.levels.update_one(
                        {"_id": level["_id"]},
                        {"$set": {"thumbnail_url": thumbnail_url}}
                    )
                    fixed_youtube += 1
        
        if fixed_youtube > 0:
            results.append(f"✅ Fixed {fixed_youtube} YouTube thumbnails")
        
        # 4. Clear levels cache to force reload
        global levels_cache
        levels_cache.clear()
        results.append("✅ Cleared levels cache")
        
        # 5. Create placeholder for missing thumbnails
        placeholder_path = os.path.join(cache_dir, 'placeholder.jpg')
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (320, 180), color='#f8f9fa')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            text = "No Thumbnail"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (320 - text_width) // 2
            y = (180 - text_height) // 2
            
            draw.text((x, y), text, fill='#6c757d', font=font)
            img.save(placeholder_path, 'JPEG', quality=85)
            results.append("✅ Created placeholder thumbnail")
            
        except Exception as e:
            results.append(f"⚠️ Could not create placeholder: {e}")
        
        return f"""
        <h2>🔧 Thumbnail System Fixed!</h2>
        <div style="font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px;">
            {'<br>'.join(results)}
        </div>
        <br>
        <p><a href="/instant_load" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔄 Reload Data</a></p>
        <p><a href="/" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🏠 Back to Main</a></p>
        <p><a href="/test_thumbnails" style="background: #ffc107; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🧪 Test Thumbnails</a></p>
        """
        
    except Exception as e:
        return f"❌ Error fixing thumbnails: {e}"

@app.route('/test_thumbnails')
def test_thumbnails():
    """Test thumbnail system with sample URLs"""
    try:
        import requests
        
        test_urls = [
            "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",  # Rick Roll
            "https://img.youtube.com/vi/9bZkp7q19f0/mqdefault.jpg",  # Gangnam Style
            "https://example.com/nonexistent.jpg",  # Should fail gracefully
        ]
        
        results = []
        
        for url in test_urls:
            try:
                # Test our thumbnail proxy
                proxy_url = f"/thumb/{url}"
                results.append(f"✅ Proxy URL: <a href='{proxy_url}' target='_blank'>{proxy_url}</a>")
                
                # Test direct access
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    results.append(f"✅ Direct access OK: {url}")
                else:
                    results.append(f"⚠️ Direct access failed ({response.status_code}): {url}")
                    
            except Exception as e:
                results.append(f"❌ Error testing {url}: {e}")
        
        return f"""
        <h2>🧪 Thumbnail System Test</h2>
        <div style="font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px;">
            {'<br>'.join(results)}
        </div>
        <br>
        <h3>Sample Thumbnails:</h3>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            {' '.join([f'<img src="/thumb/{url}" style="max-width: 200px; border: 1px solid #ddd;" onerror="this.style.display=\'none\'">' for url in test_urls])}
        </div>
        <br>
        <p><a href="/" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🏠 Back to Main</a></p>
        """
        
    except Exception as e:
        return f"❌ Error testing thumbnails: {e}"

@app.route('/debug_records')
def debug_records():
    """Debug route to check record and points system"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        # Get some sample data
        pending_count = mongo_db.records.count_documents({"status": "pending"})
        approved_count = mongo_db.records.count_documents({"status": "approved"})
        total_users = mongo_db.users.count_documents({})
        total_levels = mongo_db.levels.count_documents({})
        
        # Get a sample pending record
        sample_record = mongo_db.records.find_one({"status": "pending"})
        
        # Get a sample user with points
        sample_user = mongo_db.users.find_one({"points": {"$gt": 0}})
        
        # Get a sample level
        sample_level = mongo_db.levels.find_one({})
        
        results = [
            f"📊 Database Status:",
            f"- Pending records: {pending_count}",
            f"- Approved records: {approved_count}",
            f"- Total users: {total_users}",
            f"- Total levels: {total_levels}",
            "",
            f"🔍 Sample Data:",
        ]
        
        if sample_record:
            results.append(f"- Sample pending record: ID {sample_record['_id']}, Progress {sample_record.get('progress', 'N/A')}%")
        else:
            results.append("- No pending records found")
        
        if sample_user:
            results.append(f"- Sample user with points: {sample_user.get('username', 'N/A')} ({sample_user.get('points', 0)} points)")
        else:
            results.append("- No users with points found")
        
        if sample_level:
            results.append(f"- Sample level: {sample_level.get('name', 'N/A')} (Position {sample_level.get('position', 'N/A')}, Points {sample_level.get('points', 'N/A')})")
        else:
            results.append("- No levels found")
        
        # Test points calculation
        if sample_record and sample_level:
            test_record = dict(sample_record)
            test_record['status'] = 'approved'
            test_points = calculate_record_points(test_record, sample_level)
            results.append(f"- Test points calculation: {test_points} points for {test_record.get('progress', 'N/A')}% on {sample_level.get('name', 'N/A')}")
        
        return f"""
        <h2>🔧 Record System Debug</h2>
        <div style="font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px;">
            {'<br>'.join(results)}
        </div>
        <br>
        <p><a href="/admin" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🏠 Back to Admin</a></p>
        """
        
    except Exception as e:
        return f"❌ Error debugging records: {e}"

@app.route('/quick_fix')
def quick_fix():
    """Quick fix for common issues"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        results = []
        
        # 1. Fix missing points in levels
        levels_without_points = mongo_db.levels.count_documents({"points": {"$exists": False}})
        if levels_without_points > 0:
            # Update levels without points
            for level in mongo_db.levels.find({"points": {"$exists": False}}):
                position = level.get('position', 1)
                is_legacy = level.get('is_legacy', False)
                level_type = level.get('level_type', 'Level')
                points = calculate_level_points(position, is_legacy, level_type)
                
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": points}}
                )
            
            results.append(f"✅ Fixed {levels_without_points} levels without points")
        
        # 2. Fix missing points in users
        users_without_points = mongo_db.users.count_documents({"points": {"$exists": False}})
        if users_without_points > 0:
            mongo_db.users.update_many(
                {"points": {"$exists": False}},
                {"$set": {"points": 0}}
            )
            results.append(f"✅ Fixed {users_without_points} users without points")
        
        # 3. Recalculate all user points
        users_with_records = mongo_db.records.distinct("user_id", {"status": "approved"})
        points_fixed = 0
        for user_id in users_with_records:
            try:
                update_user_points(user_id)
                points_fixed += 1
            except Exception as e:
                print(f"Error updating points for user {user_id}: {e}")
        
        results.append(f"✅ Recalculated points for {points_fixed}/{len(users_with_records)} users")
        
        # 4. Fix missing min_percentage in levels
        levels_without_min_pct = mongo_db.levels.count_documents({"min_percentage": {"$exists": False}})
        if levels_without_min_pct > 0:
            mongo_db.levels.update_many(
                {"min_percentage": {"$exists": False}},
                {"$set": {"min_percentage": 100}}
            )
            results.append(f"✅ Fixed {levels_without_min_pct} levels without min_percentage")
        
        # 5. Clear levels cache
        global levels_cache
        levels_cache.clear()
        results.append("✅ Cleared levels cache")
        
        return f"""
        <h2>⚡ Quick Fix Complete!</h2>
        <div style="font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px;">
            {'<br>'.join(results)}
        </div>
        <br>
        <p><a href="/admin" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🏠 Back to Admin</a></p>
        <p><a href="/debug_records" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔍 Debug Records</a></p>
        <p><a href="/fix_all_points" style="background: #ffc107; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔧 Fix All Points</a></p>
        """
        
    except Exception as e:
        return f"❌ Error in quick fix: {e}"

@app.route('/fix_all_points')
def fix_all_points():
    """Fix all user points immediately"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        # Get all users who have approved records
        users_with_records = mongo_db.records.distinct("user_id", {"status": "approved"})
        
        results = []
        total_fixed = 0
        
        for user_id in users_with_records:
            try:
                # Get user info
                user = mongo_db.users.find_one({"_id": user_id})
                if not user:
                    continue
                
                old_points = user.get('points', 0)
                
                # Recalculate points
                update_user_points(user_id)
                
                # Get new points
                updated_user = mongo_db.users.find_one({"_id": user_id})
                new_points = updated_user.get('points', 0) if updated_user else 0
                
                if new_points != old_points:
                    results.append(f"✅ {user.get('username', 'Unknown')}: {old_points} → {new_points} points")
                    total_fixed += 1
                else:
                    results.append(f"✓ {user.get('username', 'Unknown')}: {new_points} points (no change)")
                    
            except Exception as e:
                results.append(f"❌ Error fixing user {user_id}: {e}")
        
        # Also fix users with 0 points who should have points
        zero_point_users = mongo_db.users.count_documents({"points": {"$lte": 0}})
        if zero_point_users > 0:
            mongo_db.users.update_many(
                {"points": {"$exists": False}},
                {"$set": {"points": 0}}
            )
        
        return f"""
        <h2>🔧 All User Points Fixed!</h2>
        <div style="font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px; max-height: 400px; overflow-y: auto;">
            <strong>Fixed {total_fixed} users with point changes:</strong><br><br>
            {'<br>'.join(results)}
        </div>
        <br>
        <p><a href="/debug_records" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔍 Check Results</a></p>
        <p><a href="/admin" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🏠 Back to Admin</a></p>
        """
        
    except Exception as e:
        return f"❌ Error fixing all points: {e}"

@app.route('/admin/reset_user/<int:user_id>', methods=['POST'])
def admin_reset_user(user_id):
    """Reset a user's points and records (admin only)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get user info
        user = mongo_db.users.find_one({"_id": user_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Count records before deletion
        record_count = mongo_db.records.count_documents({"user_id": user_id})
        old_points = user.get('points', 0)
        
        # Delete all user's records
        mongo_db.records.delete_many({"user_id": user_id})
        
        # Reset user points to 0
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"points": 0}}
        )
        
        # Log admin action
        log_admin_action(
            admin_username,
            "User Reset",
            f"Reset {user['username']}: Deleted {record_count} records, Points {old_points} → 0"
        )
        
        flash(f'✅ Reset {user["username"]}: Deleted {record_count} records and reset {old_points} points to 0', 'success')
        
    except Exception as e:
        flash(f'Error resetting user: {str(e)}', 'danger')
        print(f"Admin reset user error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_users'))

@app.route('/virtual')
def virtual_list():
    """Virtual scrolling version - only renders visible items"""
    main_list = get_cached_levels(is_legacy=False)
    
    if not main_list:
        return redirect(url_for('instant_load'))
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RTL - Virtual List</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            .virtual-container {{ height: 600px; overflow-y: auto; border: 1px solid #ddd; }}
            .level-item {{ 
                height: 80px; padding: 10px; border-bottom: 1px solid #eee; 
                display: flex; align-items: center; background: white;
            }}
            .level-img {{ width: 80px; height: 45px; margin-right: 15px; border-radius: 4px; object-fit: cover; }}
            .level-info {{ flex: 1; }}
            .level-name {{ font-weight: bold; margin-bottom: 5px; }}
            .level-meta {{ color: #666; font-size: 14px; }}
            .position {{ 
                background: #007bff; color: white; padding: 5px 10px; 
                border-radius: 15px; margin-right: 15px; font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 RTL - Virtual List (Ultra Fast)</h1>
        <p>Showing {len(main_list)} levels with virtual scrolling</p>
        <p><a href="/">← Back to paginated view</a></p>
        
        <div class="virtual-container" id="container">
            <!-- Items will be rendered by JavaScript -->
        </div>
        
        <script>
            const levels = {main_list};
            const container = document.getElementById('container');
            const itemHeight = 100;
            const containerHeight = 600;
            const visibleItems = Math.ceil(containerHeight / itemHeight) + 2;
            
            let scrollTop = 0;
            
            function renderItems() {{
                const startIndex = Math.floor(scrollTop / itemHeight);
                const endIndex = Math.min(startIndex + visibleItems, levels.length);
                
                container.innerHTML = '';
                container.style.height = levels.length * itemHeight + 'px';
                container.style.position = 'relative';
                
                for (let i = startIndex; i < endIndex; i++) {{
                    const level = levels[i];
                    const item = document.createElement('div');
                    item.className = 'level-item';
                    item.style.position = 'absolute';
                    item.style.top = i * itemHeight + 'px';
                    item.style.width = '100%';
                    item.style.boxSizing = 'border-box';
                    
                    const thumbUrl = level.thumbnail_url || '';
                    const imgSrc = thumbUrl.includes('youtube') ? 
                        thumbUrl.replace('maxresdefault', 'mqdefault') : thumbUrl;
                    
                    item.innerHTML = `
                        <div class="position">${{level.position}}</div>
                        ${{imgSrc ? `<img src="${{imgSrc}}" class="level-img" loading="lazy">` : 
                          '<div class="level-img" style="background: #ddd; display: flex; align-items: center; justify-content: center; font-size: 12px;">No Image</div>'}}
                        <div class="level-info">
                            <div class="level-name">${{level.name}}</div>
                            <div class="level-meta">by ${{level.creator}} • verified by ${{level.verifier}} • ${{level.difficulty}}/10 • ${{level.points}} points</div>
                        </div>
                    `;
                    
                    container.appendChild(item);
                }}
            }}
            
            container.addEventListener('scroll', () => {{
                scrollTop = container.scrollTop;
                renderItems();
            }});
            
            renderItems();
        </script>
    </body>
    </html>
    """



@app.route('/instant_load')
def instant_load():
    """NUCLEAR LOAD - Load everything with maximum optimization"""
    import time
    
    start_time = time.time()
    try:
        # Optimized query with thumbnails - should still be fast
        main_levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1))
        
        legacy_levels = list(mongo_db.levels.find(
            {"is_legacy": True},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1))
        
        # Cache everything
        levels_cache['main_list'] = main_levels
        levels_cache['legacy_list'] = legacy_levels
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        end_time = time.time()
        
        return f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1>✅ Loaded Successfully!</h1>
            <p>Load time: {end_time - start_time:.3f} seconds</p>
            <p>Main levels: {len(main_levels)} | Legacy: {len(legacy_levels)}</p>
            <br>
            <a href="/" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🚀 Go to Main List</a>
            <br><br>
            <a href="/legacy">View Legacy List</a>
        </div>
        """
        
    except Exception as e:
        return f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1>❌ Load Failed</h1>
            <p>Error: {e}</p>
            <a href="/debug_db">Check Database</a> | <a href="/fast">Use Sample Data</a>
        </div>
        """

@app.route('/load_images')
def load_images():
    """Load thumbnail URLs for existing cached levels"""
    import time
    
    start_time = time.time()
    try:
        # Get current cached levels
        main_levels = levels_cache.get('main_list', [])
        legacy_levels = levels_cache.get('legacy_list', [])
        
        if not main_levels and not legacy_levels:
            return """
            <div style="text-align: center; padding: 50px; font-family: Arial;">
                <h1>⚠️ No Levels Loaded</h1>
                <p>Please load levels first</p>
                <a href="/instant_load">Load Levels First</a>
            </div>
            """
        
        # Get level IDs to update
        main_ids = [level['_id'] for level in main_levels]
        legacy_ids = [level['_id'] for level in legacy_levels]
        
        # Load thumbnail URLs only
        main_thumbnails = {doc['_id']: doc.get('thumbnail_url', '') 
                          for doc in mongo_db.levels.find(
                              {"_id": {"$in": main_ids}}, 
                              {"_id": 1, "thumbnail_url": 1}
                          )}
        
        legacy_thumbnails = {doc['_id']: doc.get('thumbnail_url', '') 
                            for doc in mongo_db.levels.find(
                                {"_id": {"$in": legacy_ids}}, 
                                {"_id": 1, "thumbnail_url": 1}
                            )}
        
        # Update cached levels with thumbnails
        for level in main_levels:
            level['thumbnail_url'] = main_thumbnails.get(level['_id'], '')
            
        for level in legacy_levels:
            level['thumbnail_url'] = legacy_thumbnails.get(level['_id'], '')
        
        # Update cache
        levels_cache['main_list'] = main_levels
        levels_cache['legacy_list'] = legacy_levels
        
        end_time = time.time()
        
        return f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1>📷 Images Loaded!</h1>
            <p>Load time: {end_time - start_time:.3f} seconds</p>
            <p>Updated {len(main_levels)} main + {len(legacy_levels)} legacy levels</p>
            <br>
            <a href="/" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🚀 View Main List</a>
            <br><br>
            <a href="/legacy">View Legacy List</a>
        </div>
        """
        
    except Exception as e:
        return f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h1>❌ Image Load Failed</h1>
            <p>Error: {e}</p>
            <a href="/">Back to Main</a>
        </div>
        """

@app.route('/preload_cache')
def preload_cache():
    """Preload cache immediately"""
    try:
        print("Loading main levels...")
        main_count = len(get_cached_levels(is_legacy=False))
        print("Loading legacy levels...")  
        legacy_count = len(get_cached_levels(is_legacy=True))
        return f"Cache loaded! Main: {main_count}, Legacy: {legacy_count}. <a href='/'>Check main list</a>"
    except Exception as e:
        return f"Cache loading failed: {e}"

@app.route('/debug_db')
def debug_db():
    """Debug database contents and check for Base64 images"""
    try:
        # Count total documents
        total_count = mongo_db.levels.count_documents({})
        main_count = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
        
        # Check for Base64 images (huge performance killer)
        base64_count = mongo_db.levels.count_documents({"thumbnail_url": {"$regex": "^data:"}})
        
        # Get sample thumbnail URLs to see what we're dealing with
        sample_thumbs = list(mongo_db.levels.find(
            {"thumbnail_url": {"$exists": True, "$ne": ""}}, 
            {"name": 1, "thumbnail_url": 1}
        ).limit(3))
        
        # Check thumbnail URL sizes
        thumb_info = []
        for level in sample_thumbs:
            thumb_url = level.get('thumbnail_url', '')
            if thumb_url:
                size_info = f"Length: {len(thumb_url)}"
                if thumb_url.startswith('data:'):
                    size_info += " (BASE64 - HUGE!)"
                elif 'youtube' in thumb_url:
                    size_info += " (YouTube - OK)"
                else:
                    size_info += " (URL - OK)"
                thumb_info.append(f"{level['name']}: {size_info}")
        
        return f"""
        <h2>Database Debug Info</h2>
        <p>Total documents: {total_count}</p>
        <p>Main levels: {main_count}</p>
        <p>Legacy levels: {legacy_count}</p>
        <p><strong>Base64 images: {base64_count}</strong> {'⚠️ PERFORMANCE KILLER!' if base64_count > 0 else '✅ Good'}</p>
        
        <h3>Sample Thumbnail Info:</h3>
        <pre>{'<br>'.join(thumb_info) if thumb_info else 'No thumbnails found'}</pre>
        
        <p><a href='/'>Back to main</a> | <a href='/fix_base64'>Fix Base64 Images</a></p>
        """
    except Exception as e:
        return f"Database error: {e}"

@app.route('/debug')
def debug_info():
    """Show debug information"""
    import time
    
    # Test basic connection
    start_time = time.time()
    try:
        mongo_client.admin.command('ping', maxTimeMS=2000)
        ping_time = time.time() - start_time
        ping_status = f"✅ {ping_time:.2f}s"
    except Exception as e:
        ping_time = time.time() - start_time
        ping_status = f"❌ {ping_time:.2f}s - {str(e)}"
    
    # Check cache status
    cache_status = {
        'main_list': len(levels_cache['main_list']) if levels_cache['main_list'] else 'Empty',
        'legacy_list': len(levels_cache['legacy_list']) if levels_cache['legacy_list'] else 'Empty',
        'last_updated': levels_cache['last_updated'].strftime('%Y-%m-%d %H:%M:%S') if levels_cache['last_updated'] else 'Never'
    }
    
    return f"""
    <h1>Debug Information</h1>
    <h2>Database Connection</h2>
    <p><strong>Ping Test:</strong> {ping_status}</p>
    <p><strong>MongoDB URI:</strong> {mongodb_uri[:50]}...</p>
    
    <h2>Cache Status</h2>
    <p><strong>Main List:</strong> {cache_status['main_list']} items</p>
    <p><strong>Legacy List:</strong> {cache_status['legacy_list']} items</p>
    <p><strong>Last Updated:</strong> {cache_status['last_updated']}</p>
    
    <h2>Quick Actions</h2>
    <p><a href="/fast">Fast Test Page</a> (no database)</p>
    <p><a href="/preload_cache">Preload Cache</a></p>
    <p><a href="/clear_cache">Clear Cache</a></p>
    <p><a href="/">Main List</a></p>
    """

@app.route('/test_legacy_db')
def test_legacy_db():
    """Test route specifically for legacy database queries"""
    try:
        # Test basic connection
        mongo_client.admin.command('ping', maxTimeMS=10000)
        
        # Test legacy count
        legacy_count = mongo_db.levels.count_documents({"is_legacy": True}, maxTimeMS=30000)
        
        # Test legacy query with limit
        legacy_sample = list(mongo_db.levels.find(
            {"is_legacy": True}, 
            {"name": 1, "position": 1}
        ).limit(5).max_time_ms(30000))
        
        return f"""
        <h1>Legacy Database Test</h1>
        <p><strong>Connection:</strong> ✅ OK</p>
        <p><strong>Legacy Count:</strong> {legacy_count}</p>
        <p><strong>Sample Legacy Levels:</strong></p>
        <ul>
        {''.join([f'<li>{level.get("name", "Unknown")} (pos: {level.get("position", "N/A")})</li>' for level in legacy_sample])}
        </ul>
        <p><strong>MongoDB URI (first 50 chars):</strong> {mongodb_uri[:50]}...</p>
        """
    except Exception as e:
        import traceback
        return f"""
        <h1>Legacy Database Test - ERROR</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <pre>{traceback.format_exc()}</pre>
        """

@app.route('/health')
def health_check():
    """Health check endpoint for database connectivity"""
    try:
        # Quick ping test
        mongo_client.admin.command('ping', maxTimeMS=5000)
        
        # Quick count test
        level_count = mongo_db.levels.count_documents({}, maxTimeMS=5000)
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'level_count': level_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, 503

@app.route('/test_discord')
def test_discord():
    """Test route to check Discord integration"""
    import os
    
    # Check environment variables
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    website_url = os.environ.get('WEBSITE_URL')
    
    result = f"""
    <h1>Discord Integration Test</h1>
    <p><strong>Discord Available:</strong> {DISCORD_AVAILABLE}</p>
    <p><strong>Webhook URL:</strong> {'✅ Set' if webhook_url else '❌ Missing'}</p>
    <p><strong>Website URL:</strong> {website_url or '❌ Missing'}</p>
    """
    
    if webhook_url:
        result += f"<p><strong>Webhook (first 50 chars):</strong> {webhook_url[:50]}...</p>"
    
    try:
        if DISCORD_AVAILABLE:
            notify_record_submitted('TestUser', 'Test Level', 99, 'https://youtube.com/test')
            result += "<p>✅ Discord test notification sent!</p>"
        else:
            result += "<p>❌ Discord integration not available</p>"
    except Exception as e:
        result += f"<p>❌ Discord test failed: {str(e)}</p>"
        import traceback
        result += f"<pre>{traceback.format_exc()}</pre>"
    
    return result

@app.route('/')
def index():
    """AUTO-LOAD - Instantly loads everything automatically"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Show 10 levels per page for maximum speed
    
    main_list = get_cached_levels(is_legacy=False)
    
    # If no cache, auto-load it now
    if not main_list:
        try:
            print("Auto-loading main levels...")
            main_list = list(mongo_db.levels.find(
                {"is_legacy": False},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
            ).sort("position", 1))
            
            # Cache it
            levels_cache['main_list'] = main_list
            levels_cache['last_updated'] = datetime.now(timezone.utc)
            print(f"Auto-loaded {len(main_list)} levels")
            
        except Exception as e:
            print(f"Auto-load failed: {e}")
            # Fallback to sample data
            main_list = [
                {"_id": 1, "name": "Loading failed - try /debug_db", "creator": "System", "verifier": "System", "position": 1, "points": 0, "level_id": "error", "difficulty": 5}
            ]
    
    # Pagination
    total_levels = len(main_list)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_levels = main_list[start_idx:end_idx]
    
    # Pagination info
    has_prev = page > 1
    has_next = end_idx < total_levels
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    total_pages = (total_levels + per_page - 1) // per_page
    
    return render_template('index.html', 
                         levels=paginated_levels,
                         page=page,
                         has_prev=has_prev,
                         has_next=has_next,
                         prev_page=prev_page,
                         next_page=next_page,
                         total_pages=total_pages,
                         total_levels=total_levels)

# Routes

@app.route('/legacy')
def legacy():
    """AUTO-LOAD - Instantly loads legacy levels automatically"""
    legacy_list = get_cached_levels(is_legacy=True)
    
    # If no cache, auto-load it now
    if not legacy_list:
        try:
            print("Auto-loading legacy levels...")
            legacy_list = list(mongo_db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
            ).sort("position", 1))
            
            # Cache it
            levels_cache['legacy_list'] = legacy_list
            levels_cache['last_updated'] = datetime.now(timezone.utc)
            print(f"Auto-loaded {len(legacy_list)} legacy levels")
            
        except Exception as e:
            print(f"Legacy auto-load failed: {e}")
            legacy_list = []
    
    return render_template('legacy.html', levels=legacy_list)

@app.route('/timemachine')
def timemachine():
    selected_date = request.args.get('date')
    levels = []
    
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, '%Y-%m-%d')
            # Get levels that existed on or before the selected date
            levels = list(mongo_db.levels.find({
                "date_added": {"$lte": target_date},
                "is_legacy": False
            }, max_time_ms=60000).sort("position", 1))
        except ValueError:
            flash('Invalid date format', 'danger')
    
    return render_template('timemachine.html', levels=levels, selected_date=selected_date)

@app.route('/level/<level_id>')
def level_detail(level_id):
    try:
        level = mongo_db.levels.find_one({"_id": int(level_id)}, max_time_ms=5000)
        if not level:
            flash('Level not found', 'danger')
            return redirect(url_for('index'))
        
        # Get approved records with user info - optimized with timeout and limit
        records = list(mongo_db.records.aggregate([
            {"$match": {"level_id": int(level_id), "status": "approved"}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$limit": 100}  # Limit to first 100 records for performance
        ], maxTimeMS=5000))
        
        return render_template('level_detail.html', level=level, records=records)
    except (ValueError, InvalidId):
        flash('Invalid level ID', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = mongo_db.users.find_one({"username": username}, max_time_ms=60000)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['_id']
            session['is_admin'] = user.get('is_admin', False)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if mongo_db.users.find_one({"username": username}, max_time_ms=60000):
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if mongo_db.users.find_one({"email": email}, max_time_ms=60000):
            flash('Email already exists', 'danger')
            return render_template('register.html')
        
        # Get next user ID
        last_user = mongo_db.users.find_one({}, sort=[("_id", -1)], max_time_ms=60000)
        next_id = (last_user['_id'] + 1) if last_user else 1
        
        # Create new user
        new_user = {
            "_id": next_id,
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "is_admin": False,
            "points": 0,
            "date_joined": datetime.now(timezone.utc)
        }
        
        mongo_db.users.insert_one(new_user)
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/toggle_theme')
def toggle_theme():
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'theme': new_theme, 'status': 'success'}
    
    return redirect(request.referrer or url_for('index'))

@app.route('/auth/google')
def google_login():
    if not google:
        flash('Google Sign-In is not configured', 'danger')
        return redirect(url_for('login'))
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    if not google:
        flash('Google Sign-In is not configured', 'danger')
        return redirect(url_for('login'))
    
    try:
        token = google.authorize_access_token()
        resp = google.get('https://openidconnect.googleapis.com/v1/userinfo', token=token)
        user_info = resp.json()
        
        google_id = user_info['sub']
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists with this Google ID
        user = mongo_db.users.find_one({"google_id": google_id})
        
        if not user:
            # Check if user exists with this email
            user = mongo_db.users.find_one({"email": email})
            if user:
                # Link Google account to existing user
                mongo_db.users.update_one(
                    {"_id": user['_id']},
                    {"$set": {"google_id": google_id}}
                )
            else:
                # Create new user
                username = name
                counter = 1
                while mongo_db.users.find_one({"username": username}):
                    username = f"{name}{counter}"
                    counter += 1
                
                # Get next user ID
                last_user = mongo_db.users.find_one(sort=[("_id", -1)])
                next_id = (last_user['_id'] + 1) if last_user else 1
                
                user = {
                    "_id": next_id,
                    "username": username,
                    "email": email,
                    "password_hash": "",
                    "google_id": google_id,
                    "is_admin": False,
                    "points": 0,
                    "date_joined": datetime.now(timezone.utc)
                }
                mongo_db.users.insert_one(user)
        
        # Log in the user
        session['user_id'] = user['_id']
        session['is_admin'] = user.get('is_admin', False)
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user = mongo_db.users.find_one({"_id": session['user_id']}, max_time_ms=60000)
    user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": session['user_id']}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"}
    ]))
    
    return render_template('profile.html', user=user, records=user_records)

@app.route('/submit_record', methods=['GET', 'POST'])
def submit_record():
    if 'user_id' not in session:
        flash('Please log in to submit a record', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Validate form data
        level_id_str = request.form.get('level_id', '').strip()
        progress_str = request.form.get('progress', '').strip()
        video_url = request.form.get('video_url', '').strip()
        
        # Check for empty fields - use cached levels for faster response
        if not level_id_str:
            flash('Please select a level', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
            
        if not progress_str:
            flash('Please enter your progress percentage', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
            
        if not video_url:
            flash('Please provide a video URL', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        # Convert to integers
        try:
            level_id = int(level_id_str)
            progress = int(progress_str)
        except ValueError:
            flash('Invalid level ID or progress value', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        # Validate progress range
        if progress < 1 or progress > 100:
            flash('Progress must be between 1 and 100', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        # Check if level exists - fast query with projection
        level = mongo_db.levels.find_one({"_id": level_id}, {"name": 1, "min_percentage": 1}, max_time_ms=3000)
        if not level:
            flash('Selected level does not exist', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        # Check minimum progress requirement
        min_progress = level.get('min_percentage', 100)
        if progress < min_progress:
            flash(f'This level requires at least {min_progress}% progress', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        # Get next record ID
        last_record = mongo_db.records.find_one(sort=[("_id", -1)])
        next_id = (last_record['_id'] + 1) if last_record else 1
        
        new_record = {
            "_id": next_id,
            "user_id": session['user_id'],
            "level_id": level_id,
            "progress": progress,
            "video_url": video_url,
            "status": "pending",
            "date_submitted": datetime.now(timezone.utc)
        }
        
        mongo_db.records.insert_one(new_record)
        
        # Send Discord notification
        try:
            user = mongo_db.users.find_one({"_id": session['user_id']})
            username = user['username'] if user else 'Unknown'
            print(f"🔔 Sending Discord notification for {username} - {level['name']} - {progress}%")
            
            # Try the imported function first
            if DISCORD_AVAILABLE:
                notify_record_submitted(username, level['name'], progress, video_url)
            else:
                # Fallback: send Discord notification directly
                send_discord_notification_direct(username, level['name'], progress, video_url)
            
            print(f"✅ Discord notification sent successfully")
        except Exception as e:
            print(f"❌ Discord notification error: {e}")
            import traceback
            traceback.print_exc()
        
        flash('Record submitted successfully! It will be reviewed by moderators.', 'success')
        return redirect(url_for('profile'))
    
    # Use cached levels - if no cache, redirect to load
    levels = get_cached_levels(is_legacy=False)
    if not levels:
        flash('Please load levels first', 'info')
        return redirect(url_for('instant_load'))
    return render_template('submit_record.html', levels=levels)

# Admin routes
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    pending_records = list(mongo_db.records.aggregate([
        {"$match": {"status": "pending"}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "_id",
            "as": "user"
        }},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$user"},
        {"$unwind": "$level"}
    ]))
    
    return render_template('admin/index.html', pending_records=pending_records)

@app.route('/admin/levels', methods=['GET', 'POST'])
def admin_levels():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get next level ID
        last_level = mongo_db.levels.find_one(sort=[("_id", -1)])
        next_id = (last_level['_id'] + 1) if last_level else 1
        
        name = request.form.get('name')
        creator = request.form.get('creator')
        verifier = request.form.get('verifier')
        level_id = request.form.get('level_id')
        video_url = request.form.get('video_url')
        thumbnail_url = request.form.get('thumbnail_url')
        
        # Handle file upload - save to JSON and convert to base64
        if 'thumbnail_file' in request.files:
            file = request.files['thumbnail_file']
            if file and file.filename:
                import base64
                import json
                import time
                file_data = file.read()
                file_ext = file.filename.split('.')[-1].lower()
                mime_type = f'image/{file_ext}' if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else 'image/png'
                base64_data = base64.b64encode(file_data).decode('utf-8')
                thumbnail_url = f'data:{mime_type};base64,{base64_data}'
                
                # Save to JSON file
                json_file = 'thumbnails.json'
                try:
                    with open(json_file, 'r') as f:
                        thumbnails = json.load(f)
                except:
                    thumbnails = {}
                
                thumbnails[name] = {
                    'base64': base64_data,
                    'mime_type': mime_type,
                    'filename': file.filename,
                    'timestamp': int(time.time())
                }
                
                with open(json_file, 'w') as f:
                    json.dump(thumbnails, f, indent=2)
                    
                print(f"Thumbnail uploaded: {mime_type}, size: {len(base64_data)} chars")
                print(f"Thumbnail URL: {thumbnail_url[:100]}...")
        
        description = request.form.get('description')
        difficulty = float(request.form.get('difficulty'))
        position = int(request.form.get('position'))
        is_legacy = 'is_legacy' in request.form
        
        points_str = request.form.get('points')
        min_percentage = int(request.form.get('min_percentage', '100'))
        
        # Calculate points
        if points_str and points_str.strip():
            points = int(float(points_str))
        else:
            level_type = request.form.get('level_type', 'Level')
            points = calculate_level_points(position, is_legacy, level_type)
        
        # Shift existing levels at this position and below
        shift_level_positions(position, is_legacy, 1)
        
        new_level = {
            "_id": next_id,
            "name": name,
            "creator": creator,
            "verifier": verifier,
            "level_id": level_id or None,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "description": description,
            "difficulty": difficulty,
            "position": position,
            "is_legacy": is_legacy,
            "level_type": request.form.get('level_type', 'Level'),
            "date_added": datetime.now(timezone.utc),
            "points": points,
            "min_percentage": min_percentage
        }
        
        mongo_db.levels.insert_one(new_level)
        
        # Clear cache since levels changed
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Recalculate points for all levels after position changes
        recalculate_all_points()
        
        # Log level placement to changelog
        above_level = None
        below_level = None
        
        # Find levels above and below
        if position > 1:
            above_level_doc = mongo_db.levels.find_one({"position": position - 1, "is_legacy": is_legacy})
            if above_level_doc:
                above_level = above_level_doc['name']
        
        below_level_doc = mongo_db.levels.find_one({"position": position + 1, "is_legacy": is_legacy})
        if below_level_doc:
            below_level = below_level_doc['name']
        
        log_level_change(
            action="placed",
            level_name=name,
            admin_username=session.get('username', 'Unknown'),
            position=position,
            above_level=above_level,
            below_level=below_level,
            list_type="legacy" if is_legacy else "main"
        )
        
        # Save history
        history_entry = {
            "level_id": next_id,
            "action": "added",
            "new_data": new_level,
            "timestamp": datetime.now(timezone.utc)
        }
        mongo_db.level_history.insert_one(history_entry)
        
        flash('Level added successfully!', 'success')
        return redirect(url_for('admin_levels'))
    
    # Try to use cached data first, fallback to database
    main_cache = levels_cache.get('main_list', []) or []
    legacy_cache = levels_cache.get('legacy_list', []) or []
    
    if main_cache or legacy_cache:
        # Use cached data
        levels = main_cache + legacy_cache
    else:
        # Fallback to database with minimal fields
        levels = list(mongo_db.levels.find({}, {
            "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
            "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1
        }).sort([("is_legacy", 1), ("position", 1)]))
    
    # Debug: Check thumbnail URLs and file existence
    import os
    for level in levels:
        thumb = level.get('thumbnail_url', '')
        if thumb:
            if thumb.startswith('/static/uploads/'):
                file_path = thumb[1:]  # Remove leading slash
                exists = os.path.exists(file_path)
                print(f"Level {level['name']}: FILE {file_path} - {'EXISTS' if exists else 'MISSING'}")
            else:
                print(f"Level {level['name']}: URL {thumb}")
    
    return render_template('admin/levels.html', levels=levels)

@app.route('/admin/edit_level', methods=['POST'])
def admin_edit_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    db_level_id = int(request.form.get('level_id'))
    game_level_id = request.form.get('game_level_id')

    
    level = mongo_db.levels.find_one({"_id": db_level_id})
    thumbnail_url = request.form.get('thumbnail_url') or level.get('thumbnail_url', '')
    
    # Handle position changes
    old_position = level['position']
    old_is_legacy = level.get('is_legacy', False)
    

    
    # Handle file upload - save to JSON and convert to base64
    if 'thumbnail_file' in request.files:
        file = request.files['thumbnail_file']
        if file and file.filename:
            import base64
            import json
            import time
            file_data = file.read()
            file_ext = file.filename.split('.')[-1].lower()
            mime_type = f'image/{file_ext}' if file_ext in ['png', 'jpg', 'jpeg', 'gif', 'webp'] else 'image/png'
            base64_data = base64.b64encode(file_data).decode('utf-8')
            thumbnail_url = f'data:{mime_type};base64,{base64_data}'
            
            # Save to JSON file
            json_file = 'thumbnails.json'
            level_name = request.form.get('name', 'unknown')
            try:
                with open(json_file, 'r') as f:
                    thumbnails = json.load(f)
            except:
                thumbnails = {}
            
            thumbnails[level_name] = {
                'base64': base64_data,
                'mime_type': mime_type,
                'filename': file.filename,
                'timestamp': int(time.time())
            }
            
            with open(json_file, 'w') as f:
                json.dump(thumbnails, f, indent=2)
    
    points_str = request.form.get('points')
    min_percentage = int(request.form.get('min_percentage', '100'))
    position = int(request.form.get('position'))
    is_legacy = 'is_legacy' in request.form
    
    # Handle position shifting if position changed
    if position != old_position or is_legacy != old_is_legacy:
        if is_legacy == old_is_legacy:
            # Same list, just moving position
            if old_position < position:
                # Moving down: shift levels between old and new position up
                mongo_db.levels.update_many(
                    {"position": {"$gt": old_position, "$lte": position}, "is_legacy": is_legacy},
                    {"$inc": {"position": -1}}
                )
            elif old_position > position:
                # Moving up: shift levels between new and old position down
                mongo_db.levels.update_many(
                    {"position": {"$gte": position, "$lt": old_position}, "is_legacy": is_legacy},
                    {"$inc": {"position": 1}}
                )
        else:
            # Moving between lists
            # Remove from old list (shift positions down)
            mongo_db.levels.update_many(
                {"position": {"$gt": old_position}, "is_legacy": old_is_legacy},
                {"$inc": {"position": -1}}
            )
            # Add to new list (shift positions up)
            mongo_db.levels.update_many(
                {"position": {"$gte": position}, "is_legacy": is_legacy},
                {"$inc": {"position": 1}}
            )
    
    # Calculate points
    if points_str and points_str.strip():
        points = int(float(points_str))
    else:
        level_type = request.form.get('level_type', level.get('level_type', 'Level'))
        points = calculate_level_points(position, is_legacy, level_type)
    
    update_data = {
        "name": request.form.get('name'),
        "creator": request.form.get('creator'),
        "verifier": request.form.get('verifier'),
        "level_id": game_level_id if game_level_id and game_level_id.strip() else None,
        "video_url": request.form.get('video_url'),
        "thumbnail_url": thumbnail_url,
        "description": request.form.get('description'),
        "difficulty": float(request.form.get('difficulty')),
        "position": position,
        "is_legacy": is_legacy,
        "level_type": request.form.get('level_type', 'Level'),
        "points": points,
        "min_percentage": min_percentage
    }
    
    # Save history before updating
    history_entry = {
        "level_id": db_level_id,
        "action": "updated",
        "old_data": level,
        "new_data": update_data,
        "timestamp": datetime.now(timezone.utc)
    }
    mongo_db.level_history.insert_one(history_entry)
    
    mongo_db.levels.update_one({"_id": db_level_id}, {"$set": update_data})
    
    # Log level changes to changelog
    if position != old_position or is_legacy != old_is_legacy:
        level_name = update_data['name']
        
        if is_legacy != old_is_legacy:
            # Moved between lists
            if is_legacy:
                log_level_change(
                    action="legacy",
                    level_name=level_name,
                    admin_username=session.get('username', 'Unknown'),
                    old_position=old_position,
                    list_type="legacy"
                )
            else:
                log_level_change(
                    action="placed",
                    level_name=level_name,
                    admin_username=session.get('username', 'Unknown'),
                    position=position,
                    list_type="main"
                )
        else:
            # Just moved position within same list
            above_level = None
            below_level = None
            
            # Find levels above and below new position
            if position > 1:
                above_level_doc = mongo_db.levels.find_one({"position": position - 1, "is_legacy": is_legacy})
                if above_level_doc:
                    above_level = above_level_doc['name']
            
            below_level_doc = mongo_db.levels.find_one({"position": position + 1, "is_legacy": is_legacy})
            if below_level_doc:
                below_level = below_level_doc['name']
            
            log_level_change(
                action="moved",
                level_name=level_name,
                admin_username=session.get('username', 'Unknown'),
                old_position=old_position,
                new_position=position,
                above_level=above_level,
                below_level=below_level,
                list_type="legacy" if is_legacy else "main"
            )
    
    # Clear cache since levels changed
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    
    # Recalculate points for all levels after position changes
    recalculate_all_points()
    
    flash('Level updated successfully!', 'success')
    return redirect(url_for('admin_levels') + '?updated=' + str(db_level_id))

@app.route('/admin/delete_level', methods=['POST'])
def admin_delete_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    # Get level info before deletion
    level = mongo_db.levels.find_one({"_id": level_id})
    if not level:
        flash('Level not found', 'danger')
        return redirect(url_for('admin_levels'))
    
    level_position = level['position']
    is_legacy = level.get('is_legacy', False)
    
    # Delete associated records
    mongo_db.records.delete_many({"level_id": level_id})
    
    # Save history before deleting
    history_entry = {
        "level_id": level_id,
        "action": "deleted",
        "old_data": level,
        "timestamp": datetime.now(timezone.utc)
    }
    mongo_db.level_history.insert_one(history_entry)
    
    # Delete the level
    mongo_db.levels.delete_one({"_id": level_id})
    
    # Log level removal to changelog
    log_level_change(
        action="removed",
        level_name=level['name'],
        admin_username=session.get('username', 'Unknown'),
        old_position=level_position,
        list_type="legacy" if is_legacy else "main"
    )
    
    # Clear cache since levels changed
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    
    # Shift positions of levels that were below the deleted level
    mongo_db.levels.update_many(
        {"position": {"$gt": level_position}, "is_legacy": is_legacy},
        {"$inc": {"position": -1}}
    )
    
    # Recalculate points for all levels after position changes
    recalculate_all_points()
    
    flash('Level deleted successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_legacy', methods=['POST'])
def admin_move_to_legacy():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    # Get level info before moving
    level = mongo_db.levels.find_one({"_id": level_id})
    if not level or level.get('is_legacy', False):
        flash('Level not found or already in legacy', 'danger')
        return redirect(url_for('admin_levels'))
    
    old_position = level['position']
    
    # Find the highest position in the legacy list
    highest_legacy = mongo_db.levels.find_one(
        {"is_legacy": True}, 
        sort=[("position", -1)]
    )
    new_position = 1 if not highest_legacy else highest_legacy['position'] + 1
    
    # Move level to legacy
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": True, "position": new_position}}
    )
    
    # Shift positions in the main list
    mongo_db.levels.update_many(
        {"position": {"$gt": old_position}, "is_legacy": False},
        {"$inc": {"position": -1}}
    )
    
    # Recalculate points for all levels after position changes
    recalculate_all_points()
    
    flash('Level moved to legacy list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_main', methods=['POST'])
def admin_move_to_main():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    position = int(request.form.get('position'))
    
    # Get level info before moving
    level = mongo_db.levels.find_one({"_id": level_id})
    if not level or not level.get('is_legacy', False):
        flash('Level not found or already in main list', 'danger')
        return redirect(url_for('admin_levels'))
    
    old_position = level['position']
    
    # Shift positions in the legacy list
    mongo_db.levels.update_many(
        {"position": {"$gt": old_position}, "is_legacy": True},
        {"$inc": {"position": -1}}
    )
    
    # Shift positions in the main list
    mongo_db.levels.update_many(
        {"position": {"$gte": position}, "is_legacy": False},
        {"$inc": {"position": 1}}
    )
    
    # Move level to main list
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": False, "position": position}}
    )
    
    # Recalculate points for all levels after position changes
    recalculate_all_points()
    
    flash('Level moved to main list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/approve_record/<int:record_id>', methods=['POST'])
def admin_approve_record(record_id):
    """Enhanced record approval with better error handling and debugging"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        print(f"DEBUG: Attempting to approve record {record_id}")
        
        # Get record with detailed error checking
        record = mongo_db.records.find_one({"_id": record_id})
        if not record:
            flash('Record not found', 'danger')
            print(f"DEBUG: Record {record_id} not found in database")
            return redirect(url_for('admin'))
        
        print(f"DEBUG: Found record: {record}")
        
        # Check if already approved
        if record.get('status') == 'approved':
            flash('Record is already approved', 'warning')
            return redirect(url_for('admin'))
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get user and level info with validation
        user = mongo_db.users.find_one({"_id": record['user_id']})
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        
        print(f"DEBUG: User found: {user is not None}, Level found: {level is not None}")
        
        if not user:
            flash('Error: User not found for this record', 'danger')
            return redirect(url_for('admin'))
        
        if not level:
            flash('Error: Level not found for this record', 'danger')
            return redirect(url_for('admin'))
        
        # Validate record data
        if not record.get('progress') or record['progress'] < 1 or record['progress'] > 100:
            flash('Error: Invalid progress value in record', 'danger')
            return redirect(url_for('admin'))
        
        print(f"DEBUG: About to approve record. Progress: {record['progress']}, Level points: {level.get('points', 'N/A')}")
        
        # Approve the record with timestamp
        approval_time = datetime.now(timezone.utc)
        update_result = mongo_db.records.update_one(
            {"_id": record_id},
            {"$set": {
                "status": "approved",
                "approved_by": admin_username,
                "approved_at": approval_time
            }}
        )
        
        print(f"DEBUG: Record update result: {update_result.modified_count} documents modified")
        
        # Calculate points for this specific record
        approved_record = dict(record)
        approved_record['status'] = 'approved'
        points_earned = calculate_record_points(approved_record, level)
        
        print(f"DEBUG: Points calculated: {points_earned}")
        
        # Get user's points before update
        old_points = user.get('points', 0)
        
        # Update user points (recalculate all)
        update_user_points(record['user_id'])
        
        # Get user's points after update
        updated_user = mongo_db.users.find_one({"_id": record['user_id']})
        new_points = updated_user.get('points', 0) if updated_user else 0
        
        print(f"DEBUG: User points - Before: {old_points}, After: {new_points}, Difference: {new_points - old_points}")
        
        # Log admin action with more details
        log_admin_action(
            admin_username,
            "Record Approved",
            f"Approved {user['username']}'s {record['progress']}% record on {level['name']} (Position #{level.get('position', '?')}) - Earned {points_earned} points (Total: {old_points} → {new_points})"
        )
        
        # Send Discord notification
        try:
            if DISCORD_AVAILABLE:
                notify_record_approved(
                    user['username'], 
                    level['name'], 
                    record['progress'], 
                    points_earned
                )
        except Exception as e:
            print(f"Discord notification error: {e}")
            # Don't let Discord errors break the approval process
        
        flash(f'✅ Record approved! {user["username"]} earned {points_earned} points for {record["progress"]}% on {level["name"]} (Total: {old_points} → {new_points} points)', 'success')
        
    except Exception as e:
        flash(f'Error approving record: {str(e)}', 'danger')
        print(f"Admin approve record error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin'))

@app.route('/admin/reject_record/<int:record_id>', methods=['POST'])
def admin_reject_record(record_id):
    """Enhanced record rejection with better error handling"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get record info before rejecting
        record = mongo_db.records.find_one({"_id": record_id})
        if not record:
            flash('Record not found', 'danger')
            return redirect(url_for('admin'))
        
        # Check if already rejected
        if record.get('status') == 'rejected':
            flash('Record is already rejected', 'warning')
            return redirect(url_for('admin'))
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get rejection reason from form if provided
        rejection_reason = request.form.get('reason', 'No reason provided')
        
        # Reject the record with timestamp and reason
        rejection_time = datetime.now(timezone.utc)
        mongo_db.records.update_one(
            {"_id": record_id},
            {"$set": {
                "status": "rejected",
                "rejected_by": admin_username,
                "rejected_at": rejection_time,
                "rejection_reason": rejection_reason
            }}
        )
        
        # Get user and level info for notifications
        user = mongo_db.users.find_one({"_id": record['user_id']})
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        
        if user and level:
            # Log admin action
            log_admin_action(
                admin_username,
                "Record Rejected",
                f"Rejected {user['username']}'s {record['progress']}% record on {level['name']} - Reason: {rejection_reason}"
            )
            
            # Send Discord notification
            try:
                if DISCORD_AVAILABLE:
                    notify_record_rejected(
                        user['username'], 
                        level['name'], 
                        record['progress']
                    )
            except Exception as e:
                print(f"Discord notification error: {e}")
            
            flash(f'❌ Record rejected: {user["username"]}\'s {record["progress"]}% on {level["name"]}', 'warning')
        else:
            flash('Record rejected (user/level info unavailable)', 'warning')
            
    except Exception as e:
        flash(f'Error rejecting record: {str(e)}', 'danger')
        print(f"Admin reject record error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin'))

@app.route('/admin/bulk_records', methods=['POST'])
def admin_bulk_records():
    """Bulk approve/reject records"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        action = request.form.get('action')  # 'approve' or 'reject'
        record_ids = request.form.getlist('record_ids')
        
        if not record_ids:
            flash('No records selected', 'warning')
            return redirect(url_for('admin'))
        
        # Convert to integers
        record_ids = [int(rid) for rid in record_ids]
        
        # Get admin info
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        success_count = 0
        error_count = 0
        
        for record_id in record_ids:
            try:
                if action == 'approve':
                    # Use existing approve logic
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and record.get('status') != 'approved':
                        user = mongo_db.users.find_one({"_id": record['user_id']})
                        level = mongo_db.levels.find_one({"_id": record['level_id']})
                        
                        if user and level:
                            mongo_db.records.update_one(
                                {"_id": record_id},
                                {"$set": {
                                    "status": "approved",
                                    "approved_by": admin_username,
                                    "approved_at": datetime.now(timezone.utc)
                                }}
                            )
                            update_user_points(record['user_id'])
                            success_count += 1
                        else:
                            error_count += 1
                    
                elif action == 'reject':
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and record.get('status') != 'rejected':
                        mongo_db.records.update_one(
                            {"_id": record_id},
                            {"$set": {
                                "status": "rejected",
                                "rejected_by": admin_username,
                                "rejected_at": datetime.now(timezone.utc),
                                "rejection_reason": "Bulk rejection"
                            }}
                        )
                        success_count += 1
                        
            except Exception as e:
                print(f"Error processing record {record_id}: {e}")
                error_count += 1
        
        # Log bulk action
        log_admin_action(
            admin_username,
            f"Bulk {action.title()}",
            f"Bulk {action}ed {success_count} records ({error_count} errors)"
        )
        
        if success_count > 0:
            flash(f'✅ Successfully {action}ed {success_count} records', 'success')
        if error_count > 0:
            flash(f'⚠️ {error_count} records had errors', 'warning')
            
    except Exception as e:
        flash(f'Error in bulk operation: {str(e)}', 'danger')
        print(f"Bulk records error: {e}")
    
    return redirect(url_for('admin'))

@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = 'is_admin' in request.form
        
        if mongo_db.users.find_one({"username": username}):
            flash('Username already exists', 'danger')
        elif mongo_db.users.find_one({"email": email}):
            flash('Email already exists', 'danger')
        else:
            # Get next user ID
            last_user = mongo_db.users.find_one(sort=[("_id", -1)])
            next_id = (last_user['_id'] + 1) if last_user else 1
            
            new_user = {
                "_id": next_id,
                "username": username,
                "email": email,
                "password_hash": generate_password_hash(password),
                "is_admin": is_admin,
                "points": 0,
                "date_joined": datetime.now(timezone.utc)
            }
            
            mongo_db.users.insert_one(new_user)
            flash('User created successfully!', 'success')
    
    users = list(mongo_db.users.find({}, max_time_ms=60000).sort("date_joined", -1))
    return render_template('admin/users.html', users=users)

@app.route('/admin/settings')
def admin_settings():
    """Admin settings panel with system controls"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    import sys
    
    # Get system info (with fallback if psutil not available)
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)  # Faster check
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            'python_version': sys.version,
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used': f"{memory.used / (1024**3):.1f} GB",
            'memory_total': f"{memory.total / (1024**3):.1f} GB",
            'disk_percent': disk.percent,
            'disk_used': f"{disk.used / (1024**3):.1f} GB",
            'disk_total': f"{disk.total / (1024**3):.1f} GB"
        }
    except ImportError:
        system_info = {
            'python_version': sys.version,
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': "N/A",
            'memory_total': "N/A", 
            'disk_percent': 0,
            'disk_used': "N/A",
            'disk_total': "N/A",
            'note': 'Install psutil for system monitoring: pip install psutil'
        }
    except Exception as e:
        system_info = {'error': str(e)}
    
    # Cache info
    try:
        cache_info = {
            'main_levels': len(levels_cache.get('main_list', [])),
            'legacy_levels': len(levels_cache.get('legacy_list', [])),
            'last_updated': levels_cache.get('last_updated', 'Never')
        }
    except Exception as e:
        cache_info = {'error': 'Could not load cache info'}
    
    # Database stats
    try:
        db_stats = {
            'total_levels': mongo_db.levels.count_documents({}),
            'main_levels': mongo_db.levels.count_documents({"is_legacy": False}),
            'legacy_levels': mongo_db.levels.count_documents({"is_legacy": True}),
            'total_users': mongo_db.users.count_documents({}),
            'total_records': mongo_db.records.count_documents({}),
            'pending_records': mongo_db.records.count_documents({"status": "pending"})
        }
    except Exception as e:
        db_stats = {'error': 'Could not load database stats'}
    
    # Site settings
    try:
        site_settings = mongo_db.site_settings.find_one({"_id": "main"})
        if not site_settings:
            site_settings = {"future_list_enabled": False}
    except Exception as e:
        site_settings = {"future_list_enabled": False}
    
    return render_template('admin/settings.html', 
                         system_info=system_info,
                         cache_info=cache_info,
                         db_stats=db_stats,
                         site_settings=site_settings)

@app.route('/admin/settings/clear_cache', methods=['POST'])
def admin_clear_cache():
    """Clear all cached data"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    levels_cache['last_updated'] = None
    
    # Log admin action
    admin_user = mongo_db.users.find_one({"_id": session['user_id']})
    admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
    log_admin_action(admin_username, "Cache Cleared", "Cleared all cached level data")
    
    flash('Cache cleared successfully!', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/reload_cache', methods=['POST'])
def admin_reload_cache():
    """Reload all cached data"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Clear first
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Reload main levels
        main_levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1))
        levels_cache['main_list'] = main_levels
        
        # Reload legacy levels
        legacy_levels = list(mongo_db.levels.find(
            {"is_legacy": True},
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1}
        ).sort("position", 1))
        levels_cache['legacy_list'] = legacy_levels
        
        levels_cache['last_updated'] = datetime.now(timezone.utc)
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "Cache Reloaded", f"Reloaded cache: {len(main_levels)} main, {len(legacy_levels)} legacy levels")
        
        flash(f'Cache reloaded! Main: {len(main_levels)}, Legacy: {len(legacy_levels)}', 'success')
        
    except Exception as e:
        flash(f'Cache reload failed: {e}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/restart', methods=['POST'])
def admin_restart():
    """Restart the application (if possible)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    import os
    import signal
    
    flash('Attempting to restart application...', 'info')
    
    # This will work if running with a process manager like PM2, systemd, etc.
    def restart_app():
        import time
        time.sleep(1)  # Give time for response to send
        os.kill(os.getpid(), signal.SIGTERM)
    
    import threading
    threading.Thread(target=restart_app).start()
    
    return """
    <div style="text-align: center; padding: 50px; font-family: Arial;">
        <h1>🔄 Restarting Application...</h1>
        <p>The application is restarting. Please wait a moment and refresh the page.</p>
        <script>
            setTimeout(function() {
                window.location.href = '/';
            }, 5000);
        </script>
    </div>
    """

@app.route('/admin/settings/optimize_db', methods=['POST'])
def admin_optimize_db():
    """Optimize database performance"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Create indexes for better performance (with error handling for existing indexes)
        indexes_to_create = [
            (mongo_db.levels, [("is_legacy", 1), ("position", 1)]),
            (mongo_db.levels, [("position", 1)]),
            (mongo_db.levels, [("is_legacy", 1)]),
            (mongo_db.records, [("level_id", 1), ("status", 1)]),
            (mongo_db.records, [("user_id", 1)]),
            (mongo_db.users, [("username", 1)]),
            (mongo_db.users, [("email", 1)])
        ]
        
        for collection, index_spec in indexes_to_create:
            try:
                collection.create_index(index_spec)
            except Exception as idx_error:
                if "IndexKeySpecsConflict" in str(idx_error) or "already exists" in str(idx_error):
                    print(f"Index already exists: {index_spec}")
                else:
                    print(f"Error creating index {index_spec}: {idx_error}")
        
        # Remove Base64 images if any
        result = mongo_db.levels.update_many(
            {"thumbnail_url": {"$regex": "^data:"}},
            {"$set": {"thumbnail_url": ""}}
        )
        
        flash(f'Database optimized! Created indexes and removed {result.modified_count} Base64 images.', 'success')
        
    except Exception as e:
        flash(f'Database optimization failed: {e}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/future_list', methods=['POST'])
def admin_toggle_future_list():
    """Toggle future list feature"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    action = request.form.get('action')
    
    try:
        # Get or create settings document
        settings = mongo_db.site_settings.find_one({"_id": "main"})
        if not settings:
            settings = {"_id": "main", "future_list_enabled": False}
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        if action == 'enable':
            mongo_db.site_settings.update_one(
                {"_id": "main"},
                {"$set": {"future_list_enabled": True}},
                upsert=True
            )
            log_admin_action(admin_username, "Future List Enabled", "Enabled the Future List feature")
            flash('Future List enabled! 🚀', 'success')
        elif action == 'disable':
            mongo_db.site_settings.update_one(
                {"_id": "main"},
                {"$set": {"future_list_enabled": False}},
                upsert=True
            )
            log_admin_action(admin_username, "Future List Disabled", "Disabled the Future List feature")
            flash('Future List disabled', 'info')
            
    except Exception as e:
        flash(f'Error toggling future list: {e}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/delete_website', methods=['POST'])
def admin_delete_website():
    """Definitely delete the website (not a rickroll)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # This is totally a real delete function 😉
    return redirect('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

@app.route('/admin/future_levels', methods=['GET', 'POST'])
def admin_future_levels():
    """Admin interface for managing future levels"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get next level ID
        last_level = mongo_db.future_levels.find_one(sort=[("_id", -1)])
        next_id = (last_level['_id'] + 1) if last_level else 1
        
        name = request.form.get('name')
        creator = request.form.get('creator')
        verifier = request.form.get('verifier')
        level_id = request.form.get('level_id')
        video_url = request.form.get('video_url')
        description = request.form.get('description')
        difficulty = float(request.form.get('difficulty'))
        position = int(request.form.get('position'))
        
        # Shift existing levels at this position and below
        mongo_db.future_levels.update_many(
            {"position": {"$gte": position}},
            {"$inc": {"position": 1}}
        )
        
        new_level = {
            "_id": next_id,
            "name": name,
            "creator": creator,
            "verifier": verifier,
            "level_id": level_id or None,
            "video_url": video_url,
            "description": description,
            "difficulty": difficulty,
            "position": position,
            "date_added": datetime.now(timezone.utc)
        }
        
        mongo_db.future_levels.insert_one(new_level)
        
        # Log level placement to changelog
        above_level = None
        below_level = None
        
        # Find levels above and below
        if position > 1:
            above_level_doc = mongo_db.future_levels.find_one({"position": position - 1})
            if above_level_doc:
                above_level = above_level_doc['name']
        
        below_level_doc = mongo_db.future_levels.find_one({"position": position + 1})
        if below_level_doc:
            below_level = below_level_doc['name']
        
        log_level_change(
            action="placed",
            level_name=name,
            admin_username=session.get('username', 'Unknown'),
            position=position,
            above_level=above_level,
            below_level=below_level,
            list_type="future"
        )
        
        flash('Future level added successfully!', 'success')
        return redirect(url_for('admin_future_levels'))
    
    # Get all future levels
    future_levels = list(mongo_db.future_levels.find({}).sort("position", 1))
    
    return render_template('admin/future_levels.html', levels=future_levels)

@app.route('/admin/delete_future_level', methods=['POST'])
def admin_delete_future_level():
    """Delete a future level"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    # Get level info before deletion
    level = mongo_db.future_levels.find_one({"_id": level_id})
    if not level:
        flash('Future level not found', 'danger')
        return redirect(url_for('admin_future_levels'))
    
    level_position = level['position']
    
    # Delete the level
    mongo_db.future_levels.delete_one({"_id": level_id})
    
    # Log level removal to changelog
    log_level_change(
        action="removed",
        level_name=level['name'],
        admin_username=session.get('username', 'Unknown'),
        old_position=level_position,
        list_type="future"
    )
    
    # Shift positions of levels that were below the deleted level
    mongo_db.future_levels.update_many(
        {"position": {"$gt": level_position}},
        {"$inc": {"position": -1}}
    )
    
    flash('Future level deleted successfully!', 'success')
    return redirect(url_for('admin_future_levels'))

@app.route('/future')
def future_list():
    """Future Recent Tab List"""
    # Check if future list is enabled
    settings = mongo_db.site_settings.find_one({"_id": "main"})
    if not settings or not settings.get('future_list_enabled', False):
        return render_template('future_disabled.html')
    
    # Get future levels
    future_levels = list(mongo_db.future_levels.find({}).sort("position", 1))
    
    return render_template('future.html', levels=future_levels)

@app.route('/admin/announcements', methods=['GET', 'POST'])
def admin_announcements():
    """Admin interface for managing site announcements"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        announcement_type = request.form.get('type', 'info')  # info, success, warning, danger
        expires_in_hours = int(request.form.get('expires_in_hours', 24))
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        announcement = {
            "title": title,
            "message": message,
            "type": announcement_type,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "created_by": session.get('username', 'Unknown'),
            "active": True
        }
        
        mongo_db.announcements.insert_one(announcement)
        
        flash(f'Announcement created! Will expire in {expires_in_hours} hours.', 'success')
        return redirect(url_for('admin_announcements'))
    
    # Get all announcements (active and expired)
    announcements = list(mongo_db.announcements.find({}).sort("created_at", -1))
    
    return render_template('admin/announcements.html', announcements=announcements)

@app.route('/admin/delete_announcement', methods=['POST'])
def admin_delete_announcement():
    """Delete an announcement"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    announcement_id = request.form.get('announcement_id')
    
    mongo_db.announcements.delete_one({"_id": ObjectId(announcement_id)})
    
    flash('Announcement deleted successfully!', 'success')
    return redirect(url_for('admin_announcements'))

@app.route('/search')
def search_levels():
    """Search levels across the entire database"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return redirect(url_for('index'))
    
    try:
        # Search in level names, creators, and verifiers
        search_filter = {
            "is_legacy": False,
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"creator": {"$regex": query, "$options": "i"}},
                {"verifier": {"$regex": query, "$options": "i"}}
            ]
        }
        
        levels = list(mongo_db.levels.find(
            search_filter,
            {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1}
        ).sort("position", 1))
        
        return render_template('search_results.html', levels=levels, query=query, total_results=len(levels))
        
    except Exception as e:
        flash(f'Search error: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/guidelines')
def guidelines():
    """Community guidelines page"""
    return render_template('guidelines.html')

@app.route('/changelog')
def changelog():
    """Level changelog page - tracks level placements and movements"""
    try:
        # Get level changelog entries from database, sorted by date (newest first)
        changelog_entries = list(mongo_db.level_changelog.find().sort("timestamp", -1).limit(50))
        
        # If no entries exist, create some sample entries
        if not changelog_entries:
            sample_entries = [
                {
                    "timestamp": datetime.now(timezone.utc),
                    "action": "placed",
                    "level_name": "555",
                    "position": 1,
                    "above_level": None,
                    "below_level": "deimonx",
                    "list_type": "main",
                    "admin": "Miifin"
                },
                {
                    "timestamp": datetime.now(timezone.utc) - timedelta(hours=2),
                    "action": "moved",
                    "level_name": "deimonx", 
                    "old_position": 1,
                    "new_position": 2,
                    "above_level": "555",
                    "below_level": "fommy txt do verify",
                    "list_type": "main",
                    "admin": "Miifin"
                },
                {
                    "timestamp": datetime.now(timezone.utc) - timedelta(days=1),
                    "action": "legacy",
                    "level_name": "old level example",
                    "old_position": 75,
                    "list_type": "legacy",
                    "admin": "Kye"
                }
            ]
            mongo_db.level_changelog.insert_many(sample_entries)
            changelog_entries = sample_entries
            
    except Exception as e:
        print(f"Error loading changelog: {e}")
        changelog_entries = []
    
    return render_template('level_changelog.html', changelog=changelog_entries)

@app.route('/stats')
def stats_viewer():
    """Comprehensive statistics page like demon list stats"""
    try:
        # Level Statistics
        total_levels = mongo_db.levels.count_documents({})
        main_levels = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_levels = mongo_db.levels.count_documents({"is_legacy": True})
        
        # User Statistics
        total_users = mongo_db.users.count_documents({})
        active_users = mongo_db.users.count_documents({"points": {"$gt": 0}})
        admin_users = mongo_db.users.count_documents({"is_admin": True})
        
        # Record Statistics
        total_records = mongo_db.records.count_documents({})
        approved_records = mongo_db.records.count_documents({"status": "approved"})
        pending_records = mongo_db.records.count_documents({"status": "pending"})
        rejected_records = mongo_db.records.count_documents({"status": "rejected"})
        
        # Completion Statistics
        completed_records = mongo_db.records.count_documents({"status": "approved", "progress": 100})
        partial_records = mongo_db.records.count_documents({"status": "approved", "progress": {"$lt": 100}})
        
        # Top Players (by points)
        top_players = list(mongo_db.users.find(
            {"points": {"$gt": 0}},
            {"username": 1, "points": 1, "nickname": 1}
        ).sort("points", -1).limit(10))
        
        # Most Active Levels (by record count)
        most_active_levels = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$group": {"_id": "$level_id", "record_count": {"$sum": 1}}},
            {"$lookup": {
                "from": "levels",
                "localField": "_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$sort": {"record_count": -1}},
            {"$limit": 10}
        ]))
        
        # Recent Activity (last 10 approved records)
        recent_activity = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$user"},
            {"$unwind": "$level"},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 10}
        ]))
        
        # Difficulty Distribution
        difficulty_distribution = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": {"$round": "$difficulty"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]))
        
        # Monthly Registration Stats (last 6 months)
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_registrations = list(mongo_db.users.aggregate([
            {"$match": {"date_joined": {"$gte": six_months_ago}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$date_joined"},
                    "month": {"$month": "$date_joined"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]))
        
        # Calculate percentages
        approval_rate = (approved_records / total_records * 100) if total_records > 0 else 0
        completion_rate = (completed_records / approved_records * 100) if approved_records > 0 else 0
        active_user_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        stats_data = {
            'levels': {
                'total': total_levels,
                'main': main_levels,
                'legacy': legacy_levels
            },
            'users': {
                'total': total_users,
                'active': active_users,
                'admins': admin_users,
                'active_rate': round(active_user_rate, 1)
            },
            'records': {
                'total': total_records,
                'approved': approved_records,
                'pending': pending_records,
                'rejected': rejected_records,
                'completed': completed_records,
                'partial': partial_records,
                'approval_rate': round(approval_rate, 1),
                'completion_rate': round(completion_rate, 1)
            },
            'top_players': top_players,
            'most_active_levels': most_active_levels,
            'recent_activity': recent_activity,
            'difficulty_distribution': difficulty_distribution,
            'monthly_registrations': monthly_registrations
        }
        
        return render_template('stats.html', stats=stats_data)
        
    except Exception as e:
        flash(f'Error loading statistics: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/stats/overview')
def stats_overview():
    """Overview statistics page"""
    try:
        # Basic counts
        total_levels = mongo_db.levels.count_documents({})
        main_levels = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_levels = mongo_db.levels.count_documents({"is_legacy": True})
        total_users = mongo_db.users.count_documents({})
        active_users = mongo_db.users.count_documents({"points": {"$gt": 0}})
        total_records = mongo_db.records.count_documents({})
        approved_records = mongo_db.records.count_documents({"status": "approved"})
        
        # Calculate rates
        approval_rate = (approved_records / total_records * 100) if total_records > 0 else 0
        active_user_rate = (active_users / total_users * 100) if total_users > 0 else 0
        
        # Monthly growth (last 6 months)
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_stats = list(mongo_db.users.aggregate([
            {"$match": {"date_joined": {"$gte": six_months_ago}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$date_joined"},
                    "month": {"$month": "$date_joined"}
                },
                "users": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]))
        
        stats_data = {
            'levels': {'total': total_levels, 'main': main_levels, 'legacy': legacy_levels},
            'users': {'total': total_users, 'active': active_users, 'active_rate': round(active_user_rate, 1)},
            'records': {'total': total_records, 'approved': approved_records, 'approval_rate': round(approval_rate, 1)},
            'monthly_growth': monthly_stats
        }
        
        return render_template('stats/overview.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading overview: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/stats/players')
def stats_players():
    """Player statistics page"""
    try:
        # Top players by points
        top_players = list(mongo_db.users.find(
            {"points": {"$gt": 0}},
            {"username": 1, "points": 1, "nickname": 1, "date_joined": 1}
        ).sort("points", -1).limit(50))
        
        # Most active players (by record count)
        most_active = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$group": {"_id": "$user_id", "record_count": {"$sum": 1}}},
            {"$lookup": {
                "from": "users",
                "localField": "_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {"record_count": -1}},
            {"$limit": 20}
        ]))
        
        # Player distribution by points
        point_ranges = [
            {"range": "0", "min": 0, "max": 0},
            {"range": "1-100", "min": 1, "max": 100},
            {"range": "101-500", "min": 101, "max": 500},
            {"range": "501-1000", "min": 501, "max": 1000},
            {"range": "1000+", "min": 1001, "max": 999999}
        ]
        
        for range_data in point_ranges:
            if range_data["max"] == 0:
                count = mongo_db.users.count_documents({"points": 0})
            elif range_data["max"] == 999999:
                count = mongo_db.users.count_documents({"points": {"$gte": range_data["min"]}})
            else:
                count = mongo_db.users.count_documents({
                    "points": {"$gte": range_data["min"], "$lte": range_data["max"]}
                })
            range_data["count"] = count
        
        stats_data = {
            'top_players': top_players,
            'most_active': most_active,
            'point_distribution': point_ranges
        }
        
        return render_template('stats/players.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading player stats: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/stats/levels')
def stats_levels():
    """Level statistics page"""
    try:
        # Most popular levels (by record count)
        popular_levels = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$group": {"_id": "$level_id", "record_count": {"$sum": 1}}},
            {"$lookup": {
                "from": "levels",
                "localField": "_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$sort": {"record_count": -1}},
            {"$limit": 20}
        ]))
        
        # Difficulty distribution
        difficulty_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": {"$round": "$difficulty"},
                "count": {"$sum": 1},
                "avg_points": {"$avg": "$points"}
            }},
            {"$sort": {"_id": 1}}
        ]))
        
        # Creator statistics
        creator_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": "$creator",
                "level_count": {"$sum": 1},
                "total_points": {"$sum": "$points"}
            }},
            {"$sort": {"level_count": -1}},
            {"$limit": 15}
        ]))
        
        # Verifier statistics
        verifier_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": "$verifier",
                "level_count": {"$sum": 1}
            }},
            {"$sort": {"level_count": -1}},
            {"$limit": 15}
        ]))
        
        stats_data = {
            'popular_levels': popular_levels,
            'difficulty_distribution': difficulty_stats,
            'top_creators': creator_stats,
            'top_verifiers': verifier_stats
        }
        
        return render_template('stats/levels.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading level stats: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/stats/records')
def stats_records():
    """Record statistics page"""
    try:
        # Record status breakdown
        total_records = mongo_db.records.count_documents({})
        approved_records = mongo_db.records.count_documents({"status": "approved"})
        pending_records = mongo_db.records.count_documents({"status": "pending"})
        rejected_records = mongo_db.records.count_documents({"status": "rejected"})
        
        # Completion statistics
        completed_records = mongo_db.records.count_documents({"status": "approved", "progress": 100})
        partial_records = mongo_db.records.count_documents({"status": "approved", "progress": {"$lt": 100}})
        
        # Progress distribution
        progress_ranges = [
            {"range": "1-25%", "min": 1, "max": 25},
            {"range": "26-50%", "min": 26, "max": 50},
            {"range": "51-75%", "min": 51, "max": 75},
            {"range": "76-99%", "min": 76, "max": 99},
            {"range": "100%", "min": 100, "max": 100}
        ]
        
        for range_data in progress_ranges:
            count = mongo_db.records.count_documents({
                "status": "approved",
                "progress": {"$gte": range_data["min"], "$lte": range_data["max"]}
            })
            range_data["count"] = count
        
        # Daily submission trends (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_submissions = list(mongo_db.records.aggregate([
            {"$match": {"date_submitted": {"$gte": thirty_days_ago}}},
            {"$group": {
                "_id": {
                    "year": {"$year": "$date_submitted"},
                    "month": {"$month": "$date_submitted"},
                    "day": {"$dayOfMonth": "$date_submitted"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
        ]))
        
        stats_data = {
            'total': total_records,
            'approved': approved_records,
            'pending': pending_records,
            'rejected': rejected_records,
            'completed': completed_records,
            'partial': partial_records,
            'progress_distribution': progress_ranges,
            'daily_submissions': daily_submissions,
            'approval_rate': round((approved_records / total_records * 100) if total_records > 0 else 0, 1),
            'completion_rate': round((completed_records / approved_records * 100) if approved_records > 0 else 0, 1)
        }
        
        return render_template('stats/records.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading record stats: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/stats/activity')
def stats_activity():
    """Activity statistics page"""
    try:
        # Recent approved records
        recent_approved = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$user"},
            {"$unwind": "$level"},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 50}
        ]))
        
        # Recent registrations
        recent_users = list(mongo_db.users.find(
            {},
            {"username": 1, "nickname": 1, "date_joined": 1, "points": 1}
        ).sort("date_joined", -1).limit(20))
        
        # Pending records for admins
        pending_records = []
        if session.get('is_admin'):
            pending_records = list(mongo_db.records.aggregate([
                {"$match": {"status": "pending"}},
                {"$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }},
                {"$lookup": {
                    "from": "levels",
                    "localField": "level_id",
                    "foreignField": "_id",
                    "as": "level"
                }},
                {"$unwind": "$user"},
                {"$unwind": "$level"},
                {"$sort": {"date_submitted": -1}},
                {"$limit": 20}
            ]))
        
        stats_data = {
            'recent_approved': recent_approved,
            'recent_users': recent_users,
            'pending_records': pending_records
        }
        
        return render_template('stats/activity.html', stats=stats_data)
    except Exception as e:
        flash(f'Error loading activity stats: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
def admin_toggle_admin(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    user = mongo_db.users.find_one({"_id": user_id})
    if user:
        # Prevent admins from removing admin status from other admins
        if user.get('is_admin', False):
            flash('Cannot remove admin privileges from another admin', 'danger')
            return redirect(url_for('admin_users'))
        
        # Only grant admin status (cannot revoke)
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"is_admin": True}}
        )
        
        flash(f'Admin privileges granted to {user["username"]}', 'success')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
def admin_ban_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    user = mongo_db.users.find_one({"_id": user_id})
    if user:
        # Prevent banning other admins
        if user.get('is_admin', False):
            flash('Cannot ban another admin', 'danger')
            return redirect(url_for('admin_users'))
        
        # Delete user's records
        mongo_db.records.delete_many({"user_id": user_id})
        
        # Delete the user
        mongo_db.users.delete_one({"_id": user_id})
        
        flash(f'User {user["username"]} has been banned and deleted', 'success')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/update_points', methods=['POST'])
def admin_update_points():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Update all level points based on current positions
    levels = list(mongo_db.levels.find())
    updated_count = 0
    
    for level in levels:
        new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        if level.get('points') != new_points:
            mongo_db.levels.update_one(
                {"_id": level['_id']},
                {"$set": {"points": new_points}}
            )
            updated_count += 1
    
    # Recalculate all user points
    users = list(mongo_db.users.find())
    for user in users:
        update_user_points(user['_id'])
    
    flash(f'Updated {updated_count} levels and recalculated all user points!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/settings')
def user_settings():
    """User settings page"""
    if 'user_id' not in session:
        flash('Please log in to access settings', 'warning')
        return redirect(url_for('login'))
    
    user = mongo_db.users.find_one({"_id": session['user_id']})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('logout'))
    
    return render_template('settings.html', user=user)

@app.route('/settings/update', methods=['POST'])
def update_user_settings():
    """Update user settings"""
    if 'user_id' not in session:
        flash('Please log in to access settings', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    action = request.form.get('action')
    
    try:
        if action == 'profile':
            # Update profile information
            username = request.form.get('username', '').strip()
            nickname = request.form.get('nickname', '').strip()
            email = request.form.get('email', '').strip()
            bio = request.form.get('bio', '').strip()
            country = request.form.get('country', '').strip()
            
            # Validation
            if not username or len(username) < 3:
                flash('Username must be at least 3 characters', 'danger')
                return redirect(url_for('user_settings'))
            
            if not email or '@' not in email:
                flash('Please enter a valid email', 'danger')
                return redirect(url_for('user_settings'))
            
            # Check if username/email already taken by another user
            existing_user = mongo_db.users.find_one({
                "$and": [
                    {"_id": {"$ne": user_id}},
                    {"$or": [{"username": username}, {"email": email}]}
                ]
            })
            
            if existing_user:
                if existing_user['username'] == username:
                    flash('Username already taken', 'danger')
                else:
                    flash('Email already taken', 'danger')
                return redirect(url_for('user_settings'))
            
            # Update user
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "username": username,
                    "nickname": nickname,
                    "email": email,
                    "bio": bio,
                    "country": country
                }}
            )
            
            flash('Profile updated successfully!', 'success')
            
        elif action == 'preferences':
            # Update user preferences
            theme = request.form.get('theme', 'light')
            timezone = request.form.get('timezone', 'UTC')
            email_notifications = 'email_notifications' in request.form
            public_profile = 'public_profile' in request.form
            country = request.form.get('country', '').strip()
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "theme": theme,
                    "timezone": timezone,
                    "email_notifications": email_notifications,
                    "public_profile": public_profile,
                    "country": country
                }}
            )
            
            flash('Preferences updated successfully!', 'success')
            
        elif action == 'social_media':
            # Update social media connections
            youtube_url = request.form.get('youtube_url', '').strip()
            twitch_url = request.form.get('twitch_url', '').strip()
            tiktok_url = request.form.get('tiktok_url', '').strip()
            vimeo_url = request.form.get('vimeo_url', '').strip()
            discord_tag = request.form.get('discord_tag', '').strip()
            twitter_url = request.form.get('twitter_url', '').strip()
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "youtube_url": youtube_url,
                    "twitch_url": twitch_url,
                    "tiktok_url": tiktok_url,
                    "vimeo_url": vimeo_url,
                    "discord_tag": discord_tag,
                    "twitter_url": twitter_url
                }}
            )
            
            flash('Social media connections updated successfully!', 'success')
            
        elif action == 'password':
            # Update password
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_password or not new_password:
                flash('Please fill in all password fields', 'danger')
                return redirect(url_for('user_settings'))
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return redirect(url_for('user_settings'))
            
            if len(new_password) < 6:
                flash('Password must be at least 6 characters', 'danger')
                return redirect(url_for('user_settings'))
            
            # Verify current password
            user = mongo_db.users.find_one({"_id": user_id})
            if not check_password_hash(user['password_hash'], current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('user_settings'))
            
            # Update password
            new_hash = generate_password_hash(new_password)
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"password_hash": new_hash}}
            )
            
            flash('Password updated successfully!', 'success')
            
        elif action == 'avatar':
            # Update profile picture
            avatar_file = request.files.get('avatar')
            avatar_url = request.form.get('avatar_url', '').strip()
            
            # Check if user provided a file
            if avatar_file and avatar_file.filename:
                # Handle file upload
                import os
                
                # Validate file type
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                file_extension = avatar_file.filename.rsplit('.', 1)[1].lower() if '.' in avatar_file.filename else ''
                
                if file_extension not in allowed_extensions:
                    flash('Invalid file type. Please use PNG, JPG, JPEG, GIF, or WebP.', 'danger')
                    return redirect(url_for('user_settings'))
                
                # Create uploads directory
                os.makedirs('static/avatars', exist_ok=True)
                
                # Save file with proper extension
                filename = f"avatar_{user_id}_{int(datetime.now().timestamp())}.{file_extension}"
                filepath = os.path.join('static/avatars', filename)
                
                try:
                    # Try to resize and optimize image
                    from PIL import Image
                    
                    img = Image.open(avatar_file.stream)
                    img = img.convert('RGB')
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    img.save(filepath, 'JPEG', quality=85, optimize=True)
                    
                    avatar_url = f"/static/avatars/{filename}"
                    
                except ImportError:
                    # Fallback without PIL - just save the file
                    avatar_file.seek(0)  # Reset file pointer
                    avatar_file.save(filepath)
                    avatar_url = f"/static/avatars/{filename}"
                    
                except Exception as e:
                    flash(f'Error processing image: {e}', 'danger')
                    return redirect(url_for('user_settings'))
            
            # Check if user provided a URL instead
            elif avatar_url:
                # Validate URL format
                if not (avatar_url.startswith('http://') or avatar_url.startswith('https://')):
                    flash('Please provide a valid URL starting with http:// or https://', 'warning')
                    return redirect(url_for('user_settings'))
            
            else:
                flash('Please either upload a file or provide a URL', 'warning')
                return redirect(url_for('user_settings'))
            
            # Update avatar URL in database
            if avatar_url:
                mongo_db.users.update_one(
                    {"_id": user_id},
                    {"$set": {"avatar_url": avatar_url}}
                )
                flash('Profile picture updated successfully!', 'success')
            else:
                flash('No avatar provided', 'warning')
            
        elif action == 'reset_api_key':
            # Reset API key (with confirmation)
            confirm_text = request.form.get('confirm_reset', '').strip()
            if confirm_text.upper() != 'RESET API KEY':
                flash('Please type "RESET API KEY" to confirm', 'danger')
                return redirect(url_for('user_settings'))
            
            # Generate new API key
            import secrets
            new_api_key = secrets.token_urlsafe(32)
            
            # Update user with new API key
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"api_key": new_api_key}}
            )
            
            flash(f'API key reset successfully! New key: {new_api_key}', 'success')
            
        elif action == 'delete_account':
            # Delete account (with confirmation)
            confirm_text = request.form.get('confirm_delete', '').strip()
            if confirm_text.lower() != 'delete my account':
                flash('Please type "DELETE MY ACCOUNT" to confirm', 'danger')
                return redirect(url_for('user_settings'))
            
            # Delete user records first
            mongo_db.records.delete_many({"user_id": user_id})
            
            # Delete user
            mongo_db.users.delete_one({"_id": user_id})
            
            # Logout
            session.clear()
            flash('Account deleted successfully', 'info')
            return redirect(url_for('index'))
            
    except Exception as e:
        flash(f'Error updating settings: {e}', 'danger')
    
    return redirect(url_for('user_settings'))

@app.route('/export_data')
def export_user_data():
    """Export user's data as JSON"""
    if 'user_id' not in session:
        flash('Please log in to export data', 'warning')
        return redirect(url_for('login'))
    
    try:
        user_id = session['user_id']
        
        # Get user data
        user = mongo_db.users.find_one({"_id": user_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('user_settings'))
        
        # Get user's records
        records = list(mongo_db.records.find({"user_id": user_id}))
        
        # Clean up data (remove sensitive info)
        user_data = {
            'username': user.get('username'),
            'nickname': user.get('nickname'),
            'email': user.get('email'),
            'bio': user.get('bio'),
            'points': user.get('points', 0),
            'date_joined': user.get('date_joined').isoformat() if user.get('date_joined') else None,
            'is_admin': user.get('is_admin', False),
            'avatar_url': user.get('avatar_url'),
            'records': []
        }
        
        # Add records data
        for record in records:
            record_data = {
                'level_id': record.get('level_id'),
                'progress': record.get('progress'),
                'video_url': record.get('video_url'),
                'status': record.get('status'),
                'date_submitted': record.get('date_submitted').isoformat() if record.get('date_submitted') else None
            }
            user_data['records'].append(record_data)
        
        # Return as JSON download
        from flask import Response
        import json
        
        json_data = json.dumps(user_data, indent=2)
        
        response = Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={user["username"]}_data.json'}
        )
        
        return response
        
    except Exception as e:
        flash(f'Error exporting data: {e}', 'danger')
        return redirect(url_for('user_settings'))

@app.route('/api/check_username')
def check_username():
    """API endpoint to check if username is available"""
    username = request.args.get('username', '').strip()
    current_user_id = session.get('user_id')
    
    if not username or len(username) < 3:
        return {'available': False, 'message': 'Username must be at least 3 characters'}
    
    # Check if username exists (excluding current user)
    query = {"username": username}
    if current_user_id:
        query["_id"] = {"$ne": current_user_id}
    
    existing = mongo_db.users.find_one(query)
    
    if existing:
        return {'available': False, 'message': 'Username already taken'}
    else:
        return {'available': True, 'message': 'Username available'}

@app.route('/api/qr/<username>')
def generate_qr_code(username):
    """Generate QR code for user profile"""
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        # Create profile URL
        profile_url = f"{request.url_root}user/{username}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(profile_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {'success': True, 'qr_code': f'data:image/png;base64,{img_str}'}
        
    except ImportError:
        return {'success': False, 'error': 'QR code generation not available'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/user/<username>')
def public_profile(username):
    """Public user profile page"""
    user = mongo_db.users.find_one({"username": username})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    # Check if profile is public
    if not user.get('public_profile', True) and user['_id'] != session.get('user_id'):
        flash('This profile is private', 'warning')
        return redirect(url_for('index'))
    
    # Get user's approved records with level info
    user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": user['_id'], "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$sort": {"date_submitted": -1}},
        {"$limit": 50}
    ]))
    
    return render_template('public_profile.html', user=user, records=user_records)

@app.route('/world')
def world_leaderboard():
    """World map leaderboard with country-based rankings"""
    try:
        # Get top players by country (only those with points > 0)
        country_stats = list(mongo_db.users.aggregate([
            {"$match": {"points": {"$gt": 0}, "country": {"$exists": True, "$ne": ""}}},
            {"$group": {
                "_id": "$country",
                "player_count": {"$sum": 1},
                "total_points": {"$sum": "$points"},
                "avg_points": {"$avg": "$points"},
                "top_player": {"$first": "$$ROOT"}
            }},
            {"$sort": {"total_points": -1}}
        ]))
        
        # Get overall top players with countries
        top_players = list(mongo_db.users.find(
            {"points": {"$gt": 0}},
            {"username": 1, "nickname": 1, "points": 1, "country": 1}
        ).sort("points", -1).limit(100))
        
        # Country name mapping
        country_names = {
            'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AD': 'Andorra', 'AO': 'Angola',
            'AR': 'Argentina', 'AM': 'Armenia', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan',
            'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus',
            'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BT': 'Bhutan', 'BO': 'Bolivia',
            'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BR': 'Brazil', 'BN': 'Brunei', 'BG': 'Bulgaria',
            'BF': 'Burkina Faso', 'BI': 'Burundi', 'CV': 'Cape Verde', 'KH': 'Cambodia', 'CM': 'Cameroon',
            'CA': 'Canada', 'CF': 'Central African Republic', 'TD': 'Chad', 'CL': 'Chile', 'CN': 'China',
            'CO': 'Colombia', 'KM': 'Comoros', 'CG': 'Congo', 'CR': 'Costa Rica', 'HR': 'Croatia',
            'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti',
            'DM': 'Dominica', 'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador',
            'GQ': 'Equatorial Guinea', 'ER': 'Eritrea', 'EE': 'Estonia', 'SZ': 'Eswatini', 'ET': 'Ethiopia',
            'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France', 'GA': 'Gabon', 'GM': 'Gambia',
            'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GR': 'Greece', 'GD': 'Grenada',
            'GT': 'Guatemala', 'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti',
            'HN': 'Honduras', 'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia',
            'IR': 'Iran', 'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 'IT': 'Italy',
            'CI': 'Ivory Coast', 'JM': 'Jamaica', 'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan',
            'KE': 'Kenya', 'KI': 'Kiribati', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Laos',
            'LV': 'Latvia', 'LB': 'Lebanon', 'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya',
            'LI': 'Liechtenstein', 'LT': 'Lithuania', 'LU': 'Luxembourg', 'MG': 'Madagascar', 'MW': 'Malawi',
            'MY': 'Malaysia', 'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 'MH': 'Marshall Islands',
            'MR': 'Mauritania', 'MU': 'Mauritius', 'MX': 'Mexico', 'FM': 'Micronesia', 'MD': 'Moldova',
            'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MA': 'Morocco', 'MZ': 'Mozambique',
            'MM': 'Myanmar', 'NA': 'Namibia', 'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands',
            'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 'MK': 'North Macedonia',
            'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PW': 'Palau', 'PA': 'Panama',
            'PG': 'Papua New Guinea', 'PY': 'Paraguay', 'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland',
            'PT': 'Portugal', 'QA': 'Qatar', 'RO': 'Romania', 'RU': 'Russia', 'RW': 'Rwanda',
            'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'VC': 'Saint Vincent and the Grenadines',
            'WS': 'Samoa', 'SM': 'San Marino', 'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia',
            'SN': 'Senegal', 'RS': 'Serbia', 'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore',
            'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 'SO': 'Somalia', 'ZA': 'South Africa',
            'KR': 'South Korea', 'SS': 'South Sudan', 'ES': 'Spain', 'LK': 'Sri Lanka', 'SD': 'Sudan',
            'SR': 'Suriname', 'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syria', 'TW': 'Taiwan',
            'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand', 'TL': 'Timor-Leste', 'TG': 'Togo',
            'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Turkey', 'TM': 'Turkmenistan',
            'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom',
            'US': 'United States', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VA': 'Vatican City',
            'VE': 'Venezuela', 'VN': 'Vietnam', 'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
        }
        
        return render_template('world_leaderboard.html', 
                             country_stats=country_stats,
                             top_players=top_players,
                             country_names=country_names)
        
    except Exception as e:
        flash(f'Error loading world leaderboard: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/country/<country_code>')
def country_leaderboard(country_code):
    """Country-specific leaderboard with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get players from specific country with points > 0
        total_players = mongo_db.users.count_documents({
            "country": country_code,
            "points": {"$gt": 0}
        })
        
        players = list(mongo_db.users.find(
            {"country": country_code, "points": {"$gt": 0}},
            {"username": 1, "nickname": 1, "points": 1, "country": 1}
        ).sort("points", -1).skip((page - 1) * per_page).limit(per_page))
        
        # Country name mapping (same as above)
        country_names = {
            'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom', 'DE': 'Germany',
            'FR': 'France', 'IT': 'Italy', 'ES': 'Spain', 'RU': 'Russia', 'CN': 'China',
            'JP': 'Japan', 'KR': 'South Korea', 'BR': 'Brazil', 'MX': 'Mexico', 'AU': 'Australia',
            'IN': 'India', 'NL': 'Netherlands', 'SE': 'Sweden', 'NO': 'Norway', 'PL': 'Poland'
        }
        
        country_name = country_names.get(country_code, country_code)
        
        # Pagination info
        has_prev = page > 1
        has_next = (page * per_page) < total_players
        prev_page = page - 1 if has_prev else None
        next_page = page + 1 if has_next else None
        total_pages = (total_players + per_page - 1) // per_page
        
        return render_template('country_leaderboard.html',
                             players=players,
                             country_code=country_code,
                             country_name=country_name,
                             page=page,
                             has_prev=has_prev,
                             has_next=has_next,
                             prev_page=prev_page,
                             next_page=next_page,
                             total_pages=total_pages,
                             total_players=total_players)
        
    except Exception as e:
        flash(f'Error loading country leaderboard: {e}', 'danger')
        return redirect(url_for('world_leaderboard'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)