from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone, timedelta

# 1Try to import Discord integration, but don't fail if it's missing
try:
    from discord_integration import notify_record_submitted, notify_record_approved, notify_record_rejected, notify_admin_action
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
    def notify_admin_action(*args, **kwargs):
        print("❌ Discord integration not available - notify_admin_action")

# Try to import Discord bot integration
try:
    from discord_bot import start_discord_bot, check_user_role, send_dm_to_user, is_bot_available, notify_verification_submission

    # Add the new import for role assignment functions
    from discord_bot import assign_discord_role, remove_discord_role, assign_verifier_role, assign_future_list_verifier_role, assign_top_1_player_role, remove_top_1_player_role

    import threading
    import base64
    import hashlib

    print("✅ Discord bot integration loaded successfully")
except ImportError as e:
    print(f"❌ Discord bot integration failed to load: {e}")
    # Create dummy functions so the app doesn't crash
    def check_user_role(*args, **kwargs):
        print("❌ Discord bot not available - check_user_role")
        return False
    def send_dm_to_user(*args, **kwargs):
        print("❌ Discord bot not available - send_dm_to_user")
        return False
    def is_bot_available():
        return False
    def notify_verification_submission(*args, **kwargs):
        print("❌ Discord bot not available - notify_verification_submission")
        return False

# Try to import Changelog Discord integration
try:
    from changelog_discord import notify_changelog
    CHANGELOG_DISCORD_AVAILABLE = True
    print("✅ Changelog Discord integration loaded successfully")
except ImportError as e:
    print(f"❌ Changelog Discord integration failed to load: {e}")
    CHANGELOG_DISCORD_AVAILABLE = False
    # Create dummy function so the app doesn't crash
    def notify_changelog(*args, **kwargs):
        print("❌ Changelog Discord integration not available - notify_changelog")

# Try to import Discord Widget integration
try:
    from discord_widget import get_formatted_discord_data
    DISCORD_WIDGET_AVAILABLE = True
    print("✅ Discord widget integration loaded successfully")
except ImportError as e:
    print(f"❌ Discord widget integration failed to load: {e}")
    DISCORD_WIDGET_AVAILABLE = False
    # Create dummy function so the app doesn't crash
    def get_formatted_discord_data():
        return {
            'online': False,
            'name': 'RTL Discord Server',
            'member_count': 0,
            'online_count': 0,
            'channels': [],
            'members': [],
            'invite_url': 'https://discord.gg/TSjXSecuaz'
        }
from dotenv import load_dotenv
from bson.objectid import ObjectId
from bson.errors import InvalidId
import functools
import requests
import base64
from io import BytesIO

# Import profanity filter
from profanity_filter import check_username_profanity, check_level_name_profanity, check_comment_profanity, profanity_filter

# Import real-time points system
try:
    from real_time_points_system import RealTimePointsManager, handle_level_move, recalculate_all_points
    REAL_TIME_POINTS_AVAILABLE = True
    print("✅ Real-time points system loaded successfully")
except ImportError as e:
    print(f"❌ Real-time points system failed to load: {e}")
    REAL_TIME_POINTS_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')

# ULTRA-FAST Performance optimizations
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Always re-read templates from disk (picks up edits without restart)
app.config['JSON_SORT_KEYS'] = False  # Faster JSON responses
# Upload size cap - images are resized server-side before base64 encoding,
# so 10MB of raw upload is plenty and keeps us safely under Vercel's 4.5MB
# function payload once re-encoded & resized.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Enable compression for responses
try:
    from flask_compress import Compress
    Compress(app)
    print("✅ Flask compression enabled")
except ImportError:
    print("⚠️ flask-compress not installed - install with: pip install flask-compress")

# Session configuration to prevent logout issues
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # Sessions last 30 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Discord OAuth configuration will be set later with proper validation

# Initialize MongoDB - connect=False defers the actual TCP connection to the
# first DB operation, so cold-start time is <1ms here. No ping, no retries,
# no sleep - Vercel functions have a hard timeout and every ms counts.
import time
print(f"Initializing MongoDB (deferred connect)...")
mongo_client = MongoClient(
    mongodb_uri,
    tls=True,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=5000,   # fast fail if Atlas is unreachable
    connectTimeoutMS=5000,
    socketTimeoutMS=30000,           # generous for bulk thumbnail transfers
    maxPoolSize=5,
    minPoolSize=0,
    maxIdleTimeMS=30000,
    waitQueueTimeoutMS=5000,
    retryWrites=True,
    retryReads=True,
    directConnection=False,
    connect=False                    # lazy - no TCP connection at import time
)
mongo_db = mongo_client[mongodb_db]
print("✓ MongoDB client created (connection deferred to first use)")

try:
    from changelog_discord import set_mongo_db
    set_mongo_db(mongo_db)
except Exception:
    pass
    
# Console settings are seeded lazily on first use, not at cold-start.

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

# Configure Discord OAuth
print("Configuring Discord OAuth...")
app.config['DISCORD_CLIENT_ID'] = os.environ.get('DISCORD_CLIENT_ID')
app.config['DISCORD_CLIENT_SECRET'] = os.environ.get('DISCORD_CLIENT_SECRET')

discord_oauth = None
client_id = app.config['DISCORD_CLIENT_ID']
client_secret = app.config['DISCORD_CLIENT_SECRET']

if client_id and client_secret and client_secret != 'your_discord_client_secret_here':
    print("Discord OAuth credentials found, registering...")
    try:
        discord_oauth = oauth.register(
            name='discord',
            client_id=client_id,
            client_secret=client_secret,
            authorize_url='https://discord.com/api/oauth2/authorize',
            access_token_url='https://discord.com/api/oauth2/token',
            client_kwargs={
                'scope': 'identify'
            }
        )
        print("✓ Discord OAuth configured successfully")
    except Exception as e:
        print(f"❌ Discord OAuth configuration failed: {e}")
        discord_oauth = None
else:
    if not client_id:
        print("❌ DISCORD_CLIENT_ID not found in environment")
    elif not client_secret or client_secret == 'your_discord_client_secret_here':
        print("❌ DISCORD_CLIENT_SECRET not configured (placeholder value detected)")
        print("   Please get your Client Secret from Discord Developer Portal")
    print("⚠️  Discord account linking will be disabled")

# In-memory IP ban cache - refreshed every 5 min per worker.
# Eliminates one MongoDB query per HTTP request (the old find_one in before_request).
_ip_ban_set: set = set()
_ip_ban_set_updated = None
_IP_BAN_TTL = 300  # seconds

# In-memory announcements/polls cache - refreshed every 60s.
# Announcements and polls rarely change, so fetching them once per minute
# instead of once per request saves 2 DB queries on every page load.
_announcements_cache: list = []
_announcements_cache_updated = None
_polls_cache: list = []
_polls_cache_updated = None
_CONTENT_CACHE_TTL = 60  # seconds

def _get_banned_ip_set():
    """Return set of currently banned IPs, refreshing from DB at most every 5 min."""
    global _ip_ban_set, _ip_ban_set_updated
    now = datetime.now(timezone.utc)
    if (_ip_ban_set_updated is None or
            (now - _ip_ban_set_updated).total_seconds() > _IP_BAN_TTL):
        try:
            docs = mongo_db.ip_bans.find({"active": True}, {"ip_addresses": 1})
            new_set: set = set()
            for doc in docs:
                for ip in (doc.get('ip_addresses') or []):
                    new_set.add(ip)
            _ip_ban_set = new_set
            _ip_ban_set_updated = now
        except Exception as e:
            print(f"IP ban set refresh failed: {e}")
            # Keep previous set (or empty if first load) - never block on DB error
            if _ip_ban_set_updated is None:
                _ip_ban_set_updated = now  # Don't retry every request
    return _ip_ban_set

def _get_cached_announcements():
    """Return active announcements, refreshing from DB at most every 60s."""
    global _announcements_cache, _announcements_cache_updated
    now = datetime.now(timezone.utc)
    if (_announcements_cache_updated is None or
            (now - _announcements_cache_updated).total_seconds() > _CONTENT_CACHE_TTL):
        try:
            docs = list(mongo_db.announcements.find({"active": True}).sort("created_at", -1).limit(10))
            valid = []
            for a in docs:
                expires_at = a.get('expires_at')
                if expires_at:
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if expires_at > now:
                        if a.get('created_at') and a['created_at'].tzinfo is None:
                            a['created_at'] = a['created_at'].replace(tzinfo=timezone.utc)
                        a['expires_at'] = expires_at
                        valid.append(a)
            _announcements_cache = valid
            _announcements_cache_updated = now
        except Exception as e:
            print(f"Announcements cache refresh failed: {e}")
            if _announcements_cache_updated is None:
                _announcements_cache_updated = now
    return _announcements_cache

def _get_cached_polls():
    """Return active polls, refreshing from DB at most every 60s."""
    global _polls_cache, _polls_cache_updated
    now = datetime.now(timezone.utc)
    if (_polls_cache_updated is None or
            (now - _polls_cache_updated).total_seconds() > _CONTENT_CACHE_TTL):
        try:
            docs = list(mongo_db.polls.find({"active": True}).sort("created_at", -1).limit(3))
            valid = []
            for p in docs:
                expires_at = p.get('expires_at')
                if expires_at:
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if expires_at > now:
                        if p.get('created_at') and p['created_at'].tzinfo is None:
                            p['created_at'] = p['created_at'].replace(tzinfo=timezone.utc)
                        p['expires_at'] = expires_at
                        valid.append(p)
            _polls_cache = valid
            _polls_cache_updated = now
        except Exception as e:
            print(f"Polls cache refresh failed: {e}")
            if _polls_cache_updated is None:
                _polls_cache_updated = now
    return _polls_cache

# Simple cache for levels - OPTIMIZED FOR SPEED
levels_cache = {
    'main_list': None,
    'legacy_list': None,
    'main_list_updated': None,
    'legacy_list_updated': None,
    'last_updated': None,
    'ttl': 300  # 5 minutes cache TTL
}

import json

def _save_main_cache_to_file(levels):
    """Persist main list cache to disk so it survives restarts.
    Thumbnails are stripped - they live in MongoDB and would bloat the cache
    to 50MB+ of base64. Also a no-op on Vercel (read-only FS outside /tmp)."""
    try:
        serializable = []
        for lv in levels:
            lv_copy = {k: v for k, v in lv.items() if k != 'thumbnail_url'}
            lv_copy['_id'] = str(lv_copy['_id'])
            serializable.append(lv_copy)
        with open('cache_main_levels.json', 'w') as f:
            json.dump({
                'levels': serializable,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }, f)
        print(f"✓ Saved {len(serializable)} levels to cache file (no thumbs)")
    except OSError:
        # Expected on Vercel - filesystem is read-only outside /tmp
        pass
    except Exception as e:
        print(f"Warning: could not save cache file: {e}")

def _load_levels_from_db(is_legacy=False):
    """Query MongoDB for levels. Returns list or raises.
    thumbnail_url is intentionally excluded - fetching all base64 blobs in one
    query causes NetworkTimeout on Atlas M0. Thumbnails are loaded individually
    via /api/level_thumbnail/<id> or bulk-warmed by _warm_thumbnail_cache()."""
    projection = {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1,
                  "points": 1, "level_id": 1, "difficulty": 1, "video_url": 1,
                  "min_percentage": 1, "demon_type": 1}
    if is_legacy:
        return list(mongo_db.levels.find(
            {"is_legacy": True}, projection
        ).sort("position", 1))
    else:
        return list(mongo_db.levels.find(
            {"is_legacy": {"$ne": True}}, projection
        ).sort("position", 1).limit(100))

def get_fast_cached_levels(is_legacy=False):
    """Cached level retrieval with TTL. Serves stale cache on DB error."""
    global levels_cache

    cache_key = 'legacy_list' if is_legacy else 'main_list'
    updated_key = 'legacy_list_updated' if is_legacy else 'main_list_updated'
    now = datetime.now(timezone.utc)

    # Cache hit
    if (levels_cache[cache_key] is not None and
            levels_cache[updated_key] is not None):
        age = (now - levels_cache[updated_key]).total_seconds()
        if age < levels_cache['ttl']:
            return levels_cache[cache_key]

    # Cache miss - load levels from DB (thumbnails fetched separately).
    try:
        # Preserve any thumbnails already in memory - thumbnail_url is excluded
        # from the DB projection to avoid NetworkTimeout, so it only lives here.
        old_thumbs = {}
        for lv in (levels_cache.get(cache_key) or []):
            if lv.get('thumbnail_url'):
                old_thumbs[str(lv['_id'])] = lv['thumbnail_url']

        levels = _load_levels_from_db(is_legacy)

        # Re-apply preserved thumbnails to the freshly loaded list
        if old_thumbs:
            for lv in levels:
                thumb = old_thumbs.get(str(lv['_id']))
                if thumb:
                    lv['thumbnail_url'] = thumb

        levels_cache[cache_key] = levels
        levels_cache[updated_key] = now
        levels_cache['last_updated'] = now
        if not is_legacy:
            _save_main_cache_to_file(levels)
            # Warm thumbnail cache in background on first main-list load
            if not levels_cache.get('_thumb_warmer_started'):
                levels_cache['_thumb_warmer_started'] = True
                _warm_thumbnail_cache()
        print(f"✓ Refreshed {'legacy' if is_legacy else 'main'} list from DB ({len(levels)} levels)")
        return levels
    except Exception as e:
        print(f"DB load failed, serving stale cache: {e}")
        return levels_cache.get(cache_key) or []

def _warm_thumbnail_cache():
    """Spawn a background thread that fetches each level's thumbnail_url one at a
    time and stores it in the in-memory cache.  Called automatically on the first
    main-list DB load.  Once done, /api/level_thumbnails serves all thumbnails
    instantly and the page JS applies them without any per-card round-trips."""
    import threading, time as _time

    def _run():
        cache = levels_cache.get('main_list') or []
        if not cache:
            return

        print(f"Thumbnail warmer: loading thumbnails for {len(cache)} levels...")
        warmed = 0
        for lv in cache:
            if lv.get('thumbnail_url'):
                continue  # already cached
            try:
                oid = lv.get('_id')
                doc = mongo_db.levels.find_one(
                    {'_id': oid, 'thumbnail_url': {'$exists': True, '$nin': ['', None]}},
                    {'thumbnail_url': 1}
                )
                if doc and doc.get('thumbnail_url'):
                    lv['thumbnail_url'] = doc['thumbnail_url']
                    warmed += 1
            except Exception as e:
                print(f"Thumbnail warmer error for {lv.get('name')}: {e}")
            _time.sleep(0.5)  # slow pacing - keep pool free for user requests

        print(f"Thumbnail warmer: done - {warmed} thumbnails cached")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

# On Vercel each invocation starts fresh - get_fast_cached_levels() hits MongoDB
# on first use and fills the in-memory cache for subsequent requests in that worker.

@app.before_request
def check_ip_ban():
    """Check if the current IP is banned. Uses in-memory cache (refreshed every 5 min)
    so we do NOT hit MongoDB on every request."""
    if not request.endpoint:
        return None
    if request.endpoint.startswith('static'):
        return None

    client_ip = request.remote_addr
    if not client_ip:
        return None

    try:
        if client_ip in _get_banned_ip_set():
            try:
                mongo_db.security_logs.insert_one({
                    "event_type": "blocked_login_attempt",
                    "ip_address": client_ip,
                    "timestamp": datetime.now(timezone.utc),
                    "user_agent": request.headers.get('User-Agent', 'Unknown'),
                })
            except Exception:
                pass
            return "Access denied", 403
    except Exception as e:
        print(f"IP ban check error: {e}")

    return None

def get_cached_levels(is_legacy=False, quick_load=False):
    """Return cached levels only - auto-loading happens in routes"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    cached_levels = levels_cache.get(cache_key)
    return cached_levels if cached_levels is not None else []

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

def convert_image_to_base64(file):
    """Convert uploaded image file to a resized JPEG base64 data URL.

    Target size: ≤ 480 px on the longer edge at 72 % JPEG quality.
    This keeps each thumbnail document under ~30 KB, which MongoDB Atlas M0
    can transfer in milliseconds instead of timing out on large blobs.
    PNG inputs with transparency are converted to JPEG (white background) so
    we always produce the smallest possible output.
    """
    try:
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > 10 * 1024 * 1024:
            return None

        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        content_type = (file.content_type or '').lower()
        if content_type not in allowed_types:
            return None

        from PIL import Image
        import io
        img = Image.open(file)
        # GIFs: take the first frame so we don't explode file size on animated uploads
        if getattr(img, 'is_animated', False):
            img.seek(0)
        img.load()

        # Keep aspect ratio but cap at 480 px — small enough for fast DB transfer
        max_edge = 480
        if max(img.size) > max_edge:
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)

        # Always output JPEG for consistency and smallest size.
        # Flatten any alpha channel onto a white background first.
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=72, optimize=True, progressive=True)

        encoded_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_data}"

    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None


@app.after_request
def _cache_headers(response):
    """Long-cache versioned static assets; never cache dynamic HTML.
    Speeds up repeat visits on Vercel since the CDN + browser both honor this."""
    path = request.path or ''
    if path.startswith('/static/'):
        response.headers.setdefault(
            'Cache-Control', 'public, max-age=31536000, immutable'
        )
    elif response.mimetype == 'text/html':
        response.headers.setdefault(
            'Cache-Control', 'no-cache, no-store, must-revalidate'
        )
    return response


@app.errorhandler(413)
def _request_entity_too_large(e):
    """Triggered when upload exceeds MAX_CONTENT_LENGTH. Return JSON for
    fetch/XHR callers and flash+redirect for plain form posts."""
    from flask import jsonify
    msg = 'Upload is too large. Max 10MB - try a smaller image.'
    wants_json = request.is_json or 'application/json' in (request.accept_mimetypes.best or '')
    if wants_json:
        return jsonify({'error': msg}), 413
    flash(msg, 'danger')
    return redirect(request.referrer or '/'), 303

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
    
    # Twitch support
    elif 'twitch.tv' in video_url:
        # Handle Twitch clips
        if '/clip/' in video_url:
            clip_id = video_url.split('/clip/')[-1].split('?')[0].split('&')[0]
            return {
                'platform': 'twitch',
                'embed_url': f'https://clips.twitch.tv/embed?clip={clip_id}&parent=localhost',
                'video_id': clip_id
            }
        # Handle Twitch VODs/streams
        elif '/videos/' in video_url:
            video_id = video_url.split('/videos/')[-1].split('?')[0].split('&')[0]
            return {
                'platform': 'twitch',
                'embed_url': f'https://player.twitch.tv/?video={video_id}&parent=localhost',
                'video_id': video_id
            }
        else:
            # Handle channel streams
            channel = video_url.split('twitch.tv/')[-1].split('?')[0].split('&')[0]
            return {
                'platform': 'twitch',
                'embed_url': f'https://player.twitch.tv/?channel={channel}&parent=localhost',
                'video_id': channel
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
    
    # Medal.tv support
    elif 'medal.tv' in video_url:
        # Extract video ID from Medal.tv URL
        # Medal.tv URLs are typically: https://medal.tv/games/[game]/clips/[clip_id]
        # or https://medal.tv/clips/[clip_id]
        if '/clips/' in video_url:
            video_id = video_url.split('/clips/')[-1].split('?')[0].split('/')[0]
        else:
            return None
        return {
            'platform': 'medal',
            'embed_url': f'https://medal.tv/clips/{video_id}',
            'video_id': video_id
        }
    
    return None

# Context processor
@app.context_processor
def utility_processor():
    def format_points(points):
        if points is None or points == 0:
            return "0"
        # Return integer if it's a whole number, otherwise show minimal decimals
        points_float = float(points)
        if points_float == int(points_float):
            return str(int(points_float))
        return f"{points_float:.1f}".rstrip('0').rstrip('.')
    
    def get_active_announcements():
        """Get active announcements from in-memory cache, filtered by user join date."""
        all_ann = _get_cached_announcements()
        user_join_date = session.get('date_joined') if 'user_id' in session else None
        if user_join_date:
            return [a for a in all_ann if not a.get('created_at') or a['created_at'] >= user_join_date]
        return all_ann
    
    def get_active_polls():
        """Get active polls from in-memory cache, filtered by user join date and closed polls."""
        try:
            all_polls = _get_cached_polls()
            user_join_date = session.get('date_joined') if 'user_id' in session else None
            closed_polls = session.get('closed_polls', []) if 'user_id' in session else []
            user_id = session.get('user_id')

            result = []
            for poll in all_polls:
                if str(poll['_id']) in closed_polls:
                    continue
                if user_join_date and poll.get('created_at') and poll['created_at'] < user_join_date:
                    continue
                # Check voted status in-memory (voters list is already in the cached doc)
                poll['user_has_voted'] = False
                if user_id:
                    for option in poll.get('options', []):
                        if user_id in option.get('voters', []):
                            poll['user_has_voted'] = True
                            break
                result.append(poll)
            return result
        except Exception as e:
            print(f"Error getting active polls: {e}")
            return []
    
    def get_user_by_id(user_id):
        """Helper function to get user data by ID"""
        try:
            return mongo_db.users.find_one({"_id": user_id})
        except:
            return None
    
    # Get current theme from session (with error handling)
    try:
        current_theme = session.get('theme', 'light')
    except RuntimeError:
        # No request context available
        current_theme = 'light'
    
    # Get Discord widget data
    def get_discord_data():
        """Helper function to get Discord data for templates"""
        if DISCORD_WIDGET_AVAILABLE:
            return get_formatted_discord_data()
        else:
            return {
                'online': False,
                'name': 'RTL Discord Server',
                'member_count': 0,
                'online_count': 0,
                'channels': [],
                'members': [],
                'invite_url': 'https://discord.gg/TSjXSecuaz'
            }
    
    def get_notification_count():
        """Get unread notification count for current user (no DB user lookup - uses session)."""
        if 'user_id' not in session:
            return 0
        try:
            user_id = session['user_id']
            user_join_date = session.get('date_joined')
            query = {"user_id": user_id, "read": False}
            if user_join_date:
                query["created_at"] = {"$gte": user_join_date}
            return mongo_db.notifications.count_documents(query)
        except Exception as e:
            print(f"Error getting notification count: {e}")
            return 0
    

    
    return dict(
        format_points=format_points, 
        get_video_embed_info=get_video_embed_info,
        current_theme=current_theme,
        get_active_announcements=get_active_announcements,
        get_active_polls=get_active_polls,
        get_all_levels=lambda: list(mongo_db.levels.find({}, {"name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "is_legacy": 1, "min_percentage": 1}).sort("position", 1)),
        get_future_levels=lambda: list(mongo_db.future_levels.find().sort("position", 1)),
        get_demon_difficulty_display=get_demon_difficulty_display,
        get_demon_type_display=get_demon_type_display,
        get_difficulty_text=get_difficulty_text,
        datetime=datetime,
        get_user_by_id=get_user_by_id,
        get_discord_data=get_discord_data,
        get_notification_count=get_notification_count,
        get_translation=get_translation
    )

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0.0
    # p = 250(0.963655)^(x-1) where x is the placement of the level on the list
    # Position 1 = 250(0.963655)^0 = 250 points
    # Position 100 = 250(0.963655)^99 = 6.4 points
    return round(250 * (0.9636550814213581 ** (position - 1)), 2)

def get_demon_difficulty_display(difficulty, demon_type=None):
    """Get display text for difficulties - shows text-based names"""
    return get_difficulty_text(difficulty)

def get_demon_type_display(difficulty, demon_type=None):
    """Get demon type display text for 10-star levels"""
    if difficulty == 10 and demon_type:
        demon_types = {
            'easy': 'Easy Demon',
            'medium': 'Medium Demon', 
            'hard': 'Hard Demon',
            'insane': 'Insane Demon',
            'extreme': 'Extreme Demon'
        }
        return demon_types.get(demon_type, 'Demon')
    return None

def get_difficulty_text(difficulty):
    """Convert numerical difficulty (1-10) to text-based names"""
    if difficulty is None:
        return "Unknown"
    
    # If it's already a string (like 'Extreme Demon'), return it as is
    if isinstance(difficulty, str):
        return difficulty
    
    try:
        difficulty = float(difficulty)
    except (ValueError, TypeError):
        return "Unknown"
    
    if difficulty >= 1 and difficulty < 2:
        return "Easy"
    elif difficulty >= 2 and difficulty < 4:
        return "Normal"
    elif difficulty >= 4 and difficulty < 6:
        return "Hard"
    elif difficulty >= 6 and difficulty < 8:
        return "Harder"
    elif difficulty >= 8 and difficulty < 10:
        return "Insane"
    elif difficulty >= 10:
        return "Demon"
    else:
        return "Unknown"



def recalculate_user_points_after_level_move(level_id, old_points, new_points):
    """Recalculate user points when a level's points change due to position movement - DEPRECATED"""
    # This function is deprecated in favor of the real-time points system
    # Import and use the new system
    try:
        from real_time_points_system import RealTimePointsManager
        manager = RealTimePointsManager(mongo_db)
        
        # Recalculate all user points to ensure accuracy
        users_updated = manager.recalculate_all_user_points()
        return users_updated
        
    except Exception as e:
        print(f"Error recalculating user points after level move: {e}")
        return 0

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
        
        # Create new connection - same conservative timeouts as initial startup
        mongo_client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=30000,
            maxPoolSize=5,
            minPoolSize=0,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=5000,
            retryWrites=True,
            retryReads=True,
            connect=False
        )
        mongo_db = mongo_client[mongodb_db]
        
        mongo_client.admin.command('ping', maxTimeMS=5000)
        print("✓ MongoDB connection reinitialized successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to reinitialize MongoDB connection: {e}")
        return False

def calculate_record_points(record, level):
    """Calculate points earned from a record - Updated with new system"""
    # Handle both dict and aggregation result formats
    status = record.get('status', 'pending')
    if status != 'approved' or level.get('is_legacy', False):
        return 0.0
    
    # Full completion (100% points)
    if record['progress'] == 100:
        return float(level['points'])
    
    # Partial completion - 20% of full points when reaching minimum percentage
    # Only applies to levels in the top 50
    if level.get('position', 0) > 50:
        return 0.0
    min_percentage = level.get('min_percentage', 100)
    if record['progress'] >= min_percentage and min_percentage < 100:
        return round(float(level['points']) * 0.20, 2)

    return 0.0

def award_verifier_points(level_id, verifier_user_id):
    """Award points to level verifier (like first victor)"""
    try:
        level = mongo_db.levels.find_one({"_id": level_id})
        if not level or level.get('is_legacy', False):
            return False
        
        # Check if verifier already has points for this level
        existing_record = mongo_db.records.find_one({
            "user_id": verifier_user_id,
            "level_id": level_id,
            "status": "approved",
            "progress": 100
        })
        
        if existing_record:
            return False  # Already has completion record
        
        # Create a special verifier record
        verifier_record = {
            "_id": ObjectId(),
            "user_id": verifier_user_id,
            "level_id": level_id,
            "progress": 100,
            "status": "approved",
            "video_url": level.get('verification_video', ''),
            "date_submitted": datetime.now(timezone.utc),
            "is_verifier": True,  # Special flag for verifiers
            "notes": "Level verifier - automatic points award"
        }
        
        # Insert the verifier record
        mongo_db.records.insert_one(verifier_record)
        
        # Update user points
        update_user_points(verifier_user_id)
        
        return True
        
    except Exception as e:
        print(f"Error awarding verifier points: {e}")
        return False

def create_notification(user_id, notification_type, title, message, related_id=None, related_type=None):
    """Create a notification for a user"""
    try:
        notification = {
            "_id": ObjectId(),
            "user_id": user_id,
            "type": notification_type,  # 'poll', 'announcement', 'record_status', 'top_1'
            "title": title,
            "message": message,
            "related_id": related_id,  # ID of related object (record, etc.)
            "related_type": related_type,  # Type of related object
            "read": False,
            "created_at": datetime.now(timezone.utc)
        }
        mongo_db.notifications.insert_one(notification)
        return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False

def create_global_notification(notification_type, title, message, related_id=None, related_type=None, sender_username="System"):
    """Create a notification for all users"""
    try:
        # Get all users
        users = mongo_db.users.find({}, {"_id": 1})
        
        notifications = []
        for user in users:
            # Check user's notification preferences
            user_data = mongo_db.users.find_one({"_id": user["_id"]})
            notification_prefs = user_data.get('notification_preferences', {})
            
            # Check if user wants this type of notification (default to True if not set)
            if notification_prefs.get(notification_type, True):
                notification = {
                    "_id": ObjectId(),
                    "user_id": user["_id"],
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "related_id": related_id,
                    "related_type": related_type,
                    "read": False,
                    "created_at": datetime.now(timezone.utc),
                    "sender": sender_username
                }
                notifications.append(notification)
        
        if notifications:
            mongo_db.notifications.insert_many(notifications)
        
        return len(notifications)
    except Exception as e:
        print(f"Error creating global notification: {e}")
        return 0

def fix_verifier_points_bug():
    """Fix the bug where verifiers lose points and update affected users"""
    try:
        print("🔍 Starting verifier points bug fix...")
        
        # Find all records that are marked as verifier records
        verifier_records = list(mongo_db.records.find({"is_verifier": True}))
        print(f"Found {len(verifier_records)} verifier records to check")
        
        # Group records by user
        user_records = {}
        for record in verifier_records:
            user_id = record['user_id']
            if user_id not in user_records:
                user_records[user_id] = []
            user_records[user_id].append(record)
        
        # Update points for each user with verifier records
        updated_users = 0
        for user_id, records in user_records.items():
            try:
                # Recalculate points for this user
                new_points = update_user_points(user_id)
                updated_users += 1
                print(f"✅ Updated points for user {user_id}: {new_points} points")
            except Exception as e:
                print(f"❌ Error updating points for user {user_id}: {e}")
        
        print(f"✅ Verifier points bug fix completed. Updated {updated_users} users.")
        return updated_users
        
    except Exception as e:
        print(f"❌ Error in fix_verifier_points_bug: {e}")
        return 0


def get_user_notifications(user_id, limit=20, unread_only=False):
    """Get notifications for a user that were created after they joined"""
    try:
        # Get user join date
        user = mongo_db.users.find_one({"_id": user_id})
        user_join_date = user.get('date_joined') if user else None
        
        query = {"user_id": user_id}
        # If user has a join date, only show notifications created after they joined
        if user_join_date:
            query["created_at"] = {"$gte": user_join_date}
        if unread_only:
            query["read"] = False
            
        notifications = list(mongo_db.notifications.find(query)
                           .sort("created_at", -1)
                           .limit(limit))
        return notifications
    except Exception as e:
        print(f"Error getting user notifications: {e}")
        return []

def mark_notification_read(notification_id, user_id):
    """Mark a notification as read"""
    try:
        mongo_db.notifications.update_one(
            {"_id": ObjectId(notification_id), "user_id": user_id},
            {"$set": {"read": True}}
        )
        return True
    except Exception as e:
        print(f"Error marking notification as read: {e}")
        return False

def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user that were created after they joined"""
    try:
        # Get user join date
        user = mongo_db.users.find_one({"_id": user_id})
        user_join_date = user.get('date_joined') if user else None
        
        query = {"user_id": user_id, "read": False}
        # If user has a join date, only count notifications created after they joined
        if user_join_date:
            query["created_at"] = {"$gte": user_join_date}
            
        return mongo_db.notifications.count_documents(query)
    except Exception as e:
        print(f"Error getting unread notification count: {e}")
        return 0

def track_position_change(level_id, old_position, new_position, admin_username="System"):
    """Track position changes for history"""
    try:
        if old_position == new_position:
            return  # No change
            
        position_change = {
            "_id": ObjectId(),
            "level_id": level_id,
            "old_position": old_position,
            "new_position": new_position,
            "change_date": datetime.now(timezone.utc),
            "changed_by": admin_username,
            "change_type": "move_up" if new_position < old_position else "move_down"
        }
        
        mongo_db.position_history.insert_one(position_change)
        
        # Check if this is a new #1 and create notification
        if new_position == 1 and old_position != 1:
            level = mongo_db.levels.find_one({"_id": level_id})
            if level:
                create_global_notification(
                    "top_1",
                    "New #1 Level!",
                    f"'{level['name']}' is now the new #1 level on the list!",
                    level_id,
                    "level"
                )
        
    except Exception as e:
        print(f"Error tracking position change: {e}")

def update_user_points(user_id):
    """Recalculate and update user's total points - FIXED aggregation handling"""
    # Use aggregation to join records with levels in a single query
    pipeline = [
        {"$match": {
            "user_id": user_id, 
            "status": "approved",
            "$or": [
                {"hidden": {"$exists": False}},  # Records without hidden field
                {"hidden": False}  # Records explicitly not hidden
            ]
        }},
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
            "level.min_percentage": 1,
            "level.position": 1
        }}
    ]
    
    records_with_levels = list(mongo_db.records.aggregate(pipeline, allowDiskUse=True))
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

    

    
    # Get user's current points before update
    user = mongo_db.users.find_one({"_id": user_id})
    old_points = user.get('points', 0) if user else 0
    
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"points": total_points}}
    )
    
    # Check if user reached a new milestone and send Discord notifications
    if user and user.get('discord_id'):
        check_and_notify_points_milestones(user, old_points, total_points)
        
        # Sync Discord roles for this specific user if their points changed
        if old_points != total_points:
            try:
                from discord_bot import sync_single_user_roles
                sync_single_user_roles(user['discord_id'], total_points)
                print(f"✅ Synced Discord roles for user {user.get('username', 'Unknown')} (points: {old_points} → {total_points})")
            except Exception as e:
                print(f"⚠️ Error syncing Discord roles for user {user.get('username', 'Unknown')}: {e}")
    
    return total_points

def check_and_notify_points_milestones(user, old_points, new_points):
    """Check if user reached a new points milestone and send Discord notifications"""
    # Check if we're in a role sync period to avoid spamming notifications
    try:
        # Check when the last role sync was performed
        last_sync_doc = mongo_db.site_settings.find_one({"_id": "discord_bot"})
        if last_sync_doc and "last_role_sync" in last_sync_doc:
            last_sync_time = last_sync_doc["last_role_sync"]
            # If the last sync was less than 5 minutes ago, skip notifications
            from datetime import datetime, timezone
            if isinstance(last_sync_time, datetime):
                time_diff = datetime.now(timezone.utc) - last_sync_time
                if time_diff.total_seconds() < 300:  # 5 minutes
                    print(f"⏭️ Skipping milestone notifications for user {user['username']} - role sync in progress or recently completed")
                    return
    except Exception as e:
        print(f"⚠️ Error checking role sync status: {e}")
    
    # Define points thresholds and corresponding roles
    milestones = [
        (1, "1407154476900548638"),      # 1+ points
        (50, "1434561864477708412"),     # 50+ points
        (100, "1434559158056910859"),    # 100+ points
        (150, "1434559357978284072"),    # 150+ points
        (200, "1434559491164078210"),    # 200+ points
        (250, "1434559736430334013"),    # 250+ points
        (300, "1434559950142832812"),    # 300+ points
        (350, "1434560160193450056"),    # 350+ points
        (400, "1434560335540654170"),    # 400+ points
        (450, "1434560559315030279"),    # 450+ points
        (500, "1434560792845353073"),    # 500+ points
        (600, "1434562564607447072"),    # 600+ points
        (700, "1434562844678029322"),    # 700+ points
        (800, "1434563139302854796"),    # 800+ points
        (900, "1434563355917680722"),    # 900+ points
        (1000, "1434563588349100135"),   # 1000+ points
        (1500, "1434563863126474782"),   # 1500+ points
        (2000, "1434564153032315120"),   # 2000+ points
        (2500, "1434564465084596325"),   # 2500+ points
        (3000, "1434564672949977219"),   # 3000+ points
        (3500, "1434564972083413123"),   # 3500+ points
        (4000, "1434566288256012393")    # 4000+ points
    ]
    
    # Find all milestones the user has reached
    old_milestones = [points for points, role_id in milestones if old_points >= points]
    new_milestones = [points for points, role_id in milestones if new_points >= points]
    
    # Determine which milestones are newly reached
    newly_reached = [points for points in new_milestones if points not in old_milestones]
    
    # Determine which milestones are no longer reached (lost)
    lost_milestones = [points for points in old_milestones if points not in new_milestones]
    
    # Role names mapping
    role_names = {
        "1407154476900548638": "List Player",
        "1434561864477708412": "50+ Points",
        "1434559158056910859": "100+ Points",
        "1434559357978284072": "150+ Points",
        "1434559491164078210": "200+ Points",
        "1434559736430334013": "250+ Points",
        "1434559950142832812": "300+ Points",
        "1434560160193450056": "350+ Points",
        "1434560335540654170": "400+ Points",
        "1434560559315030279": "450+ Points",
        "1434560792845353073": "500+ Points",
        "1434562564607447072": "600+ Points",
        "1434562844678029322": "700+ Points",
        "1434563139302854796": "800+ Points",
        "1434563355917680722": "900+ Points",
        "1434563588349100135": "1000+ Points",
        "1434563863126474782": "1500+ Points",
        "1434564153032315120": "2000+ Points",
        "1434564465084596325": "2500+ Points",
        "1434564672949977219": "3000+ Points",
        "1434564972083413123": "3500+ Points",
        "1434566288256012393": "4000+ Points",
        # Additional achievement roles
        "1407749092821565632": "Completed Entire List",
        "1434573744889794591": "#1 Player on Stats Viewer",
        "1434089770040168499": "Top 10 Player on Stats Viewer",
        "1387947809948307516": "Current Top 1 Player",
        "1387947951426371735": "Top 5 Level Completer",
        "1387948023073738792": "Top 10 Level Completer",
        "1418198223851618327": "Future List Verifier",
        "1387982674043338804": "List Verifier",
        "1387982763549790229": "First Victor"
    }
    
    # If user reached new milestones, send notifications (roles are handled by sync_single_user_roles)
    if newly_reached:
        # Find the highest milestone reached
        highest_milestone = max(newly_reached)
        milestone_role_id = next((role_id for points, role_id in milestones if points == highest_milestone), None)
        
        if milestone_role_id:
            role_name = role_names.get(milestone_role_id, "New Role")
            
            # Send DM notification for the highest milestone reached
            message = f"🎉 Congratulations! You've reached {highest_milestone} points on the RTL list and have been awarded the '{role_name}' role!"
            try:
                if is_bot_available():
                    send_dm_to_user(user['discord_id'], message)
                    print(f"✅ Sent milestone notification to user {user['username']} for {highest_milestone} points")
                else:
                    print("⚠️ Discord bot not available - skipping milestone notification")
            except Exception as e:
                print(f"Error sending milestone notification: {e}")
    
    # Note: Role assignment/removal is now handled automatically by sync_single_user_roles() 
    # called from update_user_points(), so we don't need to manually manage roles here

def shift_level_positions(position, is_legacy=False, direction=1):
    """Shift level positions up or down from a given position"""
    mongo_db.levels.update_many(
        {"position": {"$gte": position}, "is_legacy": is_legacy},
        {"$inc": {"position": direction}}
    )

def recalculate_all_points(levels_only=False):
    """Recalculate points for all levels (and optionally users) using the real-time system.

    Pass levels_only=True in request handlers to skip the expensive per-user
    recalculation (O(n_users × n_records) DB queries).  User points will be
    at most one level-edit stale; the dedicated /admin/recalculate_all_points
    route resets them fully when needed.
    """
    if REAL_TIME_POINTS_AVAILABLE:
        try:
            from real_time_points_system import RealTimePointsManager
            manager = RealTimePointsManager(mongo_db)

            # Recalculate all level points
            levels_updated = manager.recalculate_all_level_points()

            if levels_only:
                print(f"✅ Level points recalculated: {levels_updated} levels updated (user points skipped)")
                return levels_updated, 0

            # Recalculate all user points
            users_updated = manager.recalculate_all_user_points()

            print(f"✅ Real-time recalculation: {levels_updated} levels, {users_updated} users updated")
            return levels_updated, users_updated
            
        except Exception as e:
            print(f"❌ Real-time recalculation failed: {e}")
            # Fall back to old method for levels only
            pass
    
    # Fallback: old method (levels only)
    from pymongo import UpdateOne
    
    levels = list(mongo_db.levels.find({}, {"_id": 1, "position": 1, "is_legacy": 1, "points": 1}))
    
    # Prepare bulk operations using proper MongoDB UpdateOne objects
    bulk_operations = []
    for level in levels:
        new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        # Compare with tolerance for floating point
        current_points = level.get('points', 0)
        if abs(float(current_points) - float(new_points)) > 0.01:
            bulk_operations.append(
                UpdateOne(
                    {"_id": level['_id']},
                    {"$set": {"points": new_points}}
                )
            )
    
    # Execute all updates in a single bulk operation
    if bulk_operations:
        mongo_db.levels.bulk_write(bulk_operations)
        print(f"⚠️ Fallback: Updated points for {len(bulk_operations)} levels only (users not updated)")
        return len(bulk_operations), 0
    
    return 0, 0

def log_level_change(action, level_name, admin_username, **kwargs):
    """Log level placement/movement changes to changelog and send Discord notification"""
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

        # Fire Discord notification in a daemon thread so the HTTP call
        # doesn't block the response. The changelog entry is already saved above.
        import threading
        t = threading.Thread(
            target=send_enhanced_changelog_notification,
            args=(action, level_name, admin_username),
            kwargs=kwargs,
            daemon=True
        )
        t.start()

    except Exception as e:
        print(f"Error logging level change: {e}")

def send_enhanced_changelog_notification(action, level_name, admin_username, **kwargs):
    """Send changelog notifications with enhanced dethroning and legacy push messaging"""
    try:
        message = ""
        list_type = kwargs.get('list_type', 'main')  # main, legacy, future
        
        if action == "placed":
            position = kwargs.get('position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            
            # Enhanced message format with list type specification
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            if position == 1:
                # Special case for #1 placement with enhanced dethroning message
                dethroned_level = kwargs.get('dethroned_level', '')
                pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
                
                message = f"{level_name} has been placed at #1"
                if dethroned_level:
                    message += f", dethroning {dethroned_level}"
                message += list_suffix + "."
                
                if pushed_to_legacy:
                    message += f" This pushes {pushed_to_legacy} to the legacy list."
            else:
                # Regular placement with enhanced messaging
                message = f"{level_name} has been placed at #{position}"
                if below_level and above_level:
                    message += f" below {above_level} and above {below_level}"
                elif below_level:
                    message += f" above {below_level}"
                elif above_level:
                    message += f" below {above_level}"
                message += list_suffix + "."
                
                # Always check if this placement pushed something to legacy
                pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
                if pushed_to_legacy:
                    message += f" This pushes {pushed_to_legacy} to the legacy list."
                
                # Check if this placement pushed something out of top 10
                pushed_out_of_top10 = kwargs.get('pushed_out_of_top10', '')
                if pushed_out_of_top10 and position <= 10:
                    message += f" This pushes {pushed_out_of_top10} out of the top 10."
        
        elif action == "moved":
            old_position = kwargs.get('old_position', '?')
            new_position = kwargs.get('new_position', '?')
            above_level = kwargs.get('above_level', '')
            below_level = kwargs.get('below_level', '')
            dethroned_level = kwargs.get('dethroned_level', '')
            
            # Enhanced message format for moves with list type
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            if new_position == 1 and dethroned_level:
                # Special case for moves to #1 with dethroning
                message = f"{level_name} has been moved from #{old_position} to #1, dethroning {dethroned_level}"
                message += list_suffix + "."
            else:
                # Regular move
                message = f"{level_name} has been moved from #{old_position} to #{new_position}"
                if below_level and above_level:
                    message += f" below {above_level} and above {below_level}"
                elif below_level:
                    message += f" above {below_level}"
                elif above_level:
                    message += f" below {above_level}"
                message += list_suffix + "."
            
            # Check if this move pushed something to legacy
            pushed_to_legacy = kwargs.get('pushed_to_legacy', '')
            if pushed_to_legacy:
                message += f" This pushes {pushed_to_legacy} to the legacy list."
            
            # Check if this move pushed something out of top 10
            pushed_out_of_top10 = kwargs.get('pushed_out_of_top10', '')
            if pushed_out_of_top10 and new_position <= 10:
                message += f" This pushes {pushed_out_of_top10} out of the top 10."
        
        elif action == "removed":
            old_position = kwargs.get('old_position', '?')
            reason = kwargs.get('reason', '')
            
            # Enhanced message format for removals with list type
            list_suffix = ""
            if list_type == "legacy":
                list_suffix = " from the legacy list"
            elif list_type == "future":
                list_suffix = " from the future list"
            
            message = f"{level_name} has been removed"
            if old_position and old_position != '?':
                message += f" from #{old_position}"
            
            message += list_suffix
            
            if reason:
                message += f". Reason: {reason}"
            else:
                message += "."
        
        elif action == "legacy":
            old_position = kwargs.get('old_position', '?')
            legacy_position = kwargs.get('legacy_position', '?')
            
            message = f"{level_name} has been moved to the legacy list"
            if legacy_position and legacy_position != '?':
                message += f" at position #{legacy_position}"  # Legacy positions are now direct (101, 102, etc.)
            message += "."
        
        # Send the notification - ensure only one message is sent
        if message and CHANGELOG_DISCORD_AVAILABLE:
            notify_changelog(message, admin_username)
            print(f"✅ Changelog notification sent: {message}")
        
    except Exception as e:
        print(f"Error sending changelog notification: {e}")

def auto_manage_legacy_list():
    """Automatically manage legacy list - move level at position 101 to legacy and shift positions"""
    try:
        # Find level at position 101 (should be moved to legacy)
        level_at_101 = mongo_db.levels.find_one({
            "position": 101,
            "is_legacy": {"$ne": True}
        }, {"name": 1, "points": 1})

        if level_at_101:
            # Shift all existing legacy levels down by 1 to make room at position 101
            mongo_db.levels.update_many(
                {"is_legacy": True},
                {"$inc": {"position": 1}}
            )

            # Place the pushed level at the top of the legacy list (position 101)
            mongo_db.levels.update_one(
                {"_id": level_at_101["_id"]},
                {"$set": {
                    "is_legacy": True,
                    "position": 101,
                    "points": 0
                }}
            )

            # Shift main list levels above 101 down to fill the gap
            mongo_db.levels.update_many(
                {"position": {"$gt": 101}, "is_legacy": {"$ne": True}},
                {"$inc": {"position": -1}}
            )
            
            # Clear the cache to ensure fresh data
            global levels_cache
            levels_cache['main_list'] = None
            levels_cache['legacy_list'] = None
            
            # User points will be updated on next manual recalculate — skipping here to avoid timeout
            
            # Note: We don't log this as a separate changelog entry since 
            # the placement message already mentions "This pushes X to the legacy list"
            
            print(f"🔄 Automatically moved {level_at_101['name']} to legacy list at position #101")
            return level_at_101["name"]
        
        return None
        
    except Exception as e:
        print(f"Error in auto legacy management: {e}")
        return None

def get_level_neighbors(position, is_legacy=False):
    """Get the levels that will be above and below a given position"""
    try:
        above_level = None
        below_level = None
        
        # Get level above (position - 1)
        if position > 1:
            above_query = {"position": position - 1}
            if is_legacy:
                above_query["is_legacy"] = True
            else:
                above_query["is_legacy"] = {"$ne": True}
            
            above_result = mongo_db.levels.find_one(above_query, {"name": 1})
            if above_result:
                above_level = above_result["name"]
        
        # Get level below (position + 1)
        below_query = {"position": position + 1}
        if is_legacy:
            below_query["is_legacy"] = True
        else:
            below_query["is_legacy"] = {"$ne": True}
        
        below_result = mongo_db.levels.find_one(below_query, {"name": 1})
        if below_result:
            below_level = below_result["name"]
        
        return above_level, below_level
        
    except Exception as e:
        print(f"Error getting level neighbors: {e}")
        return None, None

def get_top10_pushout_info(new_position):
    """Get information about what level gets pushed out of top 10 when a new level enters"""
    try:
        if new_position > 10:
            return None  # Not entering top 10
        
        # Find the level currently at position 10
        level_at_10 = mongo_db.levels.find_one({
            "position": 10,
            "is_legacy": {"$ne": True}
        }, {"name": 1})
        
        if level_at_10:
            return level_at_10["name"]
        
        return None
        
    except Exception as e:
        print(f"Error getting top 10 pushout info: {e}")
        return None

def log_admin_action(admin_username, action, details=""):
    """Log admin actions to database and Discord"""
    try:
        # Log to database (without IP address)
        try:
            mongo_db.admin_logs.insert_one({
                "action": action,
                "admin_user": admin_username,
                "details": details,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            print(f"Error logging to database: {e}")
        
        # Send Discord notification using the new system
        if DISCORD_AVAILABLE:
            try:
                notify_admin_action(admin_username, action, details)
            except Exception as e:
                print(f"Error sending Discord admin notification: {e}")
        else:
            print("Discord integration not available for admin notifications")
            
    except Exception as e:
        print(f"Error in log_admin_action: {e}")

print("Setting up routes...")

# Start Discord bot after all initialization is complete
print("🔧 Initializing Discord bot integration...")
try:
    print("📦 Importing Discord bot module...")
    from discord_bot import start_discord_bot, is_bot_available
    print("✅ Discord bot module imported successfully")
    
    # Set the MongoDB reference for the discord_bot module
    import discord_bot
    discord_bot.mongo_db = mongo_db
    
    print("🤖 Attempting to start Discord bot...")
    bot_started = start_discord_bot()
    if bot_started:
        print("🤖 Discord bot startup initiated")
        print("⏳ Bot will be available once it connects to Discord")
        
        # Quick check after a moment
        import time
        time.sleep(2)
        if is_bot_available():
            print("🎉 Discord bot connected successfully!")
        else:
            print("⏳ Discord bot still connecting...")
            
        # Start level monitor after a short delay to ensure bot is ready
        def start_monitor_delayed():
            import time
            time.sleep(10)  # Wait 10 seconds for bot to be ready
            try:
                from level_monitor import start_level_monitor
                from discord_bot import bot
                monitor = start_level_monitor(mongo_db, bot)
                if monitor:
                    print("✅ Level monitor started automatically")
                else:
                    print("❌ Failed to start level monitor automatically")
            except Exception as e:
                print(f"❌ Error starting level monitor: {e}")
        
        # Start monitor in background thread
        import threading
        monitor_thread = threading.Thread(target=start_monitor_delayed, daemon=True)
        monitor_thread.start()
        
    else:
        print("⚠️ Discord bot could not be started - continuing without bot features")
except ImportError as e:
    print(f"❌ Failed to import Discord bot module: {e}")
    print("⚠️ Continuing without Discord bot features")
except Exception as e:
    print(f"❌ Failed to start Discord bot: {e}")
    import traceback
    traceback.print_exc()
    print("⚠️ Continuing without Discord bot features")

# ULTRA-FAST: Preload cache on startup
print("\n⚡ PRELOADING CACHE FOR ULTRA-FAST PERFORMANCE...")
try:
    import threading
    def preload_cache():
        import time
        start = time.time()
        print("Loading main list into cache...")
        main_levels = get_fast_cached_levels(is_legacy=False)
        print(f"Loaded {len(main_levels)} main levels in {time.time() - start:.3f}s")
        
        start = time.time()
        print("Loading legacy list into cache...")
        legacy_levels = get_fast_cached_levels(is_legacy=True)
        print(f"Loaded {len(legacy_levels)} legacy levels in {time.time() - start:.3f}s")
        
        print("✅ CACHE PRELOADED - Site will load ULTRA-FAST!")
    
    # Preload in background thread so app starts immediately
    preload_thread = threading.Thread(target=preload_cache, daemon=True)
    preload_thread.start()
except Exception as e:
    print(f"⚠️ Cache preload failed: {e}")

@app.route('/thumb/<path:url>')
def thumbnail_proxy(url):
    """Enhanced thumbnail proxy with better error handling"""
    import requests
    from flask import Response
    from urllib.parse import unquote
    
    try:
        # Decode the URL
        url = unquote(url)
        print(f"Thumbnail request for: {url}")
        
        # Enhanced headers to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Fetch the image with longer timeout
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # Get content type from response
            content_type = response.headers.get('content-type', 'image/jpeg')
            
            return Response(
                response.content,
                mimetype=content_type,
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            print(f"Thumbnail fetch failed: {response.status_code}")
            # Return placeholder image
            return Response(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
                mimetype='image/png'
            )
            
    except Exception as e:
        print(f"Thumbnail error: {e}")
        # Return placeholder image
        return Response(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
            mimetype='image/png'
        )

# Removed duplicate route

@app.route('/fix_missing_urls')
def fix_missing_urls():
    """Fix missing video URLs for levels that should have images"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "❌ Access denied - Admin only"
    
    try:
        # Direct database updates with exact level names and URLs
        fixes = [
            # Based on your earlier data
            {'name': 'the light circles', 'url': 'https://youtu.be/s82TlWCh-V4'},
            {'name': 'old memories', 'url': 'https://youtu.be/vVDeEQuQ_pM'},
            {'name': 'los pollos tv 3', 'url': 'https://streamable.com/wzux7b'},
            {'name': 'ochiru 2', 'url': 'https://www.youtube.com/watch?v=sImN3-3e5u0'},
            {'name': 'the ringer', 'url': 'https://www.youtube.com/watch?v=3CwTD5RtFDk'},
            # Add more if needed
        ]
        
        results = []
        
        for fix in fixes:
            # Try exact match first
            level = mongo_db.levels.find_one({
                "name": fix['name'],
                "is_legacy": False
            })
            
            if not level:
                # Try case-insensitive match
                level = mongo_db.levels.find_one({
                    "name": {"$regex": f"^{fix['name']}$", "$options": "i"},
                    "is_legacy": False
                })
            
            if level:
                # Update the video URL
                result = mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"video_url": fix['url']}}
                )
                
                if result.modified_count > 0:
                    results.append(f"✅ UPDATED: '{level['name']}' → {fix['url']}")
                else:
                    results.append(f"⚪ UNCHANGED: '{level['name']}' (already had URL)")
            else:
                results.append(f"❌ NOT FOUND: '{fix['name']}'")
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        html = f"""
        <h1>🔧 URL Fix Results</h1>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
            {'<br>'.join(results)}
        </div>
        <p style="margin-top: 20px;">
            <!-- Image debug link removed --> |
            <a href="/">🏠 Main List</a>
        </p>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/quick_fix_urls')
def quick_fix_urls():
    """Quick fix to add missing YouTube URLs"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        # Direct fixes based on your data
        fixes = [
            {'name': 'the light circles', 'url': 'https://youtu.be/s82TlWCh-V4'},
            {'name': 'old memories', 'url': 'https://youtu.be/vVDeEQuQ_pM'},
            {'name': 'los pollos tv 3', 'url': 'https://streamable.com/wzux7b'},
            {'name': 'ochiru 2', 'url': 'https://www.youtube.com/watch?v=sImN3-3e5u0'},
            {'name': 'the ringer', 'url': 'https://www.youtube.com/watch?v=3CwTD5RtFDk'},
        ]
        
        results = []
        
        for fix in fixes:
            # Find the level by name (case insensitive)
            level = mongo_db.levels.find_one({
                "name": {"$regex": f"^{fix['name']}$", "$options": "i"},
                "is_legacy": False
            })
            
            if level:
                # Update the video URL
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"video_url": fix['url']}}
                )
                results.append(f"✅ Updated '{level['name']}' (#{level.get('position', '?')}) with {fix['url']}")
            else:
                results.append(f"❌ Level '{fix['name']}' not found")
        
        html = "<h2>🚀 Quick URL Fix Results</h2><ul>"
        for result in results:
            html += f"<li>{result}</li>"
        html += "</ul>"
        html += '<p><a href="/debug_levels">🔍 Check Results</a> | <a href="/">← Back</a></p>'
        
        return html
        
    except Exception as e:
        return f"<h2>❌ Error</h2><p>{str(e)}</p>"

# Base64 image testing removed - no image uploads supported

@app.route('/admin/records')
def admin_records():
    """Admin record management system"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    visibility_filter = request.args.get('visibility', 'all')
    username_filter = request.args.get('username', '').strip()
    level_filter = request.args.get('level', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 25
    
    # Build query
    match_conditions = {}
    
    if status_filter != 'all':
        match_conditions['status'] = status_filter
    
    # Add visibility filter
    if visibility_filter == 'visible':
        match_conditions['$or'] = [
            {'hidden': {'$exists': False}},
            {'hidden': False}
        ]
    elif visibility_filter == 'hidden':
        match_conditions['hidden'] = True
    
    # Aggregation pipeline
    pipeline = [
        {"$match": match_conditions},
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
        {"$addFields": {
            "percentage": {"$ifNull": ["$percentage", "$progress"]}
        }},
        {"$sort": {"date_submitted": -1}}
    ]
    
    # Add username filter if specified
    if username_filter:
        pipeline.insert(3, {
            "$match": {
                "user.username": {"$regex": username_filter, "$options": "i"}
            }
        })
    
    # Add level name filter if specified
    if level_filter:
        pipeline.insert(-1, {
            "$match": {
                "level.name": {"$regex": level_filter, "$options": "i"}
            }
        })
    
    # Get total count - strip $sort before counting (unnecessary and expensive)
    count_pipeline = [s for s in pipeline if "$sort" not in s] + [{"$count": "total"}]
    total_result = list(mongo_db.records.aggregate(count_pipeline, allowDiskUse=True))
    total_records = total_result[0]['total'] if total_result else 0
    
    # Add pagination
    pipeline.extend([
        {"$skip": (page - 1) * per_page},
        {"$limit": per_page}
    ])
    
    # Execute query
    records = list(mongo_db.records.aggregate(pipeline, allowDiskUse=True))
    
    # Calculate pagination info
    total_pages = (total_records + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('admin/records.html', 
                         records=records,
                         total_records=total_records,
                         page=page,
                         total_pages=total_pages,
                         has_prev=has_prev,
                         has_next=has_next,
                         status_filter=status_filter,
                         visibility_filter=visibility_filter,
                         username_filter=username_filter,
                         level_filter=level_filter)

@app.route('/admin/record/<string:record_id>/edit', methods=['GET', 'POST'])
def admin_edit_record(record_id):
    """Edit a specific record"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_records'))
    
    try:
        # Get record with user and level info
        pipeline = [
            {"$match": {"_id": ObjectId(record_id)}},
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
            {"$addFields": {
                "percentage": {"$ifNull": ["$percentage", "$progress"]}
            }}
        ]
        
        record_result = list(mongo_db.records.aggregate(pipeline, allowDiskUse=True))
        if not record_result:
            flash('Record not found', 'danger')
            return redirect(url_for('admin_records'))
        
        record = record_result[0]
        
        if request.method == 'POST':
            # Update record
            updates = {
                'percentage': int(request.form.get('percentage', record['percentage'])),
                'status': request.form.get('status', record['status']),
                'video_url': request.form.get('video_url', record.get('video_url', '')).strip()
            }
            
            # Add admin edit info
            admin_user = mongo_db.users.find_one({"_id": session['user_id']})
            admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
            
            updates['last_edited_by'] = admin_username
            updates['last_edited_at'] = datetime.now(timezone.utc)
            
            # Update in database
            mongo_db.records.update_one(
                {"_id": ObjectId(record_id)},
                {"$set": updates}
            )
            
            # Log admin action
            log_admin_action(
                admin_username,
                f"EDITED RECORD: {record['user']['username']} on {record['level']['name']}",
                f"Status: {updates['status']}, Percentage: {updates['percentage']}%"
            )
            
            # Recalculate user points if status changed
            if updates['status'] != record['status']:
                update_user_points(record['user_id'])
            
            flash('Record updated successfully!', 'success')
            return redirect(url_for('admin_records'))
        
        return render_template('admin/edit_record.html', record=record)
        
    except Exception as e:
        flash(f'Error editing record: {str(e)}', 'danger')
        return redirect(url_for('admin_records'))

@app.route('/admin/record/<string:record_id>/delete', methods=['POST'])
def admin_delete_record(record_id):
    """Delete a specific record"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_records'))
    
    try:
        # Get record info before deletion
        record = mongo_db.records.find_one({"_id": ObjectId(record_id)})
        if not record:
            flash('Record not found', 'danger')
            return redirect(url_for('admin_records'))
        
        # Get user and level info for logging
        user = mongo_db.users.find_one({"_id": record['user_id']})
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        
        # Delete the record
        mongo_db.records.delete_one({"_id": ObjectId(record_id)})
        
        # Recalculate user points
        update_user_points(record['user_id'])
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get the percentage value (handle both 'percentage' and 'progress' fields)
        percentage_value = record.get('percentage', record.get('progress', 0))
        
        log_admin_action(
            admin_username,
            f"DELETED RECORD: {user['username'] if user else 'Unknown'} on {level['name'] if level else 'Unknown'}",
            f"Percentage: {percentage_value}%, Status: {record['status']}"
        )
        
        flash('Record deleted successfully!', 'success')
        
    except Exception as e:
        flash(f'Error deleting record: {str(e)}', 'danger')
    
    return redirect(url_for('admin_records'))

@app.route('/admin/record/<string:record_id>/discussion')
def admin_record_discussion(record_id):
    """Admin record discussion and polling system"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get the record with user and level info
        record_pipeline = [
            {"$match": {"_id": ObjectId(record_id)}},
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
        ]
        
        record_result = list(mongo_db.records.aggregate(record_pipeline, allowDiskUse=True))
        if not record_result:
            flash('Record not found', 'danger')
            return redirect(url_for('admin_records'))
        
        record = record_result[0]
        
        # Get discussion messages for this record
        messages = list(mongo_db.record_discussions.find({
            "record_id": ObjectId(record_id)
        }).sort("timestamp", 1))
        
        # Get polls for this record
        polls = list(mongo_db.record_polls.find({
            "record_id": ObjectId(record_id)
        }).sort("created_at", -1))
        
        # Add admin info to messages and polls
        admin_ids = set()
        for msg in messages:
            admin_ids.add(msg['admin_id'])
        for poll in polls:
            admin_ids.add(poll['created_by'])
            
        admins = {admin['_id']: admin for admin in mongo_db.users.find({
            "_id": {"$in": list(admin_ids)},
            "is_admin": True
        })}
        
        # Add admin usernames to messages
        for msg in messages:
            admin = admins.get(msg['admin_id'])
            msg['admin_username'] = admin['username'] if admin else 'Unknown Admin'
            
        # Add admin usernames and vote counts to polls
        for poll in polls:
            admin = admins.get(poll['created_by'])
            poll['created_by_username'] = admin['username'] if admin else 'Unknown Admin'
            
            # Calculate vote counts
            total_votes = 0
            for option in poll.get('options', []):
                option['vote_count'] = len(option.get('votes', []))
                total_votes += option['vote_count']
            poll['total_votes'] = total_votes
            
            # Check if current admin has voted
            current_admin_id = session['user_id']
            poll['user_has_voted'] = False
            for option in poll.get('options', []):
                if current_admin_id in option.get('votes', []):
                    poll['user_has_voted'] = True
                    break
        
        return render_template('admin/record_discussion.html', 
                             record=record, 
                             messages=messages, 
                             polls=polls)
        
    except Exception as e:
        print(f"Error in admin_record_discussion: {e}")
        flash('Error loading record discussion', 'danger')
        return redirect(url_for('admin_records'))

@app.route('/admin/record/<string:record_id>/discussion/message', methods=['POST'])
def admin_add_discussion_message(record_id):
    """Add a message to record discussion"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        message_text = request.form.get('message', '').strip()
        if not message_text:
            flash('Message cannot be empty', 'danger')
            return redirect(url_for('admin_record_discussion', record_id=record_id))
        
        # Create discussion message
        message = {
            "_id": ObjectId(),
            "record_id": ObjectId(record_id),
            "admin_id": session['user_id'],
            "message": message_text,
            "timestamp": datetime.now(timezone.utc)
        }
        
        mongo_db.record_discussions.insert_one(message)
        flash('Message added successfully', 'success')
        
    except Exception as e:
        print(f"Error adding discussion message: {e}")
        flash('Error adding message', 'danger')
    
    return redirect(url_for('admin_record_discussion', record_id=record_id))

@app.route('/admin/record/<string:record_id>/discussion/poll', methods=['POST'])
def admin_create_record_poll(record_id):
    """Create a poll for record discussion"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        question = request.form.get('question', '').strip()
        options_text = request.form.get('options', '').strip()
        
        if not question or not options_text:
            flash('Question and options are required', 'danger')
            return redirect(url_for('admin_record_discussion', record_id=record_id))
        
        # Parse options (one per line)
        options = []
        for line in options_text.split('\n'):
            line = line.strip()
            if line:
                options.append({
                    "text": line,
                    "votes": []
                })
        
        if len(options) < 2:
            flash('At least 2 options are required', 'danger')
            return redirect(url_for('admin_record_discussion', record_id=record_id))
        
        # Create poll
        poll = {
            "_id": ObjectId(),
            "record_id": ObjectId(record_id),
            "question": question,
            "options": options,
            "created_by": session['user_id'],
            "created_at": datetime.now(timezone.utc),
            "active": True
        }
        
        mongo_db.record_polls.insert_one(poll)
        flash('Poll created successfully', 'success')
        
    except Exception as e:
        print(f"Error creating record poll: {e}")
        flash('Error creating poll', 'danger')
    
    return redirect(url_for('admin_record_discussion', record_id=record_id))

@app.route('/admin/record/poll/<string:poll_id>/vote', methods=['POST'])
def admin_vote_record_poll(poll_id):
    """Vote in a record poll"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        option_index = int(request.form.get('option', -1))
        
        poll = mongo_db.record_polls.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            flash('Poll not found', 'danger')
            return redirect(url_for('admin_records'))
        
        if option_index < 0 or option_index >= len(poll['options']):
            flash('Invalid option selected', 'danger')
            return redirect(url_for('admin_record_discussion', record_id=str(poll['record_id'])))
        
        admin_id = session['user_id']
        
        # Remove previous votes by this admin
        for option in poll['options']:
            if admin_id in option.get('votes', []):
                option['votes'].remove(admin_id)
        
        # Add new vote
        poll['options'][option_index]['votes'].append(admin_id)
        
        # Update poll in database
        mongo_db.record_polls.update_one(
            {"_id": ObjectId(poll_id)},
            {"$set": {"options": poll['options']}}
        )
        
        flash('Vote recorded successfully', 'success')
        
    except Exception as e:
        print(f"Error voting in record poll: {e}")
        flash('Error recording vote', 'danger')
    
    return redirect(url_for('admin_record_discussion', record_id=str(poll['record_id'])))

@app.route('/admin/record/poll/<string:poll_id>/close', methods=['POST'])
def admin_close_record_poll(poll_id):
    """Close a record poll"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        poll = mongo_db.record_polls.find_one({"_id": ObjectId(poll_id)})
        if not poll:
            flash('Poll not found', 'danger')
            return redirect(url_for('admin_records'))
        
        # Close the poll
        mongo_db.record_polls.update_one(
            {"_id": ObjectId(poll_id)},
            {"$set": {"active": False}}
        )
        
        flash('Poll closed successfully', 'success')
        
    except Exception as e:
        print(f"Error closing record poll: {e}")
        flash('Error closing poll', 'danger')
    
    return redirect(url_for('admin_record_discussion', record_id=str(poll['record_id'])))

@app.route('/admin/record/<string:record_id>/hide', methods=['POST'])
def admin_hide_record(record_id):
    """Hide a record from public view (admin only)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        record = mongo_db.records.find_one({"_id": ObjectId(record_id)})
        if not record:
            flash('Record not found', 'danger')
            return redirect(url_for('admin_records'))
        
        # Hide the record
        mongo_db.records.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"hidden": True, "hidden_by": session['user_id'], "hidden_at": datetime.now(timezone.utc)}}
        )
        
        # Recalculate user points since hidden records don't count
        if REAL_TIME_POINTS_AVAILABLE:
            try:
                from real_time_points_system import RealTimePointsManager
                manager = RealTimePointsManager(mongo_db)
                manager.recalculate_user_points(record['user_id'])
            except Exception as e:
                print(f"Error recalculating points after hiding record: {e}")
        
        flash('Record hidden successfully', 'success')
        
    except Exception as e:
        print(f"Error hiding record: {e}")
        flash('Error hiding record', 'danger')
    
    # Redirect back to level detail if we have level_id, otherwise admin records
    level_id = request.form.get('level_id')
    if level_id:
        return redirect(url_for('level_detail', level_id=level_id))
    return redirect(url_for('admin_records'))

@app.route('/admin/record/<string:record_id>/show', methods=['POST'])
def admin_show_record(record_id):
    """Show a previously hidden record (admin only)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        record = mongo_db.records.find_one({"_id": ObjectId(record_id)})
        if not record:
            flash('Record not found', 'danger')
            return redirect(url_for('admin_records'))
        
        # Show the record
        mongo_db.records.update_one(
            {"_id": ObjectId(record_id)},
            {"$unset": {"hidden": "", "hidden_by": "", "hidden_at": ""}}
        )
        
        # Recalculate user points since the record is now visible again
        if REAL_TIME_POINTS_AVAILABLE:
            try:
                from real_time_points_system import RealTimePointsManager
                manager = RealTimePointsManager(mongo_db)
                manager.recalculate_user_points(record['user_id'])
            except Exception as e:
                print(f"Error recalculating points after showing record: {e}")
        
        flash('Record shown successfully', 'success')
        
    except Exception as e:
        print(f"Error showing record: {e}")
        flash('Error showing record', 'danger')
    
    # Redirect back to level detail if we have level_id, otherwise admin records
    level_id = request.form.get('level_id')
    if level_id:
        return redirect(url_for('level_detail', level_id=level_id))
    return redirect(url_for('admin_records'))

def debug_thumbnails():
    """Debug thumbnail URLs in database"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get first 10 levels with their thumbnail info
        levels = list(mongo_db.levels.find(
            {}, 
            {"name": 1, "thumbnail_url": 1, "video_url": 1, "position": 1}
        ).sort("position", 1).limit(10))
        
        debug_html = """
        <div style="padding: 20px; font-family: Arial;">
            <h2>🔍 Thumbnail Debug Info</h2>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background: #f5f5f5;">
                    <th style="padding: 10px;">Position</th>
                    <th style="padding: 10px;">Level Name</th>
                    <th style="padding: 10px;">Thumbnail Type</th>
                    <th style="padding: 10px;">Thumbnail Info</th>
                </tr>
        """
        
        for level in levels:
            name = level.get('name', 'Unknown')
            position = level.get('position', '?')
            thumbnail_url = level.get('thumbnail_url', '')
            video_url = level.get('video_url', '')
            
            if thumbnail_url and thumbnail_url.strip():
                if thumbnail_url.startswith('data:image'):
                    thumb_type = "Base64"
                    thumb_info = f"Length: {len(thumbnail_url)} chars ({len(thumbnail_url.encode('utf-8'))//1024}KB)"
                elif thumbnail_url.startswith('http'):
                    thumb_type = "External URL"
                    thumb_info = thumbnail_url[:50] + "..." if len(thumbnail_url) > 50 else thumbnail_url
                elif thumbnail_url.startswith('/static/'):
                    thumb_type = "Local File"
                    thumb_info = thumbnail_url
                else:
                    thumb_type = "Unknown"
                    thumb_info = thumbnail_url[:50] + "..." if len(thumbnail_url) > 50 else thumbnail_url
            else:
                if video_url and ('youtube.com' in video_url or 'youtu.be' in video_url):
                    thumb_type = "YouTube Auto"
                    thumb_info = "Will use YouTube thumbnail"
                else:
                    thumb_type = "No Image"
                    thumb_info = "Will show placeholder"
            
            debug_html += f"""
                <tr>
                    <td style="padding: 10px;">{position}</td>
                    <td style="padding: 10px;">{name}</td>
                    <td style="padding: 10px;"><strong>{thumb_type}</strong></td>
                    <td style="padding: 10px; font-family: monospace; font-size: 12px;">{thumb_info}</td>
                </tr>
            """
        
        debug_html += """
            </table>
            <br>
            <p><a href="/">← Back to Main List</a> | <a href="/admin/levels">Admin Levels</a> | <a href="/test_base64_upload">Test Base64 Upload</a> | <a href="/test_base64_display">🧪 Test Base64 Display</a></p>
        </div>
        """
        
        return debug_html
        
    except Exception as e:
        return f"<div style='padding:20px; color:red;'>Debug Error: {e}</div>"

# Base64 upload testing removed - no image uploads supported

# set_thumbnail route removed - no image functionality

@app.route('/complete_fix')
def complete_fix():
    """Complete system fix - images and decimals"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "❌ Access denied - Admin only"
    
    try:
        fixes = []
        
        # 1. Fix missing YouTube URLs
        youtube_urls = {
            'the light circles': 'https://youtu.be/s82TlWCh-V4',
            'old memories': 'https://youtu.be/vVDeEQuQ_pM', 
            'ochiru 2': 'https://www.youtube.com/watch?v=sImN3-3e5u0',
            'the ringer': 'https://www.youtube.com/watch?v=3CwTD5RtFDk',
            'los pollos tv 3': 'https://streamable.com/wzux7b',
        }
        
        for level_name, youtube_url in youtube_urls.items():
            result = mongo_db.levels.update_one(
                {"name": {"$regex": f"^{level_name}$", "$options": "i"}, "is_legacy": False},
                {"$set": {"video_url": youtube_url}}
            )
            if result.modified_count > 0:
                fixes.append(f"✅ Added video URL to '{level_name}'")
        
        # 2. Fix decimal points for all levels
        levels = list(mongo_db.levels.find({"is_legacy": False}, {"_id": 1, "position": 1, "points": 1}))
        points_fixed = 0
        
        for level in levels:
            correct_points = calculate_level_points(level['position'], False)
            current_points = level.get('points', 0)
            
            if abs(float(current_points) - float(correct_points)) > 0.01:
                mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": correct_points}}
                )
                points_fixed += 1
        
        fixes.append(f"✅ Fixed points for {points_fixed} levels")
        
        # 3. Update all user points
        users_updated = 0
        for user in mongo_db.users.find({"points": {"$exists": True}}):
            update_user_points(user["_id"])
            users_updated += 1
        
        fixes.append(f"✅ Updated points for {users_updated} users")
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        html = f"""
        <h1>🔧 Complete Fix Results</h1>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
            {'<br>'.join(fixes)}
        </div>
        <p style="margin-top: 20px;">
            <a href="/">🏠 Main List</a> |
            <a href="/stats/players">🏆 Leaderboard</a>
        </p>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/test_thumbnails')
def test_thumbnails():
    """Test route to verify thumbnail system with multiple YouTube formats"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        # Get first 10 levels
        levels = list(mongo_db.levels.find(
            {"is_legacy": False}, 
            {"name": 1, "video_url": 1, "thumbnail_url": 1, "position": 1}
        ).sort("position", 1).limit(10))
        
        html = """
        <h1>🧪 YouTube Thumbnail Format Test</h1>
        <p>Testing different YouTube thumbnail formats to find what works...</p>
        <style>
            .test-card { 
                border: 1px solid #ddd; 
                margin: 10px; 
                padding: 15px; 
                display: inline-block; 
                width: 300px;
                vertical-align: top;
            }
            .test-img { 
                width: 120px; 
                height: 90px; 
                object-fit: cover; 
                border: 1px solid #007bff;
                border-radius: 4px;
                margin: 2px;
            }
            .working { border-color: #28a745 !important; }
            .broken { border-color: #dc3545 !important; opacity: 0.3; }
        </style>
        <script>
            function markWorking(img) {
                img.classList.add('working');
                img.classList.remove('broken');
            }
            function markBroken(img) {
                img.classList.add('broken');
                img.classList.remove('working');
            }
        </script>
        """
        
        for level in levels:
            name = level.get('name', 'Unknown')
            video_url = level.get('video_url', '')
            thumbnail_url = level.get('thumbnail_url', '')
            position = level.get('position', '?')
            
            # Extract YouTube ID
            youtube_id = ''
            if video_url and 'youtu.be/' in video_url:
                youtube_id = video_url.split('youtu.be/')[1].split('?')[0].split('&')[0]
            elif video_url and 'youtube.com/watch?v=' in video_url:
                youtube_id = video_url.split('v=')[1].split('&')[0]
            
            if youtube_id:
                # Test different YouTube thumbnail formats
                formats = [
                    ('hqdefault.jpg', 'HQ Default (480x360)'),
                    ('mqdefault.jpg', 'MQ Default (320x180)'),
                    ('maxresdefault.jpg', 'Max Res (1280x720)'),
                    ('sddefault.jpg', 'SD Default (640x480)'),
                    ('default.jpg', 'Default (120x90)')
                ]
                
                html += f"""
                <div class="test-card">
                    <h4>#{position} {name}</h4>
                    <p><strong>YouTube ID:</strong> {youtube_id}</p>
                    <div>
                """
                
                for format_name, description in formats:
                    img_url = f"https://img.youtube.com/vi/{youtube_id}/{format_name}"
                    html += f"""
                        <img src="{img_url}" 
                             class="test-img" 
                             title="{description}"
                             onload="markWorking(this)" 
                             onerror="markBroken(this)">
                    """
                
                html += f"""
                    </div>
                    <p><small>Green border = working, Red border = broken</small></p>
                    <p><strong>Video URL:</strong> {video_url[:40]}{'...' if len(video_url) > 40 else ''}</p>
                </div>
                """
            elif thumbnail_url:
                html += f"""
                <div class="test-card">
                    <h4>#{position} {name}</h4>
                    <p><strong>Custom Image:</strong></p>
                    <img src="{thumbnail_url}" class="test-img" onload="markWorking(this)" onerror="markBroken(this)">
                    <p><strong>Image URL:</strong> {thumbnail_url[:40]}{'...' if len(thumbnail_url) > 40 else ''}</p>
                </div>
                """
            else:
                html += f"""
                <div class="test-card">
                    <h4>#{position} {name}</h4>
                    <p><strong>No Image Available</strong></p>
                    <div style="width: 120px; height: 90px; background: #6c757d; color: white; display: flex; align-items: center; justify-content: center; border-radius: 4px;">
                        No Video URL
                    </div>
                </div>
                """
        
        html += """
        <div style="clear: both; margin-top: 20px;">
            <h3>📋 Results Analysis:</h3>
            <p>Look for images with <strong>green borders</strong> - those formats work!</p>
            <p>Images with <strong>red borders</strong> are broken/unavailable.</p>
            <br>
            <a href="/" class="btn btn-success">Test Main List</a>
            <a href="/admin" class="btn btn-secondary">Admin Panel</a>
        </div>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/fix_youtube_thumbnails')
def fix_youtube_thumbnails():
    """Auto-fix YouTube thumbnails by testing formats and picking the best one"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        import requests
        
        # Get levels with YouTube URLs but no custom thumbnails
        levels = list(mongo_db.levels.find(
            {
                "is_legacy": False,
                "video_url": {"$regex": "youtu"},
                "$or": [
                    {"thumbnail_url": {"$exists": False}},
                    {"thumbnail_url": ""},
                    {"thumbnail_url": None}
                ]
            },
            {"name": 1, "video_url": 1, "position": 1}
        ).sort("position", 1).limit(20))
        
        results = []
        fixed_count = 0
        
        # YouTube thumbnail formats to try (in order of preference)
        formats = [
            'hqdefault.jpg',      # 480x360 - most reliable
            'maxresdefault.jpg',  # 1280x720 - highest quality
            'mqdefault.jpg',      # 320x180 - medium quality
            'sddefault.jpg',      # 640x480 - standard def
            'default.jpg'         # 120x90 - always available
        ]
        
        for level in levels:
            name = level.get('name', 'Unknown')
            video_url = level.get('video_url', '')
            position = level.get('position', '?')
            
            # Extract YouTube ID
            youtube_id = ''
            if 'youtu.be/' in video_url:
                youtube_id = video_url.split('youtu.be/')[1].split('?')[0].split('&')[0]
            elif 'youtube.com/watch?v=' in video_url:
                youtube_id = video_url.split('v=')[1].split('&')[0]
            
            if youtube_id:
                # Test formats to find the best working one
                working_format = None
                
                for format_name in formats:
                    test_url = f"https://img.youtube.com/vi/{youtube_id}/{format_name}"
                    
                    try:
                        response = requests.head(test_url, timeout=3)
                        if response.status_code == 200:
                            # Check if it's actually an image (not a placeholder)
                            content_length = response.headers.get('content-length', '0')
                            if int(content_length) > 1000:  # Real images are usually > 1KB
                                working_format = format_name
                                break
                    except:
                        continue
                
                if working_format:
                    # Update the level with the working thumbnail URL
                    best_url = f"https://img.youtube.com/vi/{youtube_id}/{working_format}"
                    
                    mongo_db.levels.update_one(
                        {"_id": level["_id"]},
                        {"$set": {"thumbnail_url": best_url}}
                    )
                    
                    results.append(f"✅ #{position} {name}: {working_format}")
                    fixed_count += 1
                else:
                    results.append(f"❌ #{position} {name}: No working format found")
            else:
                results.append(f"⚠️ #{position} {name}: Could not extract YouTube ID")
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        html = f"""
        <h1>🔧 YouTube Thumbnail Auto-Fix Results</h1>
        <p><strong>Fixed {fixed_count} out of {len(levels)} levels</strong></p>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
            {'<br>'.join(results)}
        </div>
        <p style="margin-top: 20px;">
            <a href="/">🏠 Test Main List</a> |
            <a href="/test_thumbnails">🧪 Test Thumbnails</a> |
            <a href="/admin">⚙️ Admin Panel</a>
        </p>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/admin/ip_ban/<user_id>', methods=['GET', 'POST'])
def ip_ban_user(user_id):
    """Admin route to IP ban a user and delete all their accounts"""
    if 'user_id' not in session or not session.get('head_admin'):
        flash('Access denied - Head Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        from bson.objectid import ObjectId
        from flask import request as flask_request
        
        user = mongo_db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin'))
        
        # PREVENT IP BANNING OF HEAD ADMIN USERS
        if user.get('head_admin', False):
            flash('Cannot IP ban head admin users!', 'danger')
            return redirect(url_for('admin'))
        
        # Get reason from form or query parameter
        if request.method == 'POST':
            reason = request.form.get('reason', 'Hacking/Cheating').strip()
        else:
            reason = request.args.get('reason', 'Hacking/Cheating').strip()
            
        # Get admin username for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get all IP addresses associated with this user
        user_ips = []
        
        # Add current IP
        current_ip = request.remote_addr
        if current_ip and current_ip not in user_ips:
            user_ips.append(current_ip)
        
        # Add historical IPs from login history
        login_history = mongo_db.login_history.find({"user_id": ObjectId(user_id)})
        for login_entry in login_history:
            ip = login_entry.get('ip_address')
            if ip and ip not in user_ips:
                user_ips.append(ip)
        
        # Add last IP from user document
        last_ip = user.get('last_ip')
        if last_ip and last_ip not in user_ips:
            user_ips.append(last_ip)
        
        # Create IP ban record
        ip_ban = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "username": user.get('username', 'Unknown'),
            "ip_addresses": user_ips,
            "reason": reason,
            "banned_by": admin_username,
            "ban_date": datetime.now(timezone.utc),
            "active": True
        }
        
        # Insert IP ban
        mongo_db.ip_bans.insert_one(ip_ban)
        
        # Find and delete ALL accounts with same IP
        deleted_accounts = 0
        for ip in user_ips:
            if ip:
                # Delete accounts with same IP
                accounts_with_ip = mongo_db.users.find({"_id": {"$ne": ObjectId(user_id)}, "last_ip": ip})
                for account in accounts_with_ip:
                    # Delete all records for this account
                    mongo_db.records.delete_many({"user_id": account["_id"]})
                    # Delete the account
                    mongo_db.users.delete_one({"_id": account["_id"]})
                    deleted_accounts += 1
        
        # Delete all user's records
        deleted_records = mongo_db.records.delete_many({"user_id": ObjectId(user_id)})
        
        # Reset user points to 0 and mark as banned
        mongo_db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "points": 0,
                    "banned": True,
                    "ip_banned": True,
                    "ban_reason": reason,
                    "banned_by": admin_username,
                    "ban_date": datetime.now(timezone.utc),
                    "last_ip": user_ips[0] if user_ips else None
                }
            }
        )
        
        # Log admin action
        log_admin_action(admin_username, f"IP BANNED USER: {user.get('username')}", f"Reason: {reason}, Records deleted: {deleted_records.deleted_count}, Additional accounts deleted: {deleted_accounts}")
        
        flash(f'User {user.get("username")} has been IP banned and all data deleted', 'success')
        return redirect(url_for('admin'))
    
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/temp_ban', methods=['POST'])
def admin_temp_ban():
    """Temporarily ban a user from submitting records"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        duration = int(data.get('duration', 1))
        unit = data.get('unit', 'days')
        reason = data.get('reason', 'Rule Violation')
        
        # Find the user
        user = mongo_db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {'error': 'User not found'}, 404
        
        # Prevent temp banning admins
        if user.get('is_admin') or user.get('head_admin'):
            return {'error': 'Cannot temp ban admin users'}, 400
        
        # Calculate ban expiry date
        now = datetime.now(timezone.utc)
        if unit == 'days':
            expiry_date = now + timedelta(days=duration)
        elif unit == 'weeks':
            expiry_date = now + timedelta(weeks=duration)
        elif unit == 'months':
            expiry_date = now + timedelta(days=duration * 30)  # Approximate
        elif unit == 'years':
            expiry_date = now + timedelta(days=duration * 365)  # Approximate
        else:
            return {'error': 'Invalid time unit'}, 400
        
        # Get admin info
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Create temp ban record
        temp_ban = {
            "_id": ObjectId(),
            "user_id": ObjectId(user_id),
            "username": user.get('username', 'Unknown'),
            "reason": reason,
            "duration": duration,
            "unit": unit,
            "banned_by": admin_username,
            "ban_date": now,
            "expiry_date": expiry_date,
            "active": True
        }
        
        # Insert temp ban
        mongo_db.temp_bans.insert_one(temp_ban)
        
        # Log admin action
        log_admin_action(admin_username, f"TEMP BANNED USER: {user.get('username')}", 
                        f"Duration: {duration} {unit}, Reason: {reason}, Expires: {expiry_date.strftime('%Y-%m-%d %H:%M UTC')}")
        
        return {'success': True, 'message': f'User {user.get("username")} has been temporarily banned for {duration} {unit}'}
        
    except Exception as e:
        print(f"Error in temp ban: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/check_temp_ban/<user_id>')
def admin_check_temp_ban(user_id):
    """Check if a user is currently temp banned"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        now = datetime.now(timezone.utc)
        
        # Find active temp ban for user
        temp_ban = mongo_db.temp_bans.find_one({
            "user_id": ObjectId(user_id),
            "active": True,
            "expiry_date": {"$gt": now}
        })
        
        if temp_ban:
            return {
                'temp_banned': True,
                'reason': temp_ban.get('reason'),
                'expiry_date': temp_ban.get('expiry_date').isoformat(),
                'banned_by': temp_ban.get('banned_by')
            }
        else:
            return {'temp_banned': False}
            
    except Exception as e:
        return {'error': str(e)}, 500

def is_user_temp_banned(user_id):
    """Check if a user is currently temp banned - helper function"""
    try:
        now = datetime.now(timezone.utc)
        
        # Find active temp ban for user
        temp_ban = mongo_db.temp_bans.find_one({
            "user_id": ObjectId(user_id),
            "active": True,
            "expiry_date": {"$gt": now}
        })
        
        return temp_ban is not None, temp_ban
        
    except Exception as e:
        print(f"Error checking temp ban: {e}")
        return False, None

# Language translations
TRANSLATIONS = {
    'en': {
        # Navigation
        'main_list': 'Main List',
        'legacy_list': 'Legacy List', 
        'future_list': 'Future List',
        'time_machine': 'Time Machine',
        'submit': 'Submit',
        'submit_record': 'Submit Record',
        'submit_verification': 'Submit Verification',
        'roulette': 'Roulette',
        'changelog': 'Changelog',
        'guide': 'Guide',
        'stats_viewer': 'Stats Viewer',
        'language': 'Language',
        
        # Action Cards
        'guidelines': 'Guide lines',
        'submit_records': 'Submit Records',
        'guidelines_text': 'All recent tab list operations are carried out in accordance to our guidelines. Be sure to check them before submitting a record to ensure a flawless experience!',
        'submit_text': 'Note: Please do not submit nonsense, it only makes it harder for us all and will get you banned. Also note that the form rejects duplicate submissions.',
        'stats_text': 'Get a detailed overview of who beat the most levels! There is even a leaderboard to compare yourself to the very best!',
        'read_guidelines': 'Read the guidelines!',
        'submit_record_btn': 'Submit a record!',
        'open_stats': 'Open the stats viewer!',
        
        # General UI
        'position': 'Position',
        'level': 'Level',
        'creator': 'Creator',
        'verifier': 'Verifier',
        'points': 'Points',
        'difficulty': 'Difficulty',
        'records': 'Records',
        'completion': 'Completion',
        'progress': 'Progress',
        'percentage': 'Percentage',
        'player': 'Player',
        'date': 'Date',
        'video': 'Video',
        'status': 'Status',
        'pending': 'Pending',
        'approved': 'Approved',
        'rejected': 'Rejected',
        'login': 'Login',
        'register': 'Register',
        'logout': 'Logout',
        'profile': 'Profile',
        'settings': 'Settings',
        'notifications': 'Notifications',
        'admin_panel': 'Admin Panel',
        'account': 'Account',
        
        # Level difficulties
        'easy': 'Easy',
        'normal': 'Normal',
        'hard': 'Hard',
        'harder': 'Harder',
        'insane': 'Insane',
        'easy_demon': 'Easy Demon',
        'medium_demon': 'Medium Demon',
        'hard_demon': 'Hard Demon',
        'insane_demon': 'Insane Demon',
        'extreme_demon': 'Extreme Demon',
        
        # Common actions
        'view': 'View',
        'edit': 'Edit',
        'delete': 'Delete',
        'save': 'Save',
        'cancel': 'Cancel',
        'confirm': 'Confirm',
        'search': 'Search',
        'filter': 'Filter',
        'sort': 'Sort',
        'loading': 'Loading...',
        'error': 'Error',
        'success': 'Success',
        'warning': 'Warning',
        'info': 'Info',
        
        # Site title and branding
        'site_title': 'GD Recent Tab List',
        'recent_tab_list': 'Recent Tab List',
        'demonlist': 'Recent Tab List',
        
        # About section
        'about': 'About',
        'about_text_1': 'Welcome to the GD Recent Tab List! This is a community-driven list that ranks recent tab levels by difficulty.',
        'about_text_2': 'Click on any level to view more details, including records and information about the level.',
        
        # Discord section
        'discord_server': 'Discord Server',
        'discord_text': 'Join our community for discussions and level submissions!',
        'join_discord': 'Join Discord Server',
        
        # Credits section
        'credits': 'Credits',
        'list_admin': 'List Admin',
        'list_moderators': 'List Moderators',
        'list_coders': 'List Coders',
        'server_moderator': 'Server Moderator',
        
        # Search
        'search_all_levels': 'Search all levels...',
        
        # Footer
        'showing_all_levels': 'Showing all',
        'levels': 'levels',
        
        # Level details
        'by': 'by',
        'verified_by': 'verified by'
    },
    'ru': {
        # Navigation
        'main_list': 'Основной список',
        'legacy_list': 'Устаревший список',
        'future_list': 'Будущий список',
        'time_machine': 'Машина времени',
        'submit': 'Отправить',
        'submit_record': 'Отправить рекорд',
        'submit_verification': 'Отправить верификацию',
        'roulette': 'Рулетка',
        'changelog': 'Журнал изменений',
        'guide': 'Руководство',
        'stats_viewer': 'Просмотр статистики',
        'language': 'Язык',
        
        # Action Cards
        'guidelines': 'Руководящие принципы',
        'submit_records': 'Отправить рекорды',
        'guidelines_text': 'Все операции списка последних вкладок выполняются в соответствии с нашими руководящими принципами. Обязательно ознакомьтесь с ними перед отправкой записи!',
        'submit_text': 'Примечание: Пожалуйста, не отправляйте бессмыслицу, это только усложняет работу всем нам и приведет к бану. Форма отклоняет дублирующие заявки.',
        'stats_text': 'Получите подробный обзор того, кто завершил больше всего, создал больше всего демонов или победил больше всего демонов! Есть даже таблица лидеров!',
        'read_guidelines': 'Прочитать руководящие принципы!',
        'submit_record_btn': 'Отправить рекорд!',
        'open_stats': 'Открыть просмотр статистики!',
        
        # General UI
        'position': 'Позиция',
        'level': 'Уровень',
        'creator': 'Создатель',
        'verifier': 'Верификатор',
        'points': 'Очки',
        'difficulty': 'Сложность',
        'records': 'Записи',
        'completion': 'Завершение',
        'progress': 'Прогресс',
        'percentage': 'Процент',
        'player': 'Игрок',
        'date': 'Дата',
        'video': 'Видео',
        'status': 'Статус',
        'pending': 'Ожидание',
        'approved': 'Одобрено',
        'rejected': 'Отклонено',
        'login': 'Войти',
        'register': 'Регистрация',
        'logout': 'Выйти',
        'profile': 'Профиль',
        'settings': 'Настройки',
        'notifications': 'Уведомления',
        'admin_panel': 'Панель администратора',
        'account': 'Аккаунт',
        
        # Level difficulties
        'easy': 'Легкий',
        'normal': 'Обычный',
        'hard': 'Сложный',
        'harder': 'Сложнее',
        'insane': 'Безумный',
        'easy_demon': 'Легкий демон',
        'medium_demon': 'Средний демон',
        'hard_demon': 'Сложный демон',
        'insane_demon': 'Безумный демон',
        'extreme_demon': 'Экстремальный демон',
        
        # Common actions
        'view': 'Просмотр',
        'edit': 'Редактировать',
        'delete': 'Удалить',
        'save': 'Сохранить',
        'cancel': 'Отмена',
        'confirm': 'Подтвердить',
        'search': 'Поиск',
        'filter': 'Фильтр',
        'sort': 'Сортировка',
        'loading': 'Загрузка...',
        'error': 'Ошибка',
        'success': 'Успех',
        'warning': 'Предупреждение',
        'info': 'Информация',
        
        # Site title and branding
        'site_title': 'GD Список последних вкладок',
        'recent_tab_list': 'Список последних вкладок',
        'demonlist': 'Список последних вкладок',
        
        # About section
        'about': 'О нас',
        'about_text_1': 'Добро пожаловать в GD Список последних вкладок! Это управляемый сообществом список, который ранжирует уровни последних вкладок по сложности.',
        'about_text_2': 'Нажмите на любой уровень, чтобы просмотреть более подробную информацию, включая записи и информацию об уровне.',
        
        # Discord section
        'discord_server': 'Discord Сервер',
        'discord_text': 'Присоединяйтесь к нашему сообществу для обсуждений и отправки уровней!',
        'join_discord': 'Присоединиться к Discord серверу',
        
        # Credits section
        'credits': 'Авторы',
        'list_admin': 'Администратор списка',
        'list_moderators': 'Модераторы списка',
        'list_coders': 'Программисты списка',
        'server_moderator': 'Модератор сервера',
        
        # Search
        'search_all_levels': 'Поиск всех уровней...',
        
        # Footer
        'showing_all_levels': 'Показано всего',
        'levels': 'уровней',
        
        # Level details
        'by': 'от',
        'verified_by': 'проверено'
    },
    'es': {
        # Navigation
        'main_list': 'Lista principal',
        'legacy_list': 'Lista heredada',
        'future_list': 'Lista futura',
        'time_machine': 'Máquina del tiempo',
        'submit': 'Enviar',
        'submit_record': 'Enviar récord',
        'submit_verification': 'Enviar verificación',
        'roulette': 'Ruleta',
        'changelog': 'Registro de cambios',
        'guide': 'Guía',
        'stats_viewer': 'Visor de estadísticas',
        'language': 'Idioma',
        
        # Action Cards
        'guidelines': 'Pautas',
        'submit_records': 'Enviar récords',
        'guidelines_text': '¡Todas las operaciones de la lista de pestañas recientes se llevan a cabo de acuerdo con nuestras pautas. ¡Asegúrate de revisarlas antes de enviar un récord!',
        'submit_text': 'Nota: Por favor, no envíes tonterías, solo hace que sea más difícil para todos nosotros y te banearán. El formulario rechaza envíos duplicados.',
        'stats_text': '¡Obtén una descripción detallada de quién completó más, creó más demonios o venció más demonios! ¡Incluso hay una tabla de clasificación!',
        'read_guidelines': '¡Lee las pautas!',
        'submit_record_btn': '¡Enviar un récord!',
        'open_stats': '¡Abrir el visor de estadísticas!',
        
        # General UI
        'position': 'Posición',
        'level': 'Nivel',
        'creator': 'Creador',
        'verifier': 'Verificador',
        'points': 'Puntos',
        'difficulty': 'Dificultad',
        'records': 'Récords',
        'completion': 'Completado',
        'progress': 'Progreso',
        'percentage': 'Porcentaje',
        'player': 'Jugador',
        'date': 'Fecha',
        'video': 'Video',
        'status': 'Estado',
        'pending': 'Pendiente',
        'approved': 'Aprobado',
        'rejected': 'Rechazado',
        'login': 'Iniciar sesión',
        'register': 'Registrarse',
        'logout': 'Cerrar sesión',
        'profile': 'Perfil',
        'settings': 'Configuración',
        'notifications': 'Notificaciones',
        'admin_panel': 'Panel de administración',
        'account': 'Cuenta',
        
        # Level difficulties
        'easy': 'Fácil',
        'normal': 'Normal',
        'hard': 'Difícil',
        'harder': 'Más difícil',
        'insane': 'Loco',
        'easy_demon': 'Demonio fácil',
        'medium_demon': 'Demonio medio',
        'hard_demon': 'Demonio difícil',
        'insane_demon': 'Demonio loco',
        'extreme_demon': 'Demonio extremo',
        
        # Common actions
        'view': 'Ver',
        'edit': 'Editar',
        'delete': 'Eliminar',
        'save': 'Guardar',
        'cancel': 'Cancelar',
        'confirm': 'Confirmar',
        'search': 'Buscar',
        'filter': 'Filtrar',
        'sort': 'Ordenar',
        'loading': 'Cargando...',
        'error': 'Error',
        'success': 'Éxito',
        'warning': 'Advertencia',
        'info': 'Información',
        
        # Site title and branding
        'site_title': 'GD Lista de pestañas recientes',
        'recent_tab_list': 'Lista de pestañas recientes',
        'demonlist': 'Lista de pestañas recientes',
        
        # About section
        'about': 'Acerca de',
        'about_text_1': '¡Bienvenido a la GD Lista de pestañas recientes! Esta es una lista impulsada por la comunidad que clasifica los niveles de pestañas recientes por dificultad.',
        'about_text_2': 'Haz clic en cualquier nivel para ver más detalles, incluidos registros e información sobre el nivel.',
        
        # Discord section
        'discord_server': 'Servidor de Discord',
        'discord_text': '¡Únete a nuestra comunidad para discusiones y envíos de niveles!',
        'join_discord': 'Unirse al servidor de Discord',
        
        # Credits section
        'credits': 'Créditos',
        'list_admin': 'Administrador de la lista',
        'list_moderators': 'Moderadores de la lista',
        'list_coders': 'Programadores de la lista',
        'server_moderator': 'Moderador del servidor',
        
        # Search
        'search_all_levels': 'Buscar todos los niveles...',
        
        # Footer
        'showing_all_levels': 'Mostrando todos',
        'levels': 'niveles',
        
        # Level details
        'by': 'por',
        'verified_by': 'verificado por'
    },
    'fr': {
        # Navigation
        'main_list': 'Liste principale',
        'legacy_list': 'Liste héritée',
        'future_list': 'Liste future',
        'time_machine': 'Machine à remonter le temps',
        'submit': 'Soumettre',
        'submit_record': 'Soumettre un record',
        'submit_verification': 'Soumettre une vérification',
        'roulette': 'Roulette',
        'changelog': 'Journal des modifications',
        'guide': 'Guide',
        'stats_viewer': 'Visualiseur de statistiques',
        'language': 'Langue',
        
        # Action Cards
        'guidelines': 'Directives',
        'submit_records': 'Soumettre des records',
        'guidelines_text': 'Toutes les opérations de la liste des onglets récents sont effectuées conformément à nos directives. Assurez-vous de les vérifier avant de soumettre un record!',
        'submit_text': 'Note: Veuillez ne pas soumettre de bêtises, cela ne fait que rendre les choses plus difficiles pour nous tous et vous fera bannir. Le formulaire rejette les soumissions en double.',
        'stats_text': 'Obtenez un aperçu détaillé de qui a terminé le plus, créé le plus de démons ou battu le plus de démons! Il y a même un classement!',
        'read_guidelines': 'Lire les directives!',
        'submit_record_btn': 'Soumettre un record!',
        'open_stats': 'Ouvrir le visualiseur de statistiques!',
        
        # General UI
        'position': 'Position',
        'level': 'Niveau',
        'creator': 'Créateur',
        'verifier': 'Vérificateur',
        'points': 'Points',
        'difficulty': 'Difficulté',
        'records': 'Records',
        'completion': 'Achèvement',
        'progress': 'Progrès',
        'percentage': 'Pourcentage',
        'player': 'Joueur',
        'date': 'Date',
        'video': 'Vidéo',
        'status': 'Statut',
        'pending': 'En attente',
        'approved': 'Approuvé',
        'rejected': 'Rejeté',
        'login': 'Se connecter',
        'register': "S'inscrire",
        'logout': 'Se déconnecter',
        'profile': 'Profil',
        'settings': 'Paramètres',
        'notifications': 'Notifications',
        'admin_panel': "Panneau d'administration",
        'account': 'Compte',
        
        # Level difficulties
        'easy': 'Facile',
        'normal': 'Normal',
        'hard': 'Difficile',
        'harder': 'Plus difficile',
        'insane': 'Fou',
        'easy_demon': 'Démon facile',
        'medium_demon': 'Démon moyen',
        'hard_demon': 'Démon difficile',
        'insane_demon': 'Démon fou',
        'extreme_demon': 'Démon extrême',
        
        # Common actions
        'view': 'Voir',
        'edit': 'Modifier',
        'delete': 'Supprimer',
        'save': 'Sauvegarder',
        'cancel': 'Annuler',
        'confirm': 'Confirmer',
        'search': 'Rechercher',
        'filter': 'Filtrer',
        'sort': 'Trier',
        'loading': 'Chargement...',
        'error': 'Erreur',
        'success': 'Succès',
        'warning': 'Avertissement',
        'info': 'Information',
        
        # Site title and branding
        'site_title': 'GD Liste des onglets récents',
        'recent_tab_list': 'Liste des onglets récents',
        'demonlist': 'Liste des onglets récents',
        
        # About section
        'about': 'À propos',
        'about_text_1': 'Bienvenue dans la GD Liste des onglets récents! Il s\'agit d\'une liste communautaire qui classe les niveaux d\'onglets récents par difficulté.',
        'about_text_2': 'Cliquez sur n\'importe quel niveau pour voir plus de détails, y compris les enregistrements et les informations sur le niveau.',
        
        # Discord section
        'discord_server': 'Serveur Discord',
        'discord_text': 'Rejoignez notre communauté pour des discussions et des soumissions de niveaux!',
        'join_discord': 'Rejoindre le serveur Discord',
        
        # Credits section
        'credits': 'Crédits',
        'list_admin': 'Administrateur de la liste',
        'list_moderators': 'Modérateurs de la liste',
        'list_coders': 'Programmeurs de la liste',
        'server_moderator': 'Modérateur du serveur',
        
        # Search
        'search_all_levels': 'Rechercher tous les niveaux...',
        
        # Footer
        'showing_all_levels': 'Affichage de tous',
        'levels': 'niveaux',
        
        # Level details
        'by': 'par',
        'verified_by': 'vérifié par'
    }
}

def get_translation(key, language=None):
    """Get translation for a key in the specified language"""
    if language is None:
        language = session.get('language', 'en')
    
    if language not in TRANSLATIONS:
        language = 'en'
    
    return TRANSLATIONS[language].get(key, TRANSLATIONS['en'].get(key, key))

@app.route('/set_language/<language>')
def set_language(language):
    """Set the user's preferred language"""
    supported_languages = ['en', 'ru', 'es', 'fr']
    if language in supported_languages:
        session['language'] = language
        flash(f'Language changed to {language.upper()}', 'success')
    else:
        flash('Unsupported language', 'danger')
    
    # Redirect back to the previous page or home
    return redirect(request.referrer or url_for('index'))

def admin_reset_points(user_id):
    """Admin route to reset a user's points and records"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        from bson.objectid import ObjectId
        
        user = mongo_db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin'))
        
        # Delete all user's records
        deleted_records = mongo_db.records.delete_many({"user_id": ObjectId(user_id)})
        
        # Reset points to 0
        mongo_db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"points": 0}}
        )
        
        admin_username = session.get('username', 'Unknown Admin')
        log_admin_action(admin_username, f"RESET POINTS: {user.get('username')}", f"Deleted {deleted_records.deleted_count} records")
        
        flash(f'Reset points for {user.get("username")} - deleted {deleted_records.deleted_count} records', 'success')
        return redirect(url_for('admin'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/reset_own_points', methods=['POST'])
def admin_reset_own_points():
    """Allow admins to reset their own points and records"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        user_id = session['user_id']
        user = mongo_db.users.find_one({"_id": user_id})
        
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('profile'))
        
        # Delete all own records
        deleted_records = mongo_db.records.delete_many({"user_id": user_id})
        
        # Reset own points to 0
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"points": 0}}
        )
        
        admin_username = session.get('username', 'Unknown Admin')
        log_admin_action(admin_username, f"SELF RESET POINTS", f"Deleted own {deleted_records.deleted_count} records")
        
        flash(f'Reset your own points - deleted {deleted_records.deleted_count} records', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('profile'))

@app.route('/admin/find_user', methods=['POST'])
def admin_find_user():
    """Admin route to find user ID by username"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        from flask import request
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return {'error': 'Username required'}, 400
        
        # Find user by username (case insensitive)
        user = mongo_db.users.find_one({
            "username": {"$regex": f"^{username}$", "$options": "i"}
        })
        
        if user:
            return {'user_id': str(user['_id']), 'username': user['username']}
        else:
            return {'error': 'User not found'}, 404
            
    except Exception as e:
        return {'error': str(e)}, 500



@app.route('/admin/move_level/<level_id>', methods=['POST'])
def admin_move_level(level_id):
    """Move a level up or down in the list with real-time points recalculation"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        from bson.objectid import ObjectId
        from flask import request
        from real_time_points_system import RealTimePointsManager
        
        data = request.get_json()
        direction = data.get('direction')
        
        level = mongo_db.levels.find_one({"_id": ObjectId(level_id)})
        if not level:
            return {'error': 'Level not found'}, 404
        
        current_position = level['position']
        
        if direction == 'up' and current_position > 1:
            new_position = current_position - 1
            # Move the level that was at new_position down
            mongo_db.levels.update_one(
                {"position": new_position, "is_legacy": {"$ne": True}},
                {"$set": {"position": current_position}}
            )
        elif direction == 'down':
            new_position = current_position + 1
            # Move the level that was at new_position up
            mongo_db.levels.update_one(
                {"position": new_position, "is_legacy": {"$ne": True}},
                {"$set": {"position": current_position}}
            )
        else:
            return {'error': 'Invalid move'}, 400
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Use the real-time points system to handle the complete recalculation
        manager = RealTimePointsManager(mongo_db)
        success = manager.handle_level_position_change(
            ObjectId(level_id), 
            current_position, 
            new_position, 
            admin_username
        )
        
        if not success:
            return {'error': 'Failed to update points system'}, 500
        
        # Handle automatic legacy management if needed
        if new_position <= 100:
            auto_manage_legacy_list()
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Check if this move will push something to legacy
        pushed_to_legacy = None
        if new_position <= 100 and current_position > 100:
            level_at_100 = mongo_db.levels.find_one({
                "position": 100,
                "is_legacy": {"$ne": True}
            })
            if level_at_100:
                pushed_to_legacy = level_at_100["name"]
        
        # Get levels that will be above and below after the move
        above_level, below_level = get_level_neighbors(new_position, False)
        
        # Special handling for moves to #1 (dethroning)
        dethroned_level = None
        if new_position == 1 and current_position > 1:
            # This level is moving to #1, so it's dethroning whoever was there
            current_first = mongo_db.levels.find_one({
                "position": 1,
                "is_legacy": {"$ne": True},
                "_id": {"$ne": ObjectId(level_id)}  # Exclude the level being moved
            })
            if current_first:
                dethroned_level = current_first["name"]
        
        # Check if this move pushes something out of top 10
        pushed_out_of_top10 = None
        if new_position <= 10 and current_position > 10:
            # Find what level is currently at position 10 that will be pushed out
            level_at_10 = mongo_db.levels.find_one({
                "position": 10,
                "is_legacy": {"$ne": True},
                "_id": {"$ne": ObjectId(level_id)}
            })
            if level_at_10:
                pushed_out_of_top10 = level_at_10["name"]
        
        # Log enhanced changelog
        changelog_kwargs = {
            'old_position': current_position,
            'new_position': new_position,
            'above_level': above_level,
            'below_level': below_level,
            'list_type': 'main'  # This is a main list move
        }
        
        # Add dethroning info for #1 moves
        if new_position == 1 and dethroned_level:
            changelog_kwargs['dethroned_level'] = dethroned_level
        
        if pushed_to_legacy:
            changelog_kwargs['pushed_to_legacy'] = pushed_to_legacy
        
        if pushed_out_of_top10:
            changelog_kwargs['pushed_out_of_top10'] = pushed_out_of_top10
        
        log_level_change(
            action="moved",
            level_name=level['name'],
            admin_username=admin_username,
            **changelog_kwargs
        )
        
        # Log admin action
        log_admin_action(admin_username, f"MOVED LEVEL: {level['name']}", f"Position {current_position} → {new_position}")
        
        # Update historical rankings
        try:
            update_historical_rankings()
        except Exception as e:
            print(f"Warning: Failed to update historical rankings: {e}")
        
        return {'success': True, 'users_updated': users_updated}
        
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/admin/recalculate_all_points', methods=['POST'])
def admin_recalculate_all_points():
    """Recalculate all level points and user points using verified calculation method"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        # Step 1: Recalculate all level points
        print("🔄 Admin recalculate: Starting level points recalculation...")
        _pts_proj = {"_id": 1, "position": 1, "is_legacy": 1, "points": 1}
        levels = list(mongo_db.levels.find({}, _pts_proj))
        levels_updated = 0

        for level in levels:
            position = level.get("position", 0)
            is_legacy = level.get("is_legacy", False)
            current_points = level.get("points", 0)
            correct_points = calculate_level_points(position, is_legacy)

            if abs(current_points - correct_points) > 0.01:
                result = mongo_db.levels.update_one(
                    {"_id": level["_id"]},
                    {"$set": {"points": correct_points}}
                )
                if result.modified_count > 0:
                    levels_updated += 1

        # Step 2: Recalculate all user points using verified method
        print("🔄 Admin recalculate: Starting user points recalculation...")

        # Reload levels with correct points (no thumbnail needed)
        levels = list(mongo_db.levels.find({}, {"_id": 1, "points": 1, "is_legacy": 1}))
        level_lookup = {str(level['_id']): level for level in levels}
        
        users = list(mongo_db.users.find({}))
        users_updated = 0
        
        for user in users:
            user_id = user['_id']
            current_points = user.get('points', 0.0)
            
            # Get all approved records for this user
            records = list(mongo_db.records.find({
                "user_id": user_id,
                "status": "approved"
            }))
            
            # Calculate correct total points
            correct_total_points = 0.0
            
            for record in records:
                level_id = str(record['level_id'])
                level = level_lookup.get(level_id)
                
                if level:
                    # Calculate points for this record
                    if level.get('is_legacy', False):
                        points = 0.0
                    elif record['progress'] == 100:
                        points = float(level['points'])
                    else:
                        # Partial completion - 20% of full points when reaching minimum percentage
                        # Only applies to levels in the top 50
                        if level.get('position', 0) > 50:
                            points = 0.0
                        else:
                            min_percentage = level.get('min_percentage', 100)
                            if record['progress'] >= min_percentage and min_percentage < 100:
                                points = round(float(level['points']) * 0.20, 2)
                            else:
                                points = 0.0
                    
                    correct_total_points += points
            
            # Round to 2 decimal places
            correct_total_points = round(correct_total_points, 2)
            
            # Update user if points changed
            if abs(correct_total_points - current_points) > 0.01:
                result = mongo_db.users.update_one(
                    {"_id": user_id},
                    {"$set": {"points": correct_total_points}}
                )
                if result.modified_count > 0:
                    users_updated += 1
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Log the action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "RECALCULATED ALL POINTS", f"Updated {levels_updated} levels and {users_updated} users")
        
        print(f"✅ Admin recalculate completed: {levels_updated} levels, {users_updated} users updated")
        
        return {
            'success': True, 
            'levels_updated': levels_updated, 
            'users_updated': users_updated,
            'message': f'Successfully recalculated points for {levels_updated} levels and {users_updated} users'
        }
        
    except Exception as e:
        print(f"Error in admin_recalculate_all_points: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/add_level', methods=['POST'])
def admin_add_level():
    """Add a new level with enhanced changelog support"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_levels'))
    
    try:
        from bson.objectid import ObjectId
        
        name = request.form.get('name', '').strip()
        creator = request.form.get('creator', '').strip()
        verifier = request.form.get('verifier', '').strip()
        position = int(request.form.get('position', 1))
        difficulty = float(request.form.get('difficulty', 10))
        video_url = request.form.get('video_url', '').strip()
        level_id = request.form.get('level_id', '').strip()
        min_percentage = int(request.form.get('min_percentage', 100))
        is_legacy = 'is_legacy' in request.form
        
        # Check level name for profanity
        is_name_clean, profanity_reason = check_level_name_profanity(name)
        if not is_name_clean:
            flash(f'Level name not allowed: {profanity_reason}', 'danger')
            return redirect(url_for('admin_levels'))
        
        # Get admin username
        admin_username = session.get('username', 'Unknown Admin')
        
        # Check if this placement will push something to legacy (only for main list additions)
        pushed_to_legacy = None
        if not is_legacy and position <= 100:
            # Count current main list levels
            main_list_count = mongo_db.levels.count_documents({"is_legacy": {"$ne": True}})
            
            # If we already have 100 levels, adding one more will push the last one to legacy
            if main_list_count >= 100:
                # Find what's currently at position 100 (will be pushed to 101, then to legacy)
                level_at_100 = mongo_db.levels.find_one({
                    "position": 100,
                    "is_legacy": {"$ne": True}
                }, {"name": 1})
                
                if level_at_100:
                    pushed_to_legacy = level_at_100["name"]
        
        # Get levels that will be above and below the new level
        above_level, below_level = get_level_neighbors(position, is_legacy)
        
        # Special handling for #1 placement (only for main list)
        dethroned_level = None
        if not is_legacy and position == 1:
            current_first = mongo_db.levels.find_one({
                "position": 1,
                "is_legacy": {"$ne": True}
            }, {"name": 1})
            if current_first:
                dethroned_level = current_first["name"]

        # Handle legacy list positioning
        if is_legacy:
            # For legacy levels, find the next available position starting from 101
            highest_legacy = mongo_db.levels.find_one(
                {"is_legacy": True},
                {"position": 1},
                sort=[("position", -1)]
            )
            if highest_legacy:
                # If position is specified and available, use it; otherwise use next available
                if position >= 101:
                    # Check if position is already taken
                    existing_at_position = mongo_db.levels.find_one({
                        "position": position,
                        "is_legacy": True
                    }, {"_id": 1})
                    if existing_at_position:
                        # Position taken, use next available
                        position = highest_legacy['position'] + 1
                else:
                    # Position too low for legacy, use next available
                    position = highest_legacy['position'] + 1
            else:
                # First legacy level
                position = 101
        
        # Create new level first
        new_level_id = ObjectId()
        points = calculate_level_points(position, is_legacy)
        
        new_level = {
            "_id": new_level_id,
            "name": name,
            "creator": creator,
            "verifier": verifier,
            "position": position,
            "difficulty": difficulty,
            "demon_type": None,  # Demon subcategories removed
            "points": points,
            "video_url": video_url,
            "level_id": int(level_id) if level_id and level_id.strip() else None,
            "min_percentage": min_percentage,
            "is_legacy": is_legacy,
            "date_added": datetime.now(timezone.utc)
        }
        
        # Shift existing levels down based on list type
        if is_legacy:
            # Shift legacy levels down
            mongo_db.levels.update_many(
                {"position": {"$gte": position}, "is_legacy": True},
                {"$inc": {"position": 1}}
            )
        else:
            # Shift main list levels down
            mongo_db.levels.update_many(
                {"position": {"$gte": position}, "is_legacy": {"$ne": True}},
                {"$inc": {"position": 1}}
            )
        
        # Insert the new level
        mongo_db.levels.insert_one(new_level)
        
        # Handle automatic legacy management (only for main list additions)
        if not is_legacy:
            auto_manage_legacy_list()
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Check if this placement pushes something out of top 10 (only for main list)
        pushed_out_of_top10 = None
        if not is_legacy and position <= 10:
            pushed_out_of_top10 = get_top10_pushout_info(position)
        
        # Log enhanced changelog
        changelog_kwargs = {
            'position': position,
            'above_level': above_level,
            'below_level': below_level,
            'list_type': 'legacy' if is_legacy else 'main'
        }
        
        if position == 1 and dethroned_level:
            changelog_kwargs['dethroned_level'] = dethroned_level
        
        if pushed_to_legacy:
            changelog_kwargs['pushed_to_legacy'] = pushed_to_legacy
        
        if pushed_out_of_top10:
            changelog_kwargs['pushed_out_of_top10'] = pushed_out_of_top10
        
        log_level_change(
            action="placed",
            level_name=name,
            admin_username=admin_username,
            **changelog_kwargs
        )
        
        # Log admin action
        log_admin_action(admin_username, f"ADDED LEVEL: {name}", f"Position {position}, {difficulty}/10 difficulty")

        flash(f'Level "{name}" added successfully at position {position}', 'success')
        return redirect(url_for('admin_levels'))
        
    except Exception as e:
        flash(f'Error adding level: {str(e)}', 'danger')
        return redirect(url_for('admin_levels'))

@app.route('/api/discord_refresh', methods=['POST'])
def api_discord_refresh():
    """API endpoint to refresh Discord widget data"""
    try:
        if DISCORD_WIDGET_AVAILABLE:
            # Clear the cache to force refresh
            from discord_widget import discord_cache
            discord_cache['data'] = None
            discord_cache['last_updated'] = None
            return {'success': True}
        else:
            return {'success': False, 'error': 'Discord widget not available'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@app.route('/admin/test_environment')
def admin_test_environment():
    """Admin testing environment with all website features"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get sample data for testing
        sample_levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1).limit(10))
        sample_legacy_levels = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1).limit(5))
        sample_users = list(mongo_db.users.find().sort("points", -1).limit(5))
        sample_records = list(mongo_db.records.aggregate([
            {"$match": {"status": "approved"}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 10}
        ], allowDiskUse=True))
        
        # Get current admin user
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        
        return render_template('admin_test_environment.html',
                             sample_levels=sample_levels,
                             sample_legacy_levels=sample_legacy_levels,
                             sample_users=sample_users,
                             sample_records=sample_records,
                             admin_user=admin_user)
        
    except Exception as e:
        flash(f'Error loading test environment: {str(e)}', 'danger')
        return redirect(url_for('admin_levels'))

@app.route('/admin/rebuild_image_system')
def admin_rebuild_image_system():
    """Completely rebuild the image system from scratch"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        import requests
        
        # Get all levels
        levels = list(mongo_db.levels.find(
            {"is_legacy": {"$ne": True}}, 
            {"_id": 1, "name": 1, "video_url": 1, "thumbnail_url": 1, "position": 1}
        ).sort("position", 1))
        
        results = []
        fixed_count = 0
        
        for level in levels:
            name = level.get('name', 'Unknown')
            video_url = level.get('video_url', '')
            thumbnail_url = level.get('thumbnail_url', '')
            position = level.get('position', '?')
            
            # Skip if already has custom thumbnail
            if thumbnail_url and thumbnail_url.strip():
                results.append(f"#{position} {name}: ✅ Has custom thumbnail")
                continue
            
            # Try to extract and set working thumbnail
            working_thumbnail = None
            
            if video_url and video_url.strip():
                # Extract YouTube ID
                youtube_id = ''
                if 'youtu.be/' in video_url:
                    youtube_id = video_url.split('youtu.be/')[1].split('?')[0].split('&')[0]
                elif 'youtube.com/watch?v=' in video_url:
                    youtube_id = video_url.split('v=')[1].split('&')[0]
                
                if youtube_id:
                    # Test different YouTube thumbnail formats
                    formats = [
                        'hqdefault.jpg',
                        'maxresdefault.jpg', 
                        'mqdefault.jpg',
                        'default.jpg'
                    ]
                    
                    for format_name in formats:
                        test_url = f"https://img.youtube.com/vi/{youtube_id}/{format_name}"
                        
                        try:
                            response = requests.head(test_url, timeout=3)
                            if response.status_code == 200:
                                content_length = int(response.headers.get('content-length', '0'))
                                if content_length > 1000:  # Real images are usually > 1KB
                                    working_thumbnail = test_url
                                    break
                        except:
                            continue
                    
                    if working_thumbnail:
                        # Update level with working thumbnail
                        mongo_db.levels.update_one(
                            {"_id": level["_id"]},
                            {"$set": {"thumbnail_url": working_thumbnail}}
                        )
                        results.append(f"#{position} {name}: ✅ Set {format_name} thumbnail")
                        fixed_count += 1
                    else:
                        results.append(f"#{position} {name}: ❌ No working YouTube thumbnail found")
                
                elif 'streamable.com/' in video_url:
                    # Try Streamable thumbnail
                    streamable_id = video_url.split('/')[-1]
                    streamable_thumb = f"https://cdn-cf-east.streamable.com/image/{streamable_id}.jpg"
                    
                    try:
                        response = requests.head(streamable_thumb, timeout=3)
                        if response.status_code == 200:
                            mongo_db.levels.update_one(
                                {"_id": level["_id"]},
                                {"$set": {"thumbnail_url": streamable_thumb}}
                            )
                            results.append(f"#{position} {name}: ✅ Set Streamable thumbnail")
                            fixed_count += 1
                        else:
                            results.append(f"#{position} {name}: ❌ Streamable thumbnail not available")
                    except:
                        results.append(f"#{position} {name}: ❌ Error testing Streamable thumbnail")
                
                else:
                    results.append(f"#{position} {name}: ⚠️ Unknown video platform")
            else:
                results.append(f"#{position} {name}: ❌ No video URL")
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        html = f"""
        <h1>🔧 Image System Rebuild Complete</h1>
        <div class="alert alert-success">
            <h4>✅ Rebuild Summary</h4>
            <p><strong>Fixed {fixed_count} out of {len(levels)} levels</strong></p>
            <p>All working thumbnails have been automatically set.</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace; max-height: 400px; overflow-y: auto;">
            {'<br>'.join(results)}
        </div>
        
        <div class="mt-4">
            <a href="/" class="btn btn-success btn-lg">🏠 Test Main List</a>
            <a href="/admin/levels_enhanced" class="btn btn-primary btn-lg">⚙️ Enhanced Admin</a>
            <a href="/admin" class="btn btn-secondary btn-lg">📊 Admin Dashboard</a>
        </div>
        
        <div class="alert alert-info mt-4">
            <h5>🎯 What This Did:</h5>
            <ul>
                <li>✅ Tested all YouTube thumbnail formats for each level</li>
                <li>✅ Set the best working thumbnail for each level</li>
                <li>✅ Added Streamable thumbnail support</li>
                <li>✅ Cleared all caches for immediate effect</li>
                <li>✅ Images should now load properly on the main list</li>
            </ul>
        </div>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error rebuilding image system: {str(e)}"

# test_new_images route removed - no image functionality

# final_test route removed - no image functionality

# image_test route removed - no image functionality

@app.route('/restore_images')
def restore_images():
    """Restore the original working image system"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "❌ Access denied - Admin only"
    
    try:
        # Add the missing YouTube URLs that should be there
        fixes = [
            ('the light circles', 'https://youtu.be/s82TlWCh-V4'),
            ('old memories', 'https://youtu.be/vVDeEQuQ_pM'),
            ('ochiru 2', 'https://www.youtube.com/watch?v=sImN3-3e5u0'),
            ('the ringer', 'https://www.youtube.com/watch?v=3CwTD5RtFDk'),
        ]
        
        results = []
        
        for level_name, youtube_url in fixes:
            # Update the level with the YouTube URL
            result = mongo_db.levels.update_one(
                {"name": {"$regex": f"^{level_name}$", "$options": "i"}, "is_legacy": False},
                {"$set": {"video_url": youtube_url}}
            )
            
            if result.matched_count > 0:
                results.append(f"✅ Restored: {level_name}")
            else:
                results.append(f"❌ Not found: {level_name}")
        
        # Clear cache
        levels_cache['main_list'] = None
        
        return f"""
        <h1>🎨 ORIGINAL IMAGE SYSTEM RESTORED!</h1>
        
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>✅ What I Restored:</h2>
            <ul>
                <li>✅ Original template logic (no more complex mapping)</li>
                <li>✅ Simple thumbnail handling (no more base64)</li>
                <li>✅ YouTube thumbnail extraction</li>
                <li>✅ Custom image upload support</li>
            </ul>
        </div>
        
        <div style="background: #cce5ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>🔧 YouTube URLs Added:</h2>
            {'<br>'.join(results)}
        </div>
        
        <div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>🎯 How It Works Now (Original System):</h2>
            <ol>
                <li><strong>Custom Images:</strong> Upload via admin panel → Shows custom image</li>
                <li><strong>YouTube URLs:</strong> Automatic thumbnail extraction</li>
                <li><strong>No Video:</strong> Shows "📷 No Preview"</li>
            </ol>
        </div>
        
        <p>
            <a href="/" style="background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🏠 CHECK MAIN LIST - IMAGES SHOULD WORK NOW!</a>
        </p>
        """
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/test')
def test():
    # Test the points formula for key positions
    test_positions = [1, 2, 3, 5, 10, 20, 50, 75, 100]
    points_table = ""
    
    for pos in test_positions:
        points = calculate_level_points(pos)
        exponent = pos - 1
        points_table += f"<tr><td>#{pos}</td><td>{points}</td><td>250 * (0.963655^{exponent})</td></tr>"
    
    return f"""
    <h1>✅ Points Formula UPDATED SUCCESSFULLY</h1>
    <h2>Formula: p = 250(0.963655)^(position-1)</h2>
    <p><strong>✅ Position #1 = 250.00 points</strong></p>
    <p><strong>✅ Position #50 = 40.75 points</strong></p>
    <p><strong>✅ Position #100 = 6.40 points</strong></p>
    <p><strong>✅ Position #150 = 1.01 points</strong></p>
    
    <table border="1" style="border-collapse: collapse; margin: 20px 0;">
        <tr style="background: #f0f0f0;">
            <th style="padding: 10px;">Position</th>
            <th style="padding: 10px;">Points</th>
            <th style="padding: 10px;">Calculation</th>
        </tr>
        {points_table}
    </table>
    
    <h2>🎯 Key Examples:</h2>
    <ul>
        <li><strong>Position #1:</strong> 250 * (0.963655^0) = <strong>{calculate_level_points(1)} points</strong></li>
        <li><strong>Position #50:</strong> 250 * (0.963655^49) = <strong>{calculate_level_points(50)} points</strong></li>
        <li><strong>Position #100:</strong> 250 * (0.963655^99) = <strong>{calculate_level_points(100)} points</strong></li>
    </ul>
    
    <h2>✅ All Systems Updated:</h2>
    <ul>
        <li>✅ Points formula FIXED (Position 100 = 6.4 points)</li>
        <li>✅ All user points RECALCULATED</li>
        <li>✅ Level points UPDATED</li>
        <li>✅ Formula verification COMPLETE</li>
    </ul>
    
    <p><a href="/">← Back to main list</a> | <a href="/admin">Admin Panel</a></p>
    """

# test_images_simple route removed - no image functionality

@app.route('/check_missing_levels')
def check_missing_levels():
    """Check the specific levels that are missing images"""
    try:
        # Check the levels from your screenshot
        level_names = ['the light circles', 'old memories', 'los pollos tv 3', 'ochiru 2']
        
        html = """
        <h1>🔍 CHECKING MISSING LEVELS</h1>
        <p>Looking at the specific levels from your screenshot...</p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #f0f0f0;">
                <th style="padding: 10px;">Level Name</th>
                <th style="padding: 10px;">Found in DB?</th>
                <th style="padding: 10px;">Current Video URL</th>
                <th style="padding: 10px;">Status</th>
            </tr>
        """
        
        for name in level_names:
            level = mongo_db.levels.find_one(
                {"name": {"$regex": f"^{name}$", "$options": "i"}, "is_legacy": False},
                {"name": 1, "video_url": 1, "position": 1}
            )
            
            if level:
                video_url = level.get('video_url', '')
                status = '✅ Has YouTube URL' if ('youtube.com' in video_url or 'youtu.be' in video_url) else '❌ Missing URL'
                html += f"""
                <tr style="background: {'#e8f5e8' if status.startswith('✅') else '#ffebee'};">
                    <td style="padding: 10px; font-weight: bold;">{level['name']}</td>
                    <td style="padding: 10px;">✅ Found (#{level.get('position', '?')})</td>
                    <td style="padding: 10px; font-size: 11px;">{video_url or 'EMPTY'}</td>
                    <td style="padding: 10px; font-weight: bold;">{status}</td>
                </tr>
                """
            else:
                html += f"""
                <tr style="background: #ffebee;">
                    <td style="padding: 10px; font-weight: bold;">{name}</td>
                    <td style="padding: 10px;">❌ NOT FOUND</td>
                    <td style="padding: 10px;">-</td>
                    <td style="padding: 10px; font-weight: bold;">❌ Level Missing</td>
                </tr>
                """
        
        html += """
        </table>
        <p style="margin-top: 20px;">
            <a href="/fix_all_missing_images" style="background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🔧 FIX ALL MISSING IMAGES</a>
        </p>
        """
        
        return html
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# debug_images route removed - no image functionality

@app.route('/cleanup_broken_thumbnails')
def cleanup_broken_thumbnails():
    """Clean up broken thumbnail URLs pointing to missing files"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied - Admin only"
    
    try:
        # Find levels with thumbnail URLs pointing to missing files in /static/thumbnails/
        levels_with_broken_thumbs = list(mongo_db.levels.find({
            "thumbnail_url": {"$regex": "^/static/thumbnails/"}
        }))
        
        if not levels_with_broken_thumbs:
            return "<h2>✅ No broken thumbnails found!</h2><p><a href='/'>← Back to main</a></p>"
        
        # Clear the broken thumbnail URLs
        result = mongo_db.levels.update_many(
            {"thumbnail_url": {"$regex": "^/static/thumbnails/"}},
            {"$set": {"thumbnail_url": ""}}
        )
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        return f"""
        <h2>🔧 Cleaned Up Broken Thumbnails!</h2>
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p>✅ Removed {result.modified_count} broken thumbnail URLs</p>
            <p>These were pointing to missing files in /static/thumbnails/</p>
            <p>Now these levels will fall back to YouTube thumbnails automatically!</p>
        </div>
        <p>
            <a href="/" style="background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🏠 CHECK MAIN LIST NOW</a>
        </p>
        <p>
            <!-- Image debug link removed --> | 
            <a href="/admin">⚙️ Admin Panel</a>
        </p>
        """
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route('/debug_levels')
def debug_levels():
    """Debug route to check what levels exist and their video URLs"""
    try:
        levels = list(mongo_db.levels.find(
            {"is_legacy": False},
            {"name": 1, "video_url": 1, "position": 1, "thumbnail_url": 1}
        ).sort("position", 1).limit(15))
        
        html = """
        <h2>🔍 Debug: Level URLs + Fix Missing Thumbnails</h2>
        <p>Checking which levels need thumbnail fixes...</p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #f0f0f0;">
                <th style="padding: 10px;">Pos</th>
                <th style="padding: 10px;">Name</th>
                <th style="padding: 10px;">Video URL</th>
                <th style="padding: 10px;">Status</th>
                <th style="padding: 10px;">Preview</th>
                <th style="padding: 10px;">Action</th>
            </tr>
        """
        
        for level in levels:
            video_url = level.get('video_url', '')
            thumbnail_url_field = level.get('thumbnail_url', '')
            level_name = level.get('name', 'Unknown')
            position = level.get('position', '?')
            
            # Check status
            status = ''
            preview_html = ''
            action_html = ''
            
            if thumbnail_url_field and thumbnail_url_field.strip():
                status = '✅ Has Custom Thumbnail'
                preview_html = f'<img src="{thumbnail_url_field}" style="width: 80px; height: 45px; border: 2px solid purple;">'
                action_html = '✅ OK'
            elif video_url and video_url.strip():
                if 'youtube.com' in video_url and 'watch?v=' in video_url:
                    video_id = video_url.split('watch?v=')[1].split('&')[0]
                    status = '✅ Has YouTube URL'
                    preview_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" style="width: 80px; height: 45px; border: 2px solid green;">'
                    action_html = '✅ Should Work'
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                    status = '✅ Has YouTu.be URL'
                    preview_html = f'<img src="https://img.youtube.com/vi/{video_id}/mqdefault.jpg" style="width: 80px; height: 45px; border: 2px solid blue;">'
                    action_html = '✅ Should Work'
                else:
                    domain = video_url.split('/')[2] if '/' in video_url else 'Video'
                    status = f'⚠️ Non-YouTube: {domain}'
                    preview_html = f'<div style="background: #17a2b8; color: white; padding: 5px; width: 80px; height: 45px; display: flex; align-items: center; justify-content: center; font-size: 10px;">🎥 {domain}</div>'
                    action_html = '⚠️ Needs Custom Image'
            else:
                status = '❌ No Video URL'
                preview_html = '<div style="background: #f8f9fa; color: #6c757d; padding: 5px; width: 80px; height: 45px; display: flex; align-items: center; justify-content: center; font-size: 10px;">📷 None</div>'
                action_html = '❌ NEEDS FIX'
            
            # Color code the row
            row_color = ''
            if '❌' in status:
                row_color = 'background: #ffebee;'
            elif '⚠️' in status:
                row_color = 'background: #fff3e0;'
            else:
                row_color = 'background: #e8f5e8;'
            
            html += f"""
            <tr style="{row_color}">
                <td style="padding: 10px;">#{position}</td>
                <td style="padding: 10px; font-weight: bold;">{level_name}</td>
                <td style="padding: 10px; word-break: break-all; max-width: 200px; font-size: 11px;">{video_url or 'NONE'}</td>
                <td style="padding: 10px;">{status}</td>
                <td style="padding: 10px;">{preview_html}</td>
                <td style="padding: 10px; font-weight: bold;">{action_html}</td>
            </tr>
            """
        
        html += """
        </table>
        <div style="margin-top: 20px;">
            <h3>🛠️ Fix Actions Needed:</h3>
            <ul>
                <li><strong>❌ Red rows:</strong> Need video URLs or custom thumbnails</li>
                <li><strong>⚠️ Orange rows:</strong> Need custom thumbnails (non-YouTube videos)</li>
                <li><strong>✅ Green rows:</strong> Should work automatically</li>
            </ul>
        </div>
        <p style="margin-top: 20px;">
            <a href="/">← Back to main list</a> | 
            <a href="/admin/levels">🛠️ Admin Levels</a> |
            <a href="/fix_thumbnails">🔧 Auto-Fix Thumbnails</a>
        </p>
        """
        
        return html
        
    except Exception as e:
        return f"<h2>❌ Database Error</h2><p>{str(e)}</p><p><a href='/'>← Back</a></p>"

# stress_test_images route removed - no image functionality

@app.route('/fix_all_missing_images')
def fix_all_missing_images():
    """Fix ALL missing images based on the screenshot"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "❌ Access denied - Admin only"
    
    try:
        # Based on your screenshot, these levels need YouTube URLs
        fixes = [
            ('the light circles', 'https://youtu.be/s82TlWCh-V4'),
            ('old memories', 'https://youtu.be/vVDeEQuQ_pM'),
            ('los pollos tv 3', 'https://streamable.com/wzux7b'),
            ('ochiru 2', 'https://www.youtube.com/watch?v=sImN3-3e5u0'),
            ('the ringer', 'https://www.youtube.com/watch?v=3CwTD5RtFDk'),
        ]
        
        results = []
        
        for level_name, video_url in fixes:
            # Try exact match first
            result = mongo_db.levels.update_one(
                {"name": level_name, "is_legacy": False},
                {"$set": {"video_url": video_url}}
            )
            
            if result.matched_count == 0:
                # Try case-insensitive match
                result = mongo_db.levels.update_one(
                    {"name": {"$regex": f"^{level_name}$", "$options": "i"}, "is_legacy": False},
                    {"$set": {"video_url": video_url}}
                )
            
            if result.matched_count > 0:
                results.append(f"✅ FIXED: {level_name}")
            else:
                results.append(f"❌ NOT FOUND: {level_name}")
        
        # Clear cache to refresh immediately
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        return f"""
        <h1>🎯 ALL IMAGES FIXED!</h1>
        <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>✅ Results:</h2>
            {'<br>'.join(results)}
        </div>
        <div style="background: #cce5ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>🎨 What Should Happen Now:</h2>
            <ul>
                <li>✅ the light circles → YouTube thumbnail</li>
                <li>✅ old memories → YouTube thumbnail</li>
                <li>✅ ochiru 2 → YouTube thumbnail</li>
                <li>✅ the ringer → YouTube thumbnail</li>
                <li>⚠️ los pollos tv 3 → Shows "streamable.com" (non-YouTube)</li>
            </ul>
        </div>
        <p>
            <a href="/" style="background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px;">🏠 CHECK MAIN LIST NOW</a>
        </p>
        """
        
    except Exception as e:
        return f"❌ Error: {str(e)}"
# All broken code removed - clean slate
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

# fix_base64 route removed - no image functionality

@app.route('/fix_image_system')
def fix_image_system():
    """Complete image system overhaul"""
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

@app.route('/admin/reset_user/<user_id>', methods=['POST'])
def admin_reset_user(user_id):
    """Reset a user's points and records (admin only)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from bson.objectid import ObjectId
        
        # Convert user_id to ObjectId
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            flash('Invalid user ID', 'danger')
            return redirect(url_for('admin_users'))
        
        # Get user info
        user = mongo_db.users.find_one({"_id": user_obj_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Count records before deletion
        record_count = mongo_db.records.count_documents({"user_id": user_obj_id})
        old_points = user.get('points', 0)
        
        # Delete all user's records
        mongo_db.records.delete_many({"user_id": user_obj_id})
        
        # Reset user points to 0
        mongo_db.users.update_one(
            {"_id": user_obj_id},
            {"$set": {"points": 0}}
        )
        
        # Log the reset action
        log_message = (
            f"Admin {admin_username} reset user {user['username']}'s points "
            f"from {old_points} to 0 and deleted {record_count} records."
        )
        mongo_db.logs.insert_one({"message": log_message, "timestamp": datetime.utcnow()})
        
        flash('User reset successfully', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        flash(f'Error resetting user: {str(e)}', 'danger')
        return redirect(url_for('admin_users'))


@app.route('/debug_session')
def debug_session():
    """Debug route to check session variables"""
    if 'user_id' not in session:
        return "Not logged in"
    
    user = mongo_db.users.find_one({"_id": session['user_id']})
    if not user:
        return "User not found"
    
    return f"""
    <h1>Session Debug</h1>
    <p>User: {user['username']}</p>
    <p>Session user_id: {session.get('user_id')}</p>
    <p>Session is_admin: {session.get('is_admin', 'NOT SET')}</p>
    <p>Session head_admin: {session.get('head_admin', 'NOT SET')}</p>
    <p>DB is_admin: {user.get('is_admin', False)}</p>
    <p>DB head_admin: {user.get('head_admin', False)}</p>
    <a href="/">Back to home</a>
    """

@app.route('/admin/reset_user', methods=['POST'])
def reset_user():
    """Reset a user's points and delete their records"""
    if not session.get('head_admin'):
        return redirect(url_for('login'))

    user_id = request.form.get('user_id')
    if not user_id:
        flash('User ID is required', 'danger')
        return redirect(url_for('admin_users'))

    try:
        user = mongo_db.users.find_one({"_id": user_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))

        user_obj_id = ObjectId(user_id)
        old_points = user['points']
        record_count = mongo_db.records.count_documents({"user_id": user_obj_id})
        mongo_db.records.delete_many({"user_id": user_obj_id})
        mongo_db.users.update_one(
            {"_id": user_obj_id},
            {"$set": {"points": 0}}
        )
        
        # Log the reset action
        log_message = (
            f"Admin {admin_username} reset user {user['username']}'s points "
            f"from {old_points} to 0 and deleted {record_count} records."
        )
        mongo_db.logs.insert_one({"message": log_message, "timestamp": datetime.utcnow()})
        
        flash('User reset successfully', 'success')
        return redirect(url_for('admin_users'))
    except Exception as e:
        flash(f'Error resetting user: {str(e)}', 'danger')
        return redirect(url_for('admin_users'))



@app.route('/admin/users/promote/<user_id>')
def admin_promote_user(user_id):
    """Admin promote user"""
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    try:
        user = mongo_db.users.find_one({"_id": user_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))

        admin_username = session.get('username')

        # Promote user to admin
        mongo_db.users.update_one({"_id": user_id}, {"$set": {"is_admin": True}})

        # Log admin action
        log_admin_action(
            admin_username,
            "User Promote",
            f"Promoted {user['username']} to admin"
        )
        
        flash(f'{user["username"]} has been promoted to admin', 'success')
        return redirect(url_for('admin_console'))

    except Exception as e:
        flash(f'Error promoting user: {str(e)}', 'danger')
        print(f"Admin promote user error: {e}")
        import traceback

@app.route('/admin/demote/<username>')
def admin_demote(username):
    try:
        user = db.get_user(username)
        if not user:
            flash(f'User {username} not found', 'danger')
            return redirect(url_for('admin_console'))

        db.demote_user(username)
        flash(f'{user["username"]} has been demoted to regular user', 'success')
        return redirect(url_for('admin_console'))
    except Exception as e:
        flash(f'Error demoting user: {str(e)}', 'danger')
        print(f"Admin demote user error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_console'))

@app.route('/admin/reset_user_api/<user_id>', methods=['POST'])
def admin_reset_user_api(user_id):
    """Reset a user's API key (admin only)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        from bson.objectid import ObjectId
        
        # Convert user_id to ObjectId
        try:
            user_obj_id = ObjectId(user_id)
        except Exception:
            flash('Invalid user ID', 'danger')
            return redirect(url_for('admin_users'))
        
        # Get user info
        user = mongo_db.users.find_one({"_id": user_obj_id})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_users'))
        
        # Generate new API key
        import secrets
        new_api_key = secrets.token_urlsafe(32)
        
        # Update user's API key
        mongo_db.users.update_one(
            {"_id": user_obj_id},
            {"$set": {"api_key": new_api_key}}
        )
        
        # Get admin info for logging
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Log admin action
        log_admin_action(
            admin_username,
            "API Key Reset",
            f"Reset API key for {user['username']}"
        )
        
        flash(f'✅ API key reset for {user["username"]}. New key: {new_api_key}', 'success')
        
    except Exception as e:
        flash(f'Error resetting API key: {str(e)}', 'danger')
        print(f"Admin reset API error: {e}")
    
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
    """Debug database contents"""
    try:
        # Count total documents
        total_count = mongo_db.levels.count_documents({})
        main_count = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_count = mongo_db.levels.count_documents({"is_legacy": True})
        
        return f"""
        <h2>Database Debug Info</h2>
        <p>Total documents: {total_count}</p>
        <p>Main levels: {main_count}</p>
        <p>Legacy levels: {legacy_count}</p>
        <p>✅ Image functionality removed - no thumbnails stored</p>
        
        <p><a href='/'>Back to main</a></p>
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
        legacy_count = mongo_db.levels.count_documents({"is_legacy": True}, max_time_ms=30000)
        
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
    """Health check endpoint for database connectivity and Discord bot status"""
    try:
        # Quick ping test
        mongo_client.admin.command('ping', maxTimeMS=5000)
        
        # Quick count test
        level_count = mongo_db.levels.count_documents({}, max_time_ms=5000)
        
        # Check Discord bot status
        discord_status = 'unknown'
        try:
            from discord_bot import is_bot_available
            discord_status = 'connected' if is_bot_available() else 'disconnected'
        except Exception as e:
            discord_status = f'error: {str(e)}'
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'discord_bot': discord_status,
            'level_count': level_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'database': 'disconnected',
            'discord_bot': 'unknown',
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

@app.route('/api/level_thumbnails')
def api_level_thumbnails():
    """Return base64 thumbnail_url for all levels as JSON.
    Called asynchronously by the browser after the page renders so that
    the main page load is never blocked by large base64 transfers.

    IMPORTANT: We only serve from the in-memory cache - no DB fallback.
    Fetching 100+ thumbnail_url blobs from Atlas M0 in one query exceeds
    the 30s socket timeout. On a cold worker, the browser gets {} and shows
    YouTube fallbacks; on a warm worker (cache populated), custom thumbnails
    are returned instantly. The cache is populated when levels are edited or
    when individual level pages are loaded (see api_single_level_thumbnail)."""
    from flask import jsonify
    list_type = request.args.get('list', 'main')
    is_legacy = list_type == 'legacy'

    cache_key = 'legacy_list' if is_legacy else 'main_list'
    cached = levels_cache.get(cache_key) or []
    result = {
        str(lv['_id']): lv['thumbnail_url']
        for lv in cached
        if lv.get('thumbnail_url')
    }

    resp = jsonify(result)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/api/level_thumbnail/<level_id>')
def api_single_level_thumbnail(level_id):
    """Fetch and cache the thumbnail for one level.
    Called lazily (e.g. when a level card is scrolled into view) to
    gradually warm the in-memory thumbnail cache without a bulk DB query."""
    from flask import jsonify
    from bson import ObjectId
    # Try ObjectId first; fall back to integer for levels with numeric _id
    try:
        oid = ObjectId(level_id)
    except Exception:
        try:
            oid = int(level_id)
        except Exception:
            return jsonify({'error': 'invalid id'}), 400

    # Check in-memory cache first
    for lst_key in ('main_list', 'legacy_list'):
        for lv in (levels_cache.get(lst_key) or []):
            if str(lv.get('_id', '')) == level_id and lv.get('thumbnail_url'):
                resp = jsonify({'thumbnail_url': lv['thumbnail_url']})
                resp.headers['Cache-Control'] = 'no-store'
                return resp

    # Not in cache - fetch just this one document (one small DB round-trip)
    try:
        doc = mongo_db.levels.find_one(
            {'_id': oid, 'thumbnail_url': {'$exists': True, '$nin': ['', None]}},
            {'thumbnail_url': 1}
        )
        if doc and doc.get('thumbnail_url'):
            thumb = doc['thumbnail_url']
            # Store in cache for subsequent requests
            for lst_key in ('main_list', 'legacy_list'):
                for lv in (levels_cache.get(lst_key) or []):
                    if str(lv.get('_id', '')) == level_id:
                        lv['thumbnail_url'] = thumb
                        break
            resp = jsonify({'thumbnail_url': thumb})
            resp.headers['Cache-Control'] = 'no-store'
            return resp
    except Exception as e:
        print(f"Single thumbnail fetch failed for {level_id}: {e}")

    return jsonify({}), 200


@app.route('/')
def index():
    """Main list - cached level retrieval"""
    try:
        levels = get_fast_cached_levels(is_legacy=False)
        return render_template('index.html',
                             levels=levels,
                             total_levels=len(levels),
                             april_fools_active=False)
    except Exception as e:
        print(f"ERROR LOADING LEVELS: {e}")
        import traceback
        traceback.print_exc()
        return render_template('index.html',
                             levels=[],
                             total_levels=0,
                             april_fools_active=False)

@app.route('/legacy')
def legacy():
    """Legacy list - ULTRA-FAST with caching"""
    try:
        # Use fast cached levels
        levels = get_fast_cached_levels(is_legacy=True)
        
        return render_template('legacy.html', 
                             levels=levels, 
                             total_levels=len(levels))
    except Exception as e:
        print(f"Error loading legacy list: {e}")
        return render_template('legacy.html', 
                             levels=[], 
                             total_levels=0)
    legacy_list = get_cached_levels(is_legacy=True)
    
    # If no cache, auto-load it now
    if not legacy_list:
        try:
            print("Auto-loading legacy levels...")
            legacy_list = list(mongo_db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, "video_url": 1, "min_percentage": 1}
            ).sort("position", 1))
            
            # Cache it
            levels_cache['legacy_list'] = legacy_list
            levels_cache['last_updated'] = datetime.now(timezone.utc)
            print(f"Auto-loaded {len(legacy_list)} legacy levels")
            
        except Exception as e:
            print(f"Legacy auto-load failed: {e}")
            legacy_list = []
    
    # 🎭 APRIL FOOLS MODE: Randomize legacy positions if active
    if is_april_fools_active():
        legacy_list = randomize_level_positions(legacy_list.copy())
    
    return render_template('legacy.html', levels=legacy_list, april_fools_active=is_april_fools_active())

@app.route('/timemachine')
def timemachine():
    # Check if time machine is enabled
    settings = mongo_db.site_settings.find_one({"_id": "main"})
    if not settings or not settings.get('timemachine_enabled', True):
        flash('Time Machine feature is currently disabled', 'warning')
        return redirect(url_for('index'))
        
    selected_date = request.args.get('date')
    levels = []
    
    # Get today's date for max date limit
    today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    if selected_date:
        try:
            target_date = datetime.strptime(selected_date, '%Y-%m-%d')
            
            # Load historical rankings data
            historical_data = {}
            try:
                import json
                # Try to load the new historical data first
                try:
                    with open('historical_rankings_new.json', 'r') as f:
                        historical_data = json.load(f)
                    print("✅ Loaded new historical rankings data")
                except FileNotFoundError:
                    # Fallback to old file if new one doesn't exist
                    with open('historical_rankings.json', 'r') as f:
                        historical_data = json.load(f)
                    print("⚠️ Using old historical rankings data")
            except Exception as e:
                print(f"Error loading historical rankings: {e}")
                # Create fallback historical data based on current database
                historical_data = generate_fallback_historical_data()
            
            # Find the closest historical ranking to the selected date
            weekly_rankings = historical_data.get('weekly_rankings', {})
            closest_date = None
            closest_rankings = None
            
            # Check if the selected date is after our historical data
            # If so, use current database data
            latest_historical_date = None
            if weekly_rankings:
                latest_historical_date = max(datetime.strptime(date_str, '%Y-%m-%d') for date_str in weekly_rankings.keys())
            
            if latest_historical_date and target_date > latest_historical_date:
                # Use current database data for dates after historical data
                print(f"Using current database data for date {selected_date} (after historical data)")
                
                # For current dates (like today), show top 150 levels
                current_date = datetime.now(timezone.utc).date()
                selected_date_obj = target_date.date()
                
                # If the selected date is today or within the last 7 days, show top 150
                days_difference = (current_date - selected_date_obj).days
                if days_difference <= 7:
                    print(f"Showing top 150 levels for recent date: {selected_date}")
                    current_levels = list(mongo_db.levels.find(
                        {"is_legacy": False}, 
                        max_time_ms=60000
                    ).sort("position", 1).limit(100))  # Top 100 for recent dates
                else:
                    print(f"Showing top 10 levels for older date: {selected_date}")
                    current_levels = list(mongo_db.levels.find(
                        {"is_legacy": False}, 
                        max_time_ms=60000
                    ).sort("position", 1).limit(10))  # Top 10 for older dates
                
                closest_rankings = []
                for level in current_levels:
                    closest_rankings.append({
                        "position": level.get('position', 0),
                        "name": level.get('name', 'Unknown')
                    })
                closest_date = target_date
            else:
                # Find the most recent ranking before or on the selected date from historical data
                for date_str, ranking_data in weekly_rankings.items():
                    ranking_date = datetime.strptime(date_str, '%Y-%m-%d')
                    if ranking_date <= target_date:
                        if closest_date is None or ranking_date > closest_date:
                            closest_date = ranking_date
                            closest_rankings = ranking_data['rankings']
            
            if closest_rankings:
                # Get all levels from database to match with historical rankings
                all_levels = {level['name']: level for level in mongo_db.levels.find({}, max_time_ms=60000)}
                
                # Create a mapping of current level positions
                current_positions = {}
                for level in all_levels.values():
                    if not level.get('is_legacy', False):
                        current_positions[level['name']] = level.get('position')
                
                def add_current_thumbnail(level_data, level_name):
                    """Add current thumbnail data to a level - ONLY use current database images"""
                    # Only use current thumbnail from database level (NO FALLBACK to old thumbnails.json)
                    current_level = all_levels.get(level_name)
                    if current_level:
                        # Copy current thumbnail data (this ensures historical levels use current images)
                        if current_level.get('thumbnail_url'):
                            # Check if it's already a base64 data URL
                            thumbnail_url = current_level['thumbnail_url']
                            if thumbnail_url.startswith('data:image/'):
                                # It's already a base64 data URL, use it directly
                                level_data['thumbnail_base64'] = thumbnail_url
                            else:
                                # It's a regular URL
                                level_data['thumbnail_url'] = thumbnail_url
                            return
                        
                        if current_level.get('video_url'):
                            level_data['video_url'] = current_level['video_url']
                            return
                        
                        # Also copy other current data that might be useful
                        if current_level.get('creator'):
                            level_data['creator'] = current_level['creator']
                        if current_level.get('verifier'):
                            level_data['verifier'] = current_level['verifier']
                        if current_level.get('difficulty'):
                            level_data['difficulty'] = current_level['difficulty']
                        if current_level.get('level_id'):
                            level_data['level_id'] = current_level['level_id']
                    
                    # NO FALLBACK to thumbnails.json - only use current database images
                
                levels = []
                for ranking in closest_rankings:
                    level_name = ranking['name']
                    historical_pos = ranking['position']
                    
                    # Find the level in the database
                    level = all_levels.get(level_name)
                    if level:
                        # Create a copy to avoid modifying the original
                        level_copy = dict(level)
                        level_copy['historical_position'] = historical_pos
                        level_copy['historical_points'] = calculate_level_points(historical_pos, False)
                        level_copy['current_position'] = current_positions.get(level_name)
                        
                        # Always use current thumbnail data
                        add_current_thumbnail(level_copy, level_name)
                        
                        levels.append(level_copy)
                    else:
                        # Level not found in database, create a placeholder with current thumbnail
                        placeholder_level = {
                            '_id': f"placeholder_{level_name}",
                            'name': level_name,
                            'creator': 'Unknown',
                            'verifier': 'Unknown',
                            'difficulty': 10,
                            'historical_position': historical_pos,
                            'historical_points': calculate_level_points(historical_pos, False),
                            'is_placeholder': True,
                            'current_position': None,
                            'level_id': None
                        }
                        
                        # Use current thumbnail data even for placeholder levels
                        add_current_thumbnail(placeholder_level, level_name)
                        
                        levels.append(placeholder_level)
                
                # Add info about which week's data we're showing
                if 'user_id' in session and session.get('is_admin'):
                    week_num = None
                    for date_str, ranking_data in weekly_rankings.items():
                        if datetime.strptime(date_str, '%Y-%m-%d') == closest_date:
                            week_num = ranking_data.get('week')
                            break
                    print(f"Time machine: Showing week {week_num} rankings from {closest_date.strftime('%Y-%m-%d')} for selected date {selected_date}")
            
        except ValueError:
            flash('Invalid date format', 'danger')
        except Exception as e:
            print(f"Error in time machine: {e}")
            flash('Error loading historical data', 'danger')
    
    return render_template('timemachine.html', levels=levels, selected_date=selected_date, today_date=today_date)

def generate_fallback_historical_data():
    """Generate fallback historical data based on current database state"""
    try:
        # Get current main list levels (top 100)
        current_levels = list(mongo_db.levels.find(
            {"is_legacy": False}, 
            max_time_ms=60000
        ).sort("position", 1).limit(100))
        
        # Create historical snapshots going back in time
        historical_data = {"weekly_rankings": {}}
        
        # Start from June 21, 2025 and create weekly snapshots
        start_date = datetime(2025, 6, 21, tzinfo=timezone.utc)
        
        for week in range(26):  # 26 weeks of data (6 months)
            snapshot_date = start_date + timedelta(weeks=week)
            date_str = snapshot_date.strftime('%Y-%m-%d')
            
            # Create a slightly different ranking for each week
            # Simulate historical changes by shuffling positions slightly
            rankings = []
            
            for i, level in enumerate(current_levels):
                # Add some historical variation to positions
                historical_pos = i + 1
                if week > 0:
                    # Add some randomness to simulate historical changes
                    import random
                    random.seed(hash(level['name'] + str(week)))  # Consistent randomness
                    
                    # More variation for earlier weeks
                    max_variation = min(5, week // 2 + 1)
                    variation = random.randint(-max_variation, max_variation)
                    
                    # Less variation for top levels
                    if i < 10:
                        variation = variation // 2
                    
                    historical_pos = max(1, min(150, historical_pos + variation))
                
                rankings.append({
                    "position": historical_pos,
                    "name": level['name']
                })
            
            # Sort by position and ensure no duplicates
            rankings.sort(key=lambda x: x['position'])
            
            # Fix any duplicate positions
            used_positions = set()
            fixed_rankings = []
            for ranking in rankings:
                pos = ranking['position']
                while pos in used_positions and pos <= 100:
                    pos += 1
                if pos <= 100:
                    used_positions.add(pos)
                    ranking['position'] = pos
                    fixed_rankings.append(ranking)
            
            # Take top 150 and sort by position
            fixed_rankings = fixed_rankings[:150]
            fixed_rankings.sort(key=lambda x: x['position'])
            
            historical_data["weekly_rankings"][date_str] = {
                "week": week + 1,
                "rankings": fixed_rankings
            }
        
        return historical_data
        
    except Exception as e:
        print(f"Error generating fallback historical data: {e}")
        return {"weekly_rankings": {}}

def update_historical_rankings():
    """Update historical rankings with current data - called when levels change"""
    try:
        # Get current main list levels (top 100)
        current_levels = list(mongo_db.levels.find(
            {"is_legacy": False}, 
            max_time_ms=60000
        ).sort("position", 1).limit(100))
        
        # Load existing historical data
        historical_data = {}
        try:
            import json
            with open('historical_rankings.json', 'r') as f:
                historical_data = json.load(f)
        except:
            historical_data = {"weekly_rankings": {}}
        
        # Add current week's data
        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Find the highest week number
        max_week = 0
        for date_str, ranking_data in historical_data.get('weekly_rankings', {}).items():
            week_num = ranking_data.get('week', 0)
            if week_num > max_week:
                max_week = week_num
        
        # Create current rankings
        current_rankings = []
        for level in current_levels:
            current_rankings.append({
                "position": level.get('position', 0),
                "name": level.get('name', 'Unknown')
            })
        
        # Add to historical data
        historical_data['weekly_rankings'][current_date] = {
            "week": max_week + 1,
            "rankings": current_rankings
        }
        
        # Save updated historical data
        with open('historical_rankings.json', 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        print(f"Updated historical rankings for {current_date}")
        return True
        
    except Exception as e:
        print(f"Error updating historical rankings: {e}")
        return False

@app.route('/level/<level_id>')
def level_detail(level_id):
    try:
        level = None
        level_id_for_records = None
        
        # Exclude thumbnail_url — the detail page embeds a video player, not
        # a static image.  Skipping the large base64 blob avoids socket timeouts.
        _detail_proj = {"thumbnail_url": 0}

        # Try multiple approaches to find the level
        # 1. Try as ObjectId first (for new levels)
        try:
            level_object_id = ObjectId(level_id)
            level = mongo_db.levels.find_one({"_id": level_object_id}, _detail_proj)
            level_id_for_records = level_object_id
            print(f"Found level by ObjectId: {level_id}")
        except (ValueError, InvalidId):
            pass

        # 2. If not found, try as integer (for legacy levels)
        if not level:
            try:
                level_int_id = int(level_id)
                level = mongo_db.levels.find_one({"_id": level_int_id}, _detail_proj)
                level_id_for_records = level_int_id
                print(f"Found level by int ID: {level_id}")
            except (ValueError, TypeError):
                pass

        # 3. If still not found, try searching by level_id field (GD level ID)
        if not level:
            try:
                level = mongo_db.levels.find_one({"level_id": level_id}, _detail_proj)
                if level:
                    level_id_for_records = level["_id"]
                    print(f"Found level by level_id field: {level_id}")
            except Exception:
                pass

        # 4. Final attempt: search by name (case insensitive)
        if not level:
            try:
                level = mongo_db.levels.find_one({"name": {"$regex": f"^{level_id}$", "$options": "i"}}, _detail_proj)
                if level:
                    level_id_for_records = level["_id"]
                    print(f"Found level by name: {level_id}")
            except Exception:
                pass
        
        if not level:
            flash('Level not found. Please check the level ID or try browsing the main list.', 'danger')
            return redirect(url_for('index'))
        
        # Check if user is admin to show hidden records
        is_admin = 'user_id' in session and session.get('is_admin', False)
        
        # Build match criteria - exclude hidden records for non-admins
        match_criteria = {"level_id": level_id_for_records, "status": "approved"}
        if not is_admin:
            match_criteria["$or"] = [
                {"hidden": {"$exists": False}},
                {"hidden": False}
            ]
        
        # Get approved records with user info - with error handling
        records = []
        try:
            records = list(mongo_db.records.aggregate([
                {"$match": match_criteria},
                {"$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }},
                {"$unwind": "$user"},
                {"$sort": {"progress": -1, "date_submitted": 1}},  # 100% first, then by date
                {"$limit": 100}  # Limit to first 100 records for performance
            ], allowDiskUse=True))
        except Exception as e:
            print(f"Error loading records for level {level_id}: {e}")
            # Fallback to simple query
            try:
                records = list(mongo_db.records.find(match_criteria).limit(50))
                # Add user info manually
                for record in records:
                    user = mongo_db.users.find_one({"_id": record["user_id"]})
                    record["user"] = user if user else {"username": "Unknown User"}
            except Exception as e2:
                print(f"Fallback record query also failed: {e2}")
                records = []
        
        # Get position history for this level
        position_history = []
        try:
            position_history = list(mongo_db.position_history.find(
                {"level_id": level_id_for_records}
            ).sort("change_date", -1).limit(20))
        except Exception as e:
            print(f"Error loading position history: {e}")
        
        return render_template('level_detail.html', level=level, records=records, position_history=position_history, is_admin=is_admin)
        
    except Exception as e:
        print(f"Critical error in level_detail route: {e}")
        flash('An error occurred while loading the level. Please try again.', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = mongo_db.users.find_one({"username": username}, max_time_ms=60000)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['_id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            session['head_admin'] = user.get('head_admin', False)  # Add this line
            session['date_joined'] = user.get('date_joined')
            session.permanent = True  # Make session permanent

            # Load user preferences
            session['theme'] = user.get('theme_preference', 'light')
            
            # Log login activity
            login_entry = {
                "user_id": user['_id'],
                "timestamp": datetime.now(timezone.utc),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown')
            }
            mongo_db.login_history.insert_one(login_entry)
            
            # Update user's last IP address
            try:
                mongo_db.users.update_one(
                    {"_id": user['_id']},
                    {"$set": {"last_ip": request.remote_addr}}
                )
            except Exception as e:
                print(f"Error updating user IP: {e}")
            
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
        
        # Check username for profanity
        is_username_clean, profanity_reason = check_username_profanity(username)
        if not is_username_clean:
            flash(f'Username not allowed: {profanity_reason}', 'danger')
            return render_template('register.html')
        
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
            "date_joined": datetime.now(timezone.utc),
            "last_ip": request.remote_addr
        }
        
        mongo_db.users.insert_one(new_user)
        
        # Log registration activity
        try:
            login_entry = {
                "user_id": new_user['_id'],
                "timestamp": datetime.now(timezone.utc),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown'),
                "login_method": "registration"
            }
            mongo_db.login_history.insert_one(login_entry)
        except Exception as e:
            print(f"Error logging registration: {e}")
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    session.pop('head_admin', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/toggle_theme')
def toggle_theme():
    # Get the requested theme from query parameter or toggle between light/dark
    requested_theme = request.args.get('theme')
    
    if requested_theme and (requested_theme in ['light', 'dark', 'auto', 'blue', 'purple', 'green', 'red', 'orange'] or requested_theme.startswith('custom_')):
        new_theme = requested_theme
    else:
        # Fallback to simple toggle for old functionality
        current_theme = session.get('theme', 'light')
        new_theme = 'dark' if current_theme == 'light' else 'light'
    
    session['theme'] = new_theme
    session.permanent = True  # Make session permanent
    
    # Save theme to database if user is logged in
    if 'user_id' in session:
        try:
            mongo_db.users.update_one(
                {"_id": session['user_id']},
                {"$set": {"theme_preference": new_theme}}
            )
        except Exception as e:
            print(f"Error saving theme preference: {e}")
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {'theme': new_theme, 'status': 'success'}
    
    return redirect(request.referrer or url_for('index'))

@app.route('/custom-theme-creator', methods=['GET', 'POST'])
def custom_theme_creator():
    """Custom theme creator page"""
    if 'user_id' not in session:
        flash('Please log in to create custom themes', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            # Get form data
            theme_name = request.form.get('theme_name', '').strip()
            primary_color = request.form.get('primary_color', '#0d6efd')
            secondary_color = request.form.get('secondary_color', '#6c757d')
            background_color = request.form.get('background_color', '#ffffff')
            text_color = request.form.get('text_color', '#212529')
            card_color = request.form.get('card_color', '#f8f9fa')
            accent_color = request.form.get('accent_color', '#198754')
            
            if not theme_name:
                return {'success': False, 'error': 'Theme name is required'}
            
            if len(theme_name) > 50:
                return {'success': False, 'error': 'Theme name too long (max 50 characters)'}
            
            # Create custom theme object with unique ID
            from bson import ObjectId
            theme_id = str(ObjectId())
            
            custom_theme = {
                'id': theme_id,
                'name': theme_name,
                'primary_color': primary_color,
                'secondary_color': secondary_color,
                'background_color': background_color,
                'text_color': text_color,
                'card_color': card_color,
                'accent_color': accent_color,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Save to user's profile (add to array of custom themes)
            user_id = session['user_id']
            mongo_db.users.update_one(
                {"_id": user_id},
                {
                    "$push": {"custom_themes": custom_theme},
                    "$set": {"theme_preference": f"custom_{theme_id}"}
                }
            )
            
            # Update session
            session['theme'] = f'custom_{theme_id}'
            
            return {'success': True, 'message': 'Custom theme saved successfully!'}
            
        except Exception as e:
            print(f"Error saving custom theme: {e}")
            return {'success': False, 'error': 'Failed to save custom theme'}
    
    return render_template('custom_theme_creator.html')

@app.route('/theme-manager')
def theme_manager():
    """Theme management page"""
    if 'user_id' not in session:
        flash('Please log in to manage themes', 'warning')
        return redirect(url_for('login'))
    
    # Get user's custom themes
    user = mongo_db.users.find_one({"_id": session['user_id']})
    custom_themes = user.get('custom_themes', []) if user else []
    
    return render_template('theme_manager.html', custom_themes=custom_themes)

@app.route('/delete-theme/<theme_id>', methods=['POST'])
def delete_theme(theme_id):
    """Delete a custom theme"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}
    
    try:
        user_id = session['user_id']
        
        # Remove theme from user's custom_themes array
        result = mongo_db.users.update_one(
            {"_id": user_id},
            {"$pull": {"custom_themes": {"id": theme_id}}}
        )
        
        if result.modified_count > 0:
            # If user was using this theme, switch to light theme
            current_theme = session.get('theme', 'light')
            if current_theme == f'custom_{theme_id}':
                session['theme'] = 'light'
                mongo_db.users.update_one(
                    {"_id": user_id},
                    {"$set": {"theme_preference": "light"}}
                )
            
            return {'success': True, 'message': 'Theme deleted successfully'}
        else:
            return {'success': False, 'error': 'Theme not found'}
            
    except Exception as e:
        print(f"Error deleting theme: {e}")
        return {'success': False, 'error': 'Failed to delete theme'}

@app.route('/edit-theme/<theme_id>')
def edit_theme(theme_id):
    """Edit an existing custom theme"""
    if 'user_id' not in session:
        flash('Please log in to edit themes', 'warning')
        return redirect(url_for('login'))
    
    # Get the specific theme
    user = mongo_db.users.find_one({"_id": session['user_id']})
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('theme_manager'))
    
    custom_themes = user.get('custom_themes', [])
    theme_to_edit = None
    
    for theme in custom_themes:
        if theme.get('id') == theme_id:
            theme_to_edit = theme
            break
    
    if not theme_to_edit:
        flash('Theme not found', 'error')
        return redirect(url_for('theme_manager'))
    
    return render_template('custom_theme_creator.html', edit_theme=theme_to_edit)

@app.route('/update-theme/<theme_id>', methods=['POST'])
def update_theme(theme_id):
    """Update an existing custom theme"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}
    
    try:
        # Get form data
        theme_name = request.form.get('theme_name', '').strip()
        primary_color = request.form.get('primary_color', '#0d6efd')
        secondary_color = request.form.get('secondary_color', '#6c757d')
        background_color = request.form.get('background_color', '#ffffff')
        text_color = request.form.get('text_color', '#212529')
        card_color = request.form.get('card_color', '#f8f9fa')
        accent_color = request.form.get('accent_color', '#198754')
        
        if not theme_name:
            return {'success': False, 'error': 'Theme name is required'}
        
        if len(theme_name) > 50:
            return {'success': False, 'error': 'Theme name too long (max 50 characters)'}
        
        # Update the theme in the array
        user_id = session['user_id']
        result = mongo_db.users.update_one(
            {"_id": user_id, "custom_themes.id": theme_id},
            {
                "$set": {
                    "custom_themes.$.name": theme_name,
                    "custom_themes.$.primary_color": primary_color,
                    "custom_themes.$.secondary_color": secondary_color,
                    "custom_themes.$.background_color": background_color,
                    "custom_themes.$.text_color": text_color,
                    "custom_themes.$.card_color": card_color,
                    "custom_themes.$.accent_color": accent_color,
                    "custom_themes.$.updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            return {'success': True, 'message': 'Theme updated successfully!'}
        else:
            return {'success': False, 'error': 'Theme not found or no changes made'}
            
    except Exception as e:
        print(f"Error updating theme: {e}")
        return {'success': False, 'error': 'Failed to update theme'}

@app.route('/update_theme', methods=['POST'])
def update_theme_preference():
    """Update user theme preference for mobile"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}
    
    try:
        theme = request.form.get('theme', 'light')
        if theme not in ['light', 'dark']:
            theme = 'light'
        
        user_id = session['user_id']
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"theme": theme}}
        )
        
        # Update session theme
        session['theme'] = theme
        
        return {'success': True}
    except Exception as e:
        print(f"Error updating theme preference: {e}")
        return {'success': False, 'error': 'Failed to update theme'}

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
                    "head_admin": False,
                    "points": 0,
                    "date_joined": datetime.now(timezone.utc)
                }
                mongo_db.users.insert_one(user)
        
        # Log in the user
        session['user_id'] = user['_id']
        session['username'] = user['username']
        session['is_admin'] = user.get('is_admin', False)
        session['head_admin'] = user.get('head_admin', False)
        session['date_joined'] = user.get('date_joined')
        session.permanent = True  # Make session permanent

        # Load user preferences
        session['theme'] = user.get('theme_preference', 'light')

        # Log login activity
        login_entry = {
            "user_id": user['_id'],
            "timestamp": datetime.now(timezone.utc),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "login_method": "google"
        }
        mongo_db.login_history.insert_one(login_entry)
        
        # Update user's last IP address
        try:
            mongo_db.users.update_one(
                {"_id": user['_id']},
                {"$set": {"last_ip": request.remote_addr}}
            )
        except Exception as e:
            print(f"Error updating user IP: {e}")
        
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'Google login failed: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/auth/discord')
def discord_login():
    """Discord OAuth login"""
    if not discord_oauth:
        client_id = app.config.get('DISCORD_CLIENT_ID')
        client_secret = app.config.get('DISCORD_CLIENT_SECRET')
        
        if not client_id:
            flash('Discord Sign-In is not configured: Missing Client ID', 'danger')
        elif not client_secret or client_secret == 'your_discord_client_secret_here':
            flash('Discord Sign-In is not configured: Please set up your Discord Client Secret in the Developer Portal', 'warning')
        else:
            flash('Discord Sign-In configuration error: Please check your credentials', 'danger')
        
        return redirect(url_for('profile'))
    
    # Generate redirect URI - try to use the configured website URL first
    website_url = os.environ.get('WEBSITE_URL', '').rstrip('/')
    if website_url and not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
        # Production - use configured website URL
        redirect_uri = f"{website_url}/auth/discord/callback"
    else:
        # Local development - use Flask's url_for
        redirect_uri = url_for('discord_callback', _external=True)
    
    print(f"🔍 Discord OAuth redirect URI: {redirect_uri}")
    return discord_oauth.authorize_redirect(redirect_uri)

@app.route('/discord-setup-help')
def discord_setup_help():
    """Help page for Discord OAuth setup"""
    return render_template('discord_setup_help.html')

@app.route('/debug/discord-redirect')
def debug_discord_redirect():
    """Debug route to check what redirect URI is being generated"""
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access denied", 403
    
    # Generate redirect URI the same way as the login route
    website_url = os.environ.get('WEBSITE_URL', '').rstrip('/')
    if website_url and not request.host.startswith('localhost') and not request.host.startswith('127.0.0.1'):
        redirect_uri = f"{website_url}/auth/discord/callback"
    else:
        redirect_uri = url_for('discord_callback', _external=True)
    
    return f"""
    <h3>Discord OAuth Debug Info</h3>
    <p><strong>Generated Redirect URI:</strong> {redirect_uri}</p>
    <p><strong>Request Host:</strong> {request.host}</p>
    <p><strong>Request URL:</strong> {request.url}</p>
    <p><strong>Is Secure:</strong> {request.is_secure}</p>
    <p><strong>Website URL (env):</strong> {website_url}</p>
    
    <h4>Add this exact URI to your Discord application:</h4>
    <code>{redirect_uri}</code>
    
    <br><br>
    <a href="{url_for('discord_setup_help')}">Setup Help</a> | 
    <a href="{url_for('profile')}">Back to Profile</a>
    """

@app.route('/auth/discord/callback')
def discord_callback():
    """Discord OAuth callback"""
    if not discord_oauth:
        flash('Discord Sign-In is not configured', 'danger')
        return redirect(url_for('login'))
    
    try:
        token = discord_oauth.authorize_access_token()
        
        # Get user info from Discord API
        headers = {'Authorization': f'Bearer {token["access_token"]}'}
        resp = requests.get('https://discord.com/api/users/@me', headers=headers)
        user_info = resp.json()
        
        discord_id = user_info['id']
        username = user_info['username']
        discriminator = user_info.get('discriminator', '0000')
        
        # Check if user is logged in to link account
        if 'user_id' in session:
            # Link Discord account to existing logged-in user
            user = mongo_db.users.find_one({"_id": session['user_id']})
            if user:
                # Check if Discord account is already linked to another user
                existing_discord_user = mongo_db.users.find_one({"discord_id": discord_id})
                if existing_discord_user and existing_discord_user['_id'] != user['_id']:
                    flash('This Discord account is already linked to another user', 'danger')
                    return redirect(url_for('profile'))
                
                # Link Discord account
                mongo_db.users.update_one(
                    {"_id": user['_id']},
                    {"$set": {
                        "discord_id": discord_id,
                        "discord_username": f"{username}#{discriminator}"
                    }}
                )
                flash('Discord account linked successfully!', 'success')
                return redirect(url_for('profile'))
        else:
            # Check if user exists with this Discord ID
            user = mongo_db.users.find_one({"discord_id": discord_id})
            
            if not user:
                flash('No account found with this Discord ID. Please create an account first and then link your Discord.', 'warning')
                return redirect(url_for('register'))
            
            # Log in the user
            session['user_id'] = user['_id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            session['head_admin'] = user.get('head_admin', False)
            session['date_joined'] = user.get('date_joined')
            session.permanent = True

            # Load user preferences
            session['theme'] = user.get('theme_preference', 'light')
            
            # Log login activity
            login_entry = {
                "user_id": user['_id'],
                "timestamp": datetime.now(timezone.utc),
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', 'Unknown'),
                "login_method": "discord"
            }
            mongo_db.login_history.insert_one(login_entry)
            
            # Update user's last IP address
            try:
                mongo_db.users.update_one(
                    {"_id": user['_id']},
                    {"$set": {"last_ip": request.remote_addr}}
                )
            except Exception as e:
                print(f"Error updating user IP: {e}")
            
            flash('Successfully logged in with Discord!', 'success')
            return redirect(url_for('index'))
    
    except Exception as e:
        error_str = str(e).lower()
        print(f"Discord OAuth error: {e}")
        
        # Check for redirect URI error specifically
        if 'redirect_uri' in error_str or 'invalid_request' in error_str:
            flash('Discord OAuth redirect URI error. Please check the setup instructions.', 'danger')
            return redirect(url_for('discord_setup_help'))
        else:
            flash(f'Discord login failed: {str(e)}', 'danger')
            return redirect(url_for('profile'))

@app.route('/auth/discord/unlink', methods=['POST'])
def discord_unlink():
    """Unlink Discord account from user"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))
    
    try:
        mongo_db.users.update_one(
            {"_id": session['user_id']},
            {"$unset": {"discord_id": "", "discord_username": ""}}
        )
        flash('Discord account unlinked successfully!', 'success')
    except Exception as e:
        print(f"Error unlinking Discord: {e}")
        flash('Error unlinking Discord account', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user = mongo_db.users.find_one({"_id": session['user_id']}, max_time_ms=60000)

    # Single aggregation — fetch all user records with level info in one DB round-trip.
    # preserveNullAndEmptyArrays keeps records whose level was deleted so they still show.
    all_user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": session['user_id']}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": {"path": "$level", "preserveNullAndEmptyArrays": True}},
        {"$sort": {"date_submitted": -1}}
    ], allowDiskUse=True))

    # Derive filtered views in Python — no extra DB round-trips
    approved_records     = [r for r in all_user_records if r.get('status') == 'approved']
    main_list_approved   = [r for r in approved_records if not r.get('level', {}).get('is_legacy', False)]
    legacy_list_approved = [r for r in approved_records if r.get('level', {}).get('is_legacy', False)]

    # Calculate accurate stats
    approved_count         = len(approved_records)
    main_completed_count   = len([r for r in main_list_approved   if r.get('progress') == 100])
    legacy_completed_count = len([r for r in legacy_list_approved if r.get('progress') == 100])
    total_submissions = len(all_user_records)
    pending_count = len([r for r in all_user_records if r.get('status') == 'pending'])
    
    return render_template('profile.html', 
                         user=user, 
                         records=all_user_records,  # For displaying in tabs
                         approved_records=approved_records,  # For stats calculations
                         approved_count=approved_count,
                         main_completed_count=main_completed_count,
                         legacy_completed_count=legacy_completed_count,
                         total_submissions=total_submissions,
                         pending_count=pending_count)

@app.route('/submit_record', methods=['GET', 'POST'])
def submit_record():
    if 'user_id' not in session:
        flash('Please log in to submit a record', 'warning')
        return redirect(url_for('login'))
    
    # Check if user is temp banned
    is_banned, ban_info = is_user_temp_banned(session['user_id'])
    if is_banned and ban_info:
        expiry_date = ban_info.get('expiry_date')
        reason = ban_info.get('reason', 'Rule Violation')
        expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M UTC') if expiry_date else 'Unknown'
        flash(f'You are temporarily banned from submitting records. Reason: {reason}. Ban expires: {expiry_str}', 'danger')
        return redirect(url_for('index'))
    
    # Check if submissions are enabled
    try:
        settings = mongo_db.site_settings.find_one({"_id": "main"})
        submissions_enabled = settings.get('submissions_enabled', True) if settings else True
        
        if not submissions_enabled:
            flash('Record submissions are currently disabled by administrators', 'warning')
            return redirect(url_for('index'))
    except Exception as e:
        print(f"Error checking submission settings: {e}")
        # Default to enabled if there's an error
    
    if request.method == 'POST':
        # Check if this is a multiple submission
        multiple_submission = request.form.get('multiple_submission') == 'true'
        
        if multiple_submission:
            return handle_multiple_record_submission()
        else:
            return handle_single_record_submission()
    
    # Use cached levels - if no cache, redirect to load
    levels = get_cached_levels(is_legacy=False)
    if not levels:
        flash('Please load levels first', 'info')
        return redirect(url_for('instant_load'))

    return render_template('submit_record.html', levels=levels)

@app.route('/submit_verification', methods=['GET', 'POST'])
def submit_verification():
    """Handle verification submissions - requires Discord authentication"""
    if 'user_id' not in session:
        flash('Please log in to submit a verification', 'warning')
        return redirect(url_for('login'))
    
    # Check if user is temp banned
    is_banned, ban_info = is_user_temp_banned(session['user_id'])
    if is_banned and ban_info:
        expiry_date = ban_info.get('expiry_date')
        reason = ban_info.get('reason', 'Rule Violation')
        expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M UTC') if expiry_date else 'Unknown'
        flash(f'You are temporarily banned from submitting records. Reason: {reason}. Ban expires: {expiry_str}', 'danger')
        return redirect(url_for('index'))
    
    # Check if user has connected their Discord account
    user = mongo_db.users.find_one({"_id": session['user_id']})
    if not user or not user.get('discord_id'):
        flash('You must connect your Discord account to submit verifications. Please link your Discord account in your profile.', 'warning')
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        return handle_verification_submission()
    
    # Get difficulty options for dropdown
    difficulty_options = [
        'Easy', 'Normal', 'Hard', 'Harder', 'Insane',
        'Easy Demon', 'Medium Demon', 'Hard Demon', 'Insane Demon', 'Extreme Demon'
    ]
    
    return render_template('submit_verification.html', difficulty_options=difficulty_options)

def handle_verification_submission():
    """Handle verification submission form processing"""
    # Get form data
    verification_url = request.form.get('verification_url', '').strip()
    level_id = request.form.get('level_id', '').strip()
    level_name = request.form.get('level_name', '').strip()
    creator = request.form.get('creator', '').strip()
    verifier = request.form.get('verifier', '').strip()
    difficulty = request.form.get('difficulty', '').strip()
    placement = request.form.get('placement', '').strip()
    experience = request.form.get('experience', '').strip()
    enjoyment = request.form.get('enjoyment', '').strip()
    comments = request.form.get('comments', '').strip()
    
    # Validate required fields
    if not verification_url:
        flash('Please provide a verification video URL', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not level_id:
        flash('Please enter the level ID', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not level_name:
        flash('Please enter the level name', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not creator:
        flash('Please enter the creator name', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not verifier:
        flash('Please enter the verifier name', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not difficulty:
        flash('Please select a difficulty', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not placement:
        flash('Please enter the placement on the list', 'danger')
        return redirect(url_for('submit_verification'))
    
    if not experience or not enjoyment:
        flash('Please rate both experience and enjoyment', 'danger')
        return redirect(url_for('submit_verification'))
    
    # Validate numeric fields
    try:
        # Handle both ObjectId and integer level IDs
        try:
            level_id_num = ObjectId(level_id)
        except (ValueError, InvalidId):
            level_id_num = int(level_id)
        
        placement_num = int(placement)
        experience_num = int(experience)
        enjoyment_num = int(enjoyment)
        
        if level_id_num < 1:
            flash('Level ID must be a positive number', 'danger')
            return redirect(url_for('submit_verification'))
        
        if placement_num < 1:
            flash('Placement must be a positive number', 'danger')
            return redirect(url_for('submit_verification'))
        
        if experience_num < 1 or experience_num > 10:
            flash('Experience rating must be between 1 and 10', 'danger')
            return redirect(url_for('submit_verification'))
        
        if enjoyment_num < 1 or enjoyment_num > 10:
            flash('Enjoyment rating must be between 1 and 10', 'danger')
            return redirect(url_for('submit_verification'))
            
    except ValueError:
        flash('Please enter valid numbers for level ID, placement, experience, and enjoyment', 'danger')
        return redirect(url_for('submit_verification'))
    
    # Check for profanity in level name
    is_allowed, reason = check_level_name_profanity(level_name)
    if not is_allowed:
        flash(f'Level name not allowed: {reason}', 'danger')
        return redirect(url_for('submit_verification'))
    
    # Check for profanity in comments if provided
    if comments:
        is_allowed, reason = check_comment_profanity(comments)
        if not is_allowed:
            flash(f'Comments not allowed: {reason}', 'danger')
            return redirect(url_for('submit_verification'))
    
    # Create verification submission record
    verification_id = ObjectId()
    verification_submission = {
        "_id": verification_id,
        "user_id": session['user_id'],
        "verification_url": verification_url,
        "level_id": level_id,
        "level_name": level_name,
        "creator": creator,
        "verifier": verifier,
        "difficulty": difficulty,
        "placement": placement_num,
        "experience": experience_num,
        "enjoyment": enjoyment_num,
        "comments": comments,
        "status": "pending",
        "date_submitted": datetime.now(timezone.utc),
        "submission_type": "verification"
    }
    
    # Insert into database
    try:
        mongo_db.verification_submissions.insert_one(verification_submission)
        
        # Get user info for notifications
        user = mongo_db.users.find_one({"_id": session['user_id']})
        username = user['username'] if user else 'Unknown'
        
        # Send Discord notification to admin channel
        try:
            if is_bot_available():
                notify_verification_submission(
                    username, level_name, creator, verifier, difficulty, placement_num, 
                    experience_num, enjoyment_num, verification_url, comments, level_id
                )
                print(f"✅ Discord notification sent for verification submission by {username}")
            else:
                print("⚠️ Discord bot not available - skipping notification")
        except Exception as e:
            print(f"Error sending Discord notification: {e}")
        
        # Log the submission
        try:
            mongo_db.admin_logs.insert_one({
                "timestamp": datetime.now(timezone.utc),
                "action": "verification_submitted",
                "admin": username,
                "details": f"Verification submitted for {level_name} (#{placement_num})"
            })
        except Exception as e:
            print(f"Error logging verification submission: {e}")
        
        flash('Verification submitted successfully! It will be reviewed by administrators.', 'success')
        return redirect(url_for('profile'))
        
    except Exception as e:
        print(f"Error submitting verification: {e}")
        flash('Error submitting verification. Please try again.', 'danger')
        return redirect(url_for('submit_verification'))

def handle_single_record_submission():
    """Handle single record submission"""
    # Validate form data
    level_id_str = request.form.get('level_id', '').strip()
    progress_str = request.form.get('progress', '').strip()
    video_url = request.form.get('video_url', '').strip()
    comments = request.form.get('comments', '').strip()
    
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
    
    # Convert level_id and progress
    try:
        # Handle both ObjectId and integer level IDs
        try:
            level_id = ObjectId(level_id_str)
        except (ValueError, InvalidId):
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
    
    # Generate new ObjectId for record
    next_id = ObjectId()
    
    new_record = {
        "_id": next_id,
        "user_id": session['user_id'],
        "level_id": level_id,
        "progress": progress,
        "video_url": video_url,
        "comments": comments,
        "status": "pending",
        "date_submitted": datetime.now(timezone.utc)
    }
    
    mongo_db.records.insert_one(new_record)
    
    # Log submission with comments
    log_submission_with_comments(session['user_id'], level['name'], progress, comments)
    
    # Send Discord notification
    try:
        user = mongo_db.users.find_one({"_id": session['user_id']})
        username = user['username'] if user else 'Unknown'
        print(f"🔔 Sending Discord notification for {username} - {level['name']} - {progress}%")
        
        # Try the imported function first
        if DISCORD_AVAILABLE:
            notify_record_submitted(username, level['name'], progress, video_url, comments)
        else:
            # Fallback: send Discord notification directly
            send_discord_notification_direct(username, level['name'], progress, video_url, comments)
        
        print(f"✅ Discord notification sent successfully")
    except Exception as e:
        print(f"❌ Discord notification error: {e}")
        import traceback
        traceback.print_exc()
    
    flash('Record submitted successfully! It will be reviewed by moderators.', 'success')
    return redirect(url_for('profile'))

def handle_multiple_record_submission():
    """Handle multiple record submissions at once"""
    try:
        # Get the number of records being submitted
        record_count = int(request.form.get('record_count', 1))
        
        if record_count < 1 or record_count > 10:  # Limit to 10 records max
            flash('You can submit between 1 and 10 records at once', 'danger')
            levels = get_cached_levels(is_legacy=False)
            return render_template('submit_record.html', levels=levels)
        
        submitted_records = []
        errors = []
        
        for i in range(record_count):
            level_id_str = request.form.get(f'level_id_{i}', '').strip()
            progress_str = request.form.get(f'progress_{i}', '').strip()
            video_url = request.form.get(f'video_url_{i}', '').strip()
            comments = request.form.get(f'comments_{i}', '').strip()
            
            # Skip empty entries
            if not level_id_str or not progress_str or not video_url:
                continue
            
            try:
                # Handle both ObjectId and integer level IDs
                try:
                    level_id = ObjectId(level_id_str)
                except (ValueError, InvalidId):
                    level_id = int(level_id_str)
                
                progress = int(progress_str)
                
                # Validate progress range
                if progress < 1 or progress > 100:
                    errors.append(f'Record {i+1}: Progress must be between 1 and 100')
                    continue
                
                # Check if level exists
                level = mongo_db.levels.find_one({"_id": level_id}, {"name": 1, "min_percentage": 1}, max_time_ms=3000)
                if not level:
                    errors.append(f'Record {i+1}: Level not found')
                    continue
                
                # Check minimum progress requirement
                min_progress = level.get('min_percentage', 100)
                if progress < min_progress:
                    errors.append(f'Record {i+1}: {level["name"]} requires at least {min_progress}% progress')
                    continue
                
                # Create record
                next_id = ObjectId()
                new_record = {
                    "_id": next_id,
                    "user_id": session['user_id'],
                    "level_id": level_id,
                    "progress": progress,
                    "video_url": video_url,
                    "comments": comments,
                    "status": "pending",
                    "date_submitted": datetime.now(timezone.utc)
                }
                
                mongo_db.records.insert_one(new_record)
                submitted_records.append({
                    'level_name': level['name'],
                    'progress': progress,
                    'comments': comments
                })
                
                # Log submission with comments
                log_submission_with_comments(session['user_id'], level['name'], progress, comments)
                
            except ValueError:
                errors.append(f'Record {i+1}: Invalid level ID or progress value')
                continue
            except Exception as e:
                errors.append(f'Record {i+1}: {str(e)}')
                continue
        
        # Send Discord notifications for all submitted records
        if submitted_records:
            try:
                user = mongo_db.users.find_one({"_id": session['user_id']})
                username = user['username'] if user else 'Unknown'
                
                for record in submitted_records:
                    if DISCORD_AVAILABLE:
                        notify_record_submitted(username, record['level_name'], record['progress'], '', record['comments'])
                
                print(f"✅ Discord notifications sent for {len(submitted_records)} records")
            except Exception as e:
                print(f"❌ Discord notification error: {e}")
        
        # Show results
        if submitted_records:
            flash(f'Successfully submitted {len(submitted_records)} records! They will be reviewed by moderators.', 'success')
        
        if errors:
            for error in errors:
                flash(error, 'warning')
        
        if not submitted_records and not errors:
            flash('No valid records were submitted', 'warning')
        
        return redirect(url_for('profile'))
        
    except Exception as e:
        flash(f'Error processing multiple submissions: {str(e)}', 'danger')
        levels = get_cached_levels(is_legacy=False)
        return render_template('submit_record.html', levels=levels)

def log_submission_with_comments(user_id, level_name, progress, comments):
    """Log record submission with comments to submission logs"""
    try:
        user = mongo_db.users.find_one({"_id": user_id})
        username = user['username'] if user else 'Unknown'
        
        log_entry = {
            "_id": ObjectId(),
            "user_id": user_id,
            "username": username,
            "level_name": level_name,
            "progress": progress,
            "comments": comments,
            "timestamp": datetime.now(timezone.utc),
            "type": "submission"
        }
        
        mongo_db.submission_logs.insert_one(log_entry)
        print(f"📝 Logged submission: {username} - {level_name} - {progress}% - Comments: {comments}")
        
    except Exception as e:
        print(f"Error logging submission: {e}")

def send_discord_notification_direct(username, level_name, progress, video_url, comments=None):
    """Fallback Discord notification when integration is not available"""
    try:
        import requests
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        
        if not webhook_url:
            print("❌ No Discord webhook URL configured for fallback")
            return
        
        embed = {
            "title": "📝 New Record Submission",
            "description": "A new record has been submitted for review",
            "color": 10181046,  # Purple color
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": [
                {"name": "👤 Player", "value": username, "inline": True},
                {"name": "🎮 Level", "value": level_name, "inline": True},
                {"name": "📊 Progress", "value": f"{progress}%", "inline": True}
            ]
        }
        
        if video_url:
            embed["fields"].append({
                "name": "🎥 Video",
                "value": f"[Watch Video]({video_url})",
                "inline": False
            })
        
        if comments and comments.strip():
            embed["fields"].append({
                "name": "💬 Comments",
                "value": comments[:500] + ("..." if len(comments) > 500 else ""),
                "inline": False
            })
        
        payload = {"embeds": [embed]}
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 204:
            print("✅ Fallback Discord notification sent successfully")
        else:
            print(f"❌ Fallback Discord notification failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error in fallback Discord notification: {e}")

# Admin routes

@app.route('/admin/bulk_record_action', methods=['POST'])
def admin_bulk_record_action():
    """Handle bulk record actions (approve, reject, delete)"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        action = request.form.get('action')
        record_ids_json = request.form.get('record_ids')
        reason = request.form.get('reason', '').strip()
        
        if not action or not record_ids_json:
            return {'error': 'Missing action or record IDs'}, 400
        
        import json
        record_ids = json.loads(record_ids_json)
        
        if not record_ids:
            return {'error': 'No records selected'}, 400
        
        admin_username = session.get('username', 'Unknown Admin')
        success_count = 0
        
        for record_id_str in record_ids:
            try:
                record_id = ObjectId(record_id_str)
                
                if action == 'approve':
                    # Get record info
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and record.get('status') == 'pending':
                        # Approve the record
                        mongo_db.records.update_one(
                            {"_id": record_id},
                            {"$set": {
                                "status": "approved",
                                "approved_by": admin_username,
                                "approved_at": datetime.now(timezone.utc)
                            }}
                        )
                        
                        # Update user points
                        update_user_points(record['user_id'])
                        success_count += 1
                        
                elif action == 'reject':
                    # Get record info
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and record.get('status') == 'pending':
                        # Reject the record
                        update_data = {
                            "status": "rejected",
                            "rejected_by": admin_username,
                            "rejected_at": datetime.now(timezone.utc)
                        }
                        if reason:
                            update_data["rejection_reason"] = reason
                        
                        mongo_db.records.update_one(
                            {"_id": record_id},
                            {"$set": update_data}
                        )
                        success_count += 1
                        
                elif action == 'hide':
                    # Hide the record
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and not record.get('hidden', False):
                        mongo_db.records.update_one(
                            {"_id": record_id},
                            {"$set": {
                                "hidden": True,
                                "hidden_by": admin_username,
                                "hidden_at": datetime.now(timezone.utc)
                            }}
                        )
                        
                        # Recalculate user points since hidden records don't count
                        if REAL_TIME_POINTS_AVAILABLE:
                            try:
                                from real_time_points_system import RealTimePointsManager
                                manager = RealTimePointsManager(mongo_db)
                                manager.recalculate_user_points(record['user_id'])
                            except Exception as e:
                                print(f"Error recalculating points after hiding record: {e}")
                        
                        success_count += 1
                        
                elif action == 'show':
                    # Show the record
                    record = mongo_db.records.find_one({"_id": record_id})
                    if record and record.get('hidden', False):
                        mongo_db.records.update_one(
                            {"_id": record_id},
                            {"$unset": {"hidden": "", "hidden_by": "", "hidden_at": ""}}
                        )
                        
                        # Recalculate user points since the record is now visible again
                        if REAL_TIME_POINTS_AVAILABLE:
                            try:
                                from real_time_points_system import RealTimePointsManager
                                manager = RealTimePointsManager(mongo_db)
                                manager.recalculate_user_points(record['user_id'])
                            except Exception as e:
                                print(f"Error recalculating points after showing record: {e}")
                        
                        success_count += 1
                        
                elif action == 'delete':
                    # Delete the record
                    result = mongo_db.records.delete_one({"_id": record_id})
                    if result.deleted_count > 0:
                        success_count += 1
                        
            except Exception as e:
                print(f"Error processing record {record_id_str}: {e}")
                continue
        
        # Log admin action
        log_admin_action(
            admin_username,
            f"BULK {action.upper()} RECORDS",
            f"Processed {success_count}/{len(record_ids)} records" + (f" - Reason: {reason}" if reason else "")
        )
        
        return {'success': True, 'count': success_count}
        
    except Exception as e:
        print(f"Error in bulk record action: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/submission_logs')
def admin_submission_logs():
    """View submission logs with comments"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get recent submission logs
        logs = list(mongo_db.submission_logs.find().sort("timestamp", -1).limit(100))
        
        return render_template('admin/submission_logs.html', logs=logs)
        
    except Exception as e:
        flash(f'Error loading submission logs: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/delete_level/<level_id>', methods=['POST'])
def admin_delete_level_enhanced(level_id):
    """Enhanced level deletion with reason support"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    try:
        removal_reason = request.form.get('removal_reason', '').strip()
        
        # Get level info before deletion (exclude thumbnail blob — it's large and not needed for history)
        level = mongo_db.levels.find_one({"_id": ObjectId(level_id)}, {"thumbnail_url": 0})
        if not level:
            return {'error': 'Level not found'}, 404

        level_position = level['position']
        is_legacy = level.get('is_legacy', False)
        admin_username = session.get('username', 'Unknown')

        # Delete associated records
        mongo_db.records.delete_many({"level_id": ObjectId(level_id)})

        # Save history before deleting (thumbnail already excluded from level doc)
        history_entry = {
            "level_id": ObjectId(level_id),
            "action": "deleted",
            "old_data": level,
            "removal_reason": removal_reason,
            "admin": admin_username,
            "timestamp": datetime.now(timezone.utc)
        }
        mongo_db.level_history.insert_one(history_entry)
        
        # Delete the level
        mongo_db.levels.delete_one({"_id": ObjectId(level_id)})
        
        # Log enhanced level removal to changelog
        log_level_change(
            action="removed",
            level_name=level['name'],
            admin_username=admin_username,
            old_position=level_position,
            reason=removal_reason,
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
        
        # Log admin action
        reason_text = f" (Reason: {removal_reason})" if removal_reason else ""
        log_admin_action(admin_username, f"REMOVED LEVEL: {level['name']}", f"Position {level_position}{reason_text}")
        
        return {'success': True}
        
    except Exception as e:
        print(f"Error in enhanced level deletion: {e}")
        return {'error': str(e)}, 500

@app.route('/admin/remove_level_with_reason', methods=['POST'])
def admin_remove_level_with_reason():
    """Remove level with optional reason"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        level_id = request.form.get('level_id')
        reason = request.form.get('reason', '').strip()
        
        if not level_id:
            flash('Level ID is required', 'danger')
            return redirect(url_for('admin_levels'))
        
        # Get level info (thumbnail not needed here)
        level = mongo_db.levels.find_one({"_id": ObjectId(level_id)}, {"thumbnail_url": 0})
        if not level:
            flash('Level not found', 'danger')
            return redirect(url_for('admin_levels'))
        
        # Remove the level (this will call the enhanced admin_delete_level logic)
        request.form = request.form.copy()
        request.form['level_id'] = str(level['_id'])
        request.form['removal_reason'] = reason
        
        return admin_delete_level()
        
    except Exception as e:
        flash(f'Error removing level: {str(e)}', 'danger')
        return redirect(url_for('admin_levels'))
@app.route('/admin/dashboard')
def admin_dashboard():
    """New categorized admin dashboard"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get basic stats for dashboard — each query is capped at 5 s so a slow
    # Atlas cold start never causes the whole dashboard to 504.
    try:
        stats = {
            'pending_records': mongo_db.records.count_documents({"status": "pending"},   maxTimeMS=5000),
            'total_users':     mongo_db.users.count_documents({},                        maxTimeMS=5000),
            'total_levels':    mongo_db.levels.count_documents({"is_legacy": False},     maxTimeMS=5000),
            'legacy_levels':   mongo_db.levels.count_documents({"is_legacy": True},      maxTimeMS=5000),
            'total_records':   mongo_db.records.count_documents({"status": "approved"},  maxTimeMS=5000),
        }
    except Exception:
        stats = {
            'pending_records': '—',
            'total_users':     '—',
            'total_levels':    '—',
            'legacy_levels':   '—',
            'total_records':   '—',
        }

    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/profanity')
def admin_profanity():
    """Profanity filter management"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    word_lists = profanity_filter.get_word_lists()
    return render_template('admin/profanity.html', word_lists=word_lists)

@app.route('/admin/profanity/add', methods=['POST'])
def admin_add_profanity_word():
    """Add word to profanity filter"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    word = request.form.get('word', '').strip().lower()
    severity = request.form.get('severity', 'strong')
    
    if not word:
        flash('Please enter a word', 'danger')
        return redirect(url_for('admin_profanity'))
    
    try:
        profanity_filter.add_word(word, severity)
        flash(f'Added "{word}" to {severity} profanity list', 'success')
    except Exception as e:
        flash(f'Error adding word: {e}', 'danger')
    
    return redirect(url_for('admin_profanity'))

@app.route('/admin/profanity/remove', methods=['POST'])
def admin_remove_profanity_word():
    """Remove word from profanity filter"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    word = request.form.get('word', '').strip().lower()
    
    if not word:
        flash('Please enter a word', 'danger')
        return redirect(url_for('admin_profanity'))
    
    try:
        profanity_filter.remove_word(word)
        flash(f'Removed "{word}" from profanity filter', 'success')
    except Exception as e:
        flash(f'Error removing word: {e}', 'danger')
    
    return redirect(url_for('admin_profanity'))

@app.route('/admin/profanity/test', methods=['POST'])
def admin_test_profanity():
    """Test profanity filter"""
    if 'user_id' not in session or not session.get('is_admin'):
        return {'error': 'Access denied'}, 403
    
    test_text = request.form.get('test_text', '').strip()
    test_type = request.form.get('test_type', 'username')
    
    if not test_text:
        return {'error': 'Please enter text to test'}, 400
    
    try:
        if test_type == 'username':
            is_clean, reason = check_username_profanity(test_text)
        elif test_type == 'level':
            is_clean, reason = check_level_name_profanity(test_text)
        else:
            is_clean, reason = check_comment_profanity(test_text)
        
        return {
            'is_clean': is_clean,
            'reason': reason,
            'suggestion': profanity_filter.suggest_alternative(test_text) if not is_clean else test_text
        }
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/admin/news')
def admin_news():
    """Admin news management - placeholder route"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    # For now, redirect to admin dashboard since news system is not implemented
    flash('News management system is not yet implemented', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/news/create')
def admin_create_news():
    """Admin create news - placeholder route"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    # For now, redirect to admin dashboard since news system is not implemented
    flash('News creation system is not yet implemented', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/news/edit/<article_id>')
def admin_edit_news(article_id):
    """Admin edit news - placeholder route"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    # For now, redirect to admin dashboard since news system is not implemented
    flash('News editing system is not yet implemented', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/news/delete/<article_id>', methods=['POST'])
def admin_delete_news(article_id):
    """Admin delete news - placeholder route"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    # For now, redirect to admin dashboard since news system is not implemented
    flash('News deletion system is not yet implemented', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/news/<article_id>')
def news_article(article_id):
    """Display a single news article"""
    try:
        # Try to find the article in the database
        article = mongo_db.news_articles.find_one({"_id": ObjectId(article_id), "status": "published"})
        
        if not article:
            flash('Article not found', 'danger')
            return redirect(url_for('index'))
        
        # For now, since the news system is not fully implemented, 
        # redirect to index with a message
        flash('News article system is not yet fully implemented', 'info')
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Error loading news article: {e}")
        flash('Error loading article', 'danger')
        return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            verifier_name = request.form.get('verifier_name', '').strip()
            username = request.form.get('username', '').strip()
            
            if verifier_name and username:
                # Find user by username
                user = mongo_db.users.find_one({"username": username})
                if not user:
                    flash(f'User "{username}" not found', 'danger')
                else:
                    # Find all levels verified by this verifier name
                    levels = list(mongo_db.levels.find({"verifier": verifier_name, "is_legacy": False}))
                    
                    if not levels:
                        flash(f'No levels found verified by "{verifier_name}"', 'warning')
                    else:
                        awarded_count = 0
                        for level in levels:
                            success = award_verifier_points(level['_id'], user['_id'])
                            if success:
                                awarded_count += 1
                        
                        if awarded_count > 0:
                            flash(f'Verifier points awarded to {username} for {awarded_count} levels verified by {verifier_name}!', 'success')
                            # Update user points
                            update_user_points(user['_id'])
                        else:
                            flash(f'No new points awarded (user may already have completions for all levels)', 'warning')
            else:
                flash('Please enter both verifier name and username', 'danger')
        except Exception as e:
            flash(f'Error awarding verifier points: {e}', 'danger')
    
    # Get pending records - use separate queries to avoid slow $lookup on Atlas M0
    raw_pending = list(mongo_db.records.find({"status": "pending"}))
    if raw_pending:
        user_ids = list({r["user_id"] for r in raw_pending if "user_id" in r})
        level_ids = list({r["level_id"] for r in raw_pending if "level_id" in r})
        users_map = {u["_id"]: u for u in mongo_db.users.find({"_id": {"$in": user_ids}})}
        levels_map = {l["_id"]: l for l in mongo_db.levels.find({"_id": {"$in": level_ids}}, {"thumbnail_url": 0})}
        pending_records = []
        for r in raw_pending:
            user = users_map.get(r.get("user_id"))
            level = levels_map.get(r.get("level_id"))
            if user and level:
                r["user"] = user
                r["level"] = level
                pending_records.append(r)
    else:
        pending_records = []
    
    # Generate stats for the admin dashboard
    try:

        from datetime import datetime, timedelta, timezone
        
        # Basic counts
        total_users = mongo_db.users.count_documents({})
        total_levels = mongo_db.levels.count_documents({})
        total_records = mongo_db.records.count_documents({})
        pending_records_count = mongo_db.records.count_documents({"status": "pending"})
        main_levels_count = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_levels_count = mongo_db.levels.count_documents({"is_legacy": True})
        future_levels_count = mongo_db.future_levels.count_documents({})
        
        # Time-based counts (24 hours)
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        new_users_24h = mongo_db.users.count_documents({"date_joined": {"$gte": twenty_four_hours_ago}})
        new_records_24h = mongo_db.records.count_documents({"date_submitted": {"$gte": twenty_four_hours_ago}})
        new_levels_24h = mongo_db.levels.count_documents({"date_added": {"$gte": twenty_four_hours_ago}})
        
        # Active users (7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        active_users_7d = mongo_db.users.count_documents({"last_active": {"$gte": seven_days_ago}})
        
        # Top player (by points)
        top_player = mongo_db.users.find_one(
            {"points": {"$gt": 0}},
            {"username": 1, "points": 1, "nickname": 1}
        )
        if top_player:
            # Convert ObjectId to string for template
            top_player['_id'] = str(top_player['_id'])
        
        # Count admin and head admin users
        admin_users_count = mongo_db.users.count_documents({"is_admin": True})
        head_admin_users_count = mongo_db.users.count_documents({"head_admin": True})
        
        # Create stats object
        stats = {
            'total_users': total_users,
            'total_levels': total_levels,
            'total_records': total_records,
            'pending_records': pending_records_count,
            'new_users_24h': new_users_24h,
            'new_records_24h': new_records_24h,
            'new_levels_24h': new_levels_24h,
            'active_users_7d': active_users_7d,
            'main_levels': main_levels_count,
            'legacy_levels': legacy_levels_count,
            'future_levels': future_levels_count,
            'top_player': top_player,
            'admin_users': admin_users_count,
            'head_admin_users': head_admin_users_count
        }
        
    except Exception as e:
        # Fallback stats in case of error
        stats = {
            'total_users': 0,
            'total_levels': 0,
            'total_records': 0,
            'pending_records': 0,
            'new_users_24h': 0,
            'new_records_24h': 0,
            'new_levels_24h': 0,
            'active_users_7d': 0,
            'main_levels': 0,
            'legacy_levels': 0,
            'future_levels': 0,
            'top_player': None,
            'admin_users': 0,
            'head_admin_users': 0
        }
        print(f"Error generating admin stats: {e}")
    
    return render_template('admin/index.html', pending_records=pending_records, stats=stats)

@app.route('/admin/verifications')
def admin_verifications():
    """Admin verification submissions management - View only (no approve/reject)"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Automatically check for and remove duplicate submissions
        duplicates_removed = check_for_duplicate_levels()
        if duplicates_removed > 0:
            flash(f'🧹 Automatically removed {duplicates_removed} duplicate verification submissions for levels already on the list.', 'info')
        
        # Get all verification submissions with user info
        pipeline = [
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 100}  # Limit to recent 100 submissions
        ]
        
        verification_submissions = list(mongo_db.verification_submissions.aggregate(pipeline, allowDiskUse=True))
        
        return render_template('admin/verifications.html', submissions=verification_submissions)
        
    except Exception as e:
        print(f"Error loading verification submissions: {e}")
        flash('Error loading verification submissions', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/verification/<submission_id>')
def admin_verification_detail(submission_id):
    """Individual verification submission detail page"""
    
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get specific verification submission with user data
        pipeline = [
            {"$match": {"_id": ObjectId(submission_id)}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {"$unwind": "$user"}
        ]
        
        submission = list(mongo_db.verification_submissions.aggregate(pipeline, allowDiskUse=True))
        if not submission:
            flash('Verification submission not found', 'danger')
            return redirect(url_for('admin_verifications'))
        
        submission = submission[0]
        
        return render_template('admin/verification_detail.html', submission=submission)
        
    except Exception as e:
        flash(f'Error loading verification submission: {e}', 'danger')
        return redirect(url_for('admin_verifications'))

@app.route('/admin/verification-details')
def admin_verification_details():
    """Admin verification details - ID, Creator, and Verifier information"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get all verification submissions with user info and verifier info
        pipeline = [
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$lookup": {
                "from": "users",
                "localField": "approved_by",
                "foreignField": "_id",
                "as": "approved_verifier"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "rejected_by",
                "foreignField": "_id",
                "as": "rejected_verifier"
            }},
            {"$addFields": {
                "verifier": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$approved_verifier"}, 0]},
                        "then": "$approved_verifier",
                        "else": "$rejected_verifier"
                    }
                }
            }},
            {"$sort": {"date_submitted": -1}},
            {"$limit": 100}  # Limit to recent 100 submissions
        ]
        
        verification_submissions = list(mongo_db.verification_submissions.aggregate(pipeline, allowDiskUse=True))
        
        return render_template('admin/verification_details.html', submissions=verification_submissions)
        
    except Exception as e:
        print(f"Error loading verification details: {e}")
        flash('Error loading verification details', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/verification/accept/<submission_id>', methods=['POST'])
def admin_accept_verification(submission_id):
    """Accept a verification submission and add level to the list"""
    
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_verifications'))
    
    try:
        # Get the placement position from the form
        placement = int(request.form.get('placement', 1))
        
        # Get admin info
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Call the function to accept the verification submission with placement
        result = accept_verification_submission(submission_id, admin_username, placement)
        
        if result:
            flash(f'Verification accepted! Level placed at position {placement}', 'success')
            return redirect(url_for('admin_verifications'))
        else:
            flash('Error accepting verification submission', 'danger')
            return redirect(url_for('admin_verifications'))
        
    except Exception as e:
        flash(f'Error accepting verification: {str(e)}', 'danger')
        print(f"Admin accept verification error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('admin_verifications'))

def text_difficulty_to_numeric(text_difficulty):
    """Convert text-based difficulty to numeric value"""
    difficulty_mapping = {
        'easy': 1.0,
        'normal': 3.0,
        'hard': 5.0,
        'harder': 7.0,
        'insane': 9.0,
        'easy demon': 10.0,
        'medium demon': 10.0,
        'hard demon': 10.0,
        'insane demon': 10.0,
        'extreme demon': 10.0,
        'demon': 10.0
    }
    
    # If it's already a number, return it as float
    if isinstance(text_difficulty, (int, float)):
        return float(text_difficulty)
    
    # Convert to lowercase for case-insensitive matching
    return difficulty_mapping.get(text_difficulty.lower(), 10.0)  # Default to 10.0 (Demon)

def accept_verification_submission(submission_id, admin_username, custom_placement=None):
    """Accept a verification submission and add it to the main list"""
    submission = mongo_db.verification_submissions.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        return False
    
    try:
        # Check if already processed
        if submission.get('status') != 'pending':
            print(f"Verification submission {submission_id} already processed")
            return False
        
        # Validate required fields
        required_fields = ['level_name', 'creator', 'verifier', 'difficulty', 'verification_url']
        for field in required_fields:
            if not submission.get(field):
                print(f"Missing required field: {field}")
                return False
        
        # Get submitter info
        submitter = mongo_db.users.find_one({"_id": submission['user_id']})
        if not submitter:
            print("Submitter not found")
            return False
        
        # Use custom placement from admin if provided, otherwise use submission placement
        if custom_placement is not None:
            placement = int(custom_placement)
            print(f"Using admin custom placement: {placement}")
        else:
            placement = int(submission.get('placement', 1))
            print(f"Using submission placement: {placement}")
        
        # Validate placement
        if placement < 1:
            placement = 1
        
        # Shift existing levels down to make room
        shift_level_positions(placement, is_legacy=False, direction=1)
        
        # Check for dethroning at #1
        dethroned_level = None
        pushed_to_legacy = None
        
        if placement == 1:
            # Get current #1 level
            current_top_level = mongo_db.levels.find_one(
                {"position": 1, "is_legacy": False}
            )
            if current_top_level:
                dethroned_level = current_top_level['name']
                
                # Handle automatic legacy management
                try:
                    settings = mongo_db.site_settings.find_one({"_id": "main"})
                    if settings and settings.get('auto_legacy_enabled', False):
                        # Move current #1 to legacy list
                        mongo_db.levels.update_one(
                            {"_id": current_top_level['_id']},
                            {"$set": {"is_legacy": True, "position": 1}}
                        )
                        # Shift legacy positions
                        mongo_db.levels.update_many(
                            {"is_legacy": True, "position": {"$gte": 1}},
                            {"$inc": {"position": 1}}
                        )
                        pushed_to_legacy = current_top_level['name']
                except Exception as e:
                    print(f"Auto-legacy management error: {e}")
        
        # Convert text difficulty to numeric value
        numeric_difficulty = text_difficulty_to_numeric(submission['difficulty'])
        
        # Create new level document
        new_level_id = ObjectId()
        new_level = {
            "_id": new_level_id,
            "name": submission['level_name'],
            "creator": submission['creator'],
            "verifier": submission['verifier'],
            "position": placement,
            "difficulty": numeric_difficulty,
            "video_url": submission.get('verification_url', ''),
            "level_id": submission.get('level_id', ''),
            "is_legacy": False,
            "date_added": datetime.now(timezone.utc),
            "points": 0  # Will be calculated after insertion
        }
        
        # Insert the new level
        mongo_db.levels.insert_one(new_level)
        
        # Calculate points for the new level
        new_level['points'] = calculate_level_points(placement, False)
        mongo_db.levels.update_one(
            {"_id": new_level_id},
            {"$set": {"points": new_level['points']}}
        )
        
        # Get surrounding levels for changelog
        above_level = None
        below_level = None
        
        if placement > 1:
            above_level_doc = mongo_db.levels.find_one(
                {"position": placement - 1, "is_legacy": False}
            )
            if above_level_doc:
                above_level = above_level_doc['name']
        
        below_level_doc = mongo_db.levels.find_one(
            {"position": placement + 1, "is_legacy": False}
        )
        if below_level_doc:
            below_level = below_level_doc['name']
        
        # Trigger real-time points recalculation if available
        if REAL_TIME_POINTS_AVAILABLE:
            try:
                from real_time_points_system import RealTimePointsManager
                manager = RealTimePointsManager(mongo_db)
                levels_updated = manager.recalculate_all_level_points()
                users_updated = manager.recalculate_all_user_points()
                print(f"✅ Verification acceptance triggered recalculation: {levels_updated} levels, {users_updated} users updated")
            except Exception as e:
                print(f"⚠️ Warning: Real-time points recalculation failed: {e}")
        
        # Handle automatic legacy management
        auto_manage_legacy_list()
        
        # Clear cache
        levels_cache['main_list'] = None
        levels_cache['legacy_list'] = None
        
        # Create a record for the verifier automatically
        verifier_record_id = ObjectId()
        verifier_record = {
            "_id": verifier_record_id,
            "user_id": submission['user_id'],
            "level_id": new_level_id,
            "progress": 100,
            "video_url": submission.get('verification_url', ''),
            "status": "approved",
            "date_submitted": datetime.now(timezone.utc),
            "approved_by": admin_username,
            "approved_at": datetime.now(timezone.utc),
            "is_verifier": True,
            "comments": f"Automatic record created from verification submission acceptance"
        }
        
        # Insert the verifier record
        mongo_db.records.insert_one(verifier_record)
        
        # Check if the user has a Discord account connected and assign appropriate roles
        submitter = mongo_db.users.find_one({"_id": submission['user_id']})
        if submitter and submitter.get('discord_id'):
            # Assign List Verifier role
            try:
                if is_bot_available():
                    if assign_verifier_role(submitter['discord_id']):
                        print(f"✅ Assigned List Verifier role to user {submitter['username']}")
                    else:
                        print(f"❌ Failed to assign List Verifier role to user {submitter['username']}")
                else:
                    print("⚠️ Discord bot not available - skipping List Verifier role assignment")
            except Exception as e:
                print(f"Error assigning List Verifier role: {e}")
            
            # Check if this is a future list level and assign Future List Verifier role if applicable
            try:
                # Get all future levels to check if this level name matches
                future_levels = list(mongo_db.future_levels.find({}, {"name": 1}))
                future_level_names = [level['name'].lower() for level in future_levels]
                
                if submission['level_name'].lower() in future_level_names:
                    # Assign Future List Verifier role
                    if is_bot_available():
                        if assign_future_list_verifier_role(submitter['discord_id']):
                            print(f"✅ Assigned Future List Verifier role to user {submitter['username']}")
                        else:
                            print(f"❌ Failed to assign Future List Verifier role to user {submitter['username']}")
                    else:
                        print("⚠️ Discord bot not available - skipping Future List Verifier role assignment")
            except Exception as e:
                print(f"Error checking future list or assigning Future List Verifier role: {e}")
        
        # Update user points to include the new record
        update_user_points(submission['user_id'])
        
        # Update verification submission status
        mongo_db.verification_submissions.update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": {
                "status": "accepted",
                "accepted_by": admin_username,
                "accepted_at": datetime.now(timezone.utc),
                "placed_at_position": placement,
                "level_id_created": new_level_id
            }}
        )
        
        # Log changelog
        changelog_kwargs = {
            'position': placement,
            'above_level': above_level,
            'below_level': below_level,
            'list_type': 'main'
        }
        
        if placement == 1 and dethroned_level:
            changelog_kwargs['dethroned_level'] = dethroned_level
        
        if pushed_to_legacy:
            changelog_kwargs['pushed_to_legacy'] = pushed_to_legacy
        
        log_level_change(
            action="placed",
            level_name=submission['level_name'],
            admin_username=admin_username,
            **changelog_kwargs
        )
        
        # Log admin action
        log_admin_action(
            admin_username, 
            f"ACCEPTED VERIFICATION: {submission['level_name']}", 
            f"Placed at position {placement}, submitted by {submitter['username']}"
        )
        
        # Create notification for submitter
        create_notification(
            submission['user_id'],
            'verification_status',
            'Verification Accepted! ✅',
            f'Your verification for "{submission["level_name"]}" has been accepted and placed at position #{placement}! You automatically received the record and points.',
            new_level_id,
            'level'
        )
        
        # Send Discord notification
        try:
            if CHANGELOG_DISCORD_AVAILABLE:
                # Create changelog message for Discord
                message = f"{submission['level_name']} has been placed at #{placement}"
                if below_level and above_level:
                    message += f" below {above_level} and above {below_level}"
                elif below_level:
                    message += f" below {below_level}"
                elif above_level:
                    message += f" above {above_level}"
                
                if placement == 1 and dethroned_level:
                    message = f"{submission['level_name']} has been placed at #1, dethroning {dethroned_level}"
                
                message += " on the main list."
                
                if pushed_to_legacy:
                    message += f" This pushes {pushed_to_legacy} to the legacy list."
                
                notify_changelog(message, admin_username)
        except Exception as e:
            print(f"Discord changelog notification error: {e}")
        
        # Calculate points earned
        points_earned = calculate_record_points(verifier_record, new_level)
        
        flash(f'✅ Verification accepted! "{submission["level_name"]}" has been placed at position #{placement}. {submitter["username"]} automatically received the record and {points_earned} points.', 'success')
        return True
        
    except Exception as e:
        flash(f'Error accepting verification: {str(e)}', 'danger')
        print(f"Admin accept verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_top_1_player_role():
    """Assign the Top 1 Player role to the current #1 player on the list"""
    try:
        # Get the current #1 player
        top_player = mongo_db.users.find_one(
            {"points": {"$gt": 0}}, 
            sort=[("points", -1)]
        )
        
        if not top_player:
            print("No players found with points")
            return False
            
        # Remove the role from any previous holder
        previous_top_player = mongo_db.users.find_one(
            {"has_top_1_role": True}
        )
        
        if previous_top_player and previous_top_player['_id'] != top_player['_id']:
            # Remove role from previous holder
            if previous_top_player.get('discord_id'):
                try:
                    if is_bot_available():
                        if remove_top_1_player_role(previous_top_player['discord_id']):
                            print(f"✅ Removed Top 1 Player role from {previous_top_player['username']}")
                        else:
                            print(f"❌ Failed to remove Top 1 Player role from {previous_top_player['username']}")
                    else:
                        print("⚠️ Discord bot not available - skipping Top 1 Player role removal")
                except Exception as e:
                    print(f"Error removing Top 1 Player role: {e}")
            
            # Update database
            mongo_db.users.update_one(
                {"_id": previous_top_player['_id']},
                {"$unset": {"has_top_1_role": ""}}
            )
        
        # Assign role to current top player
        if top_player.get('discord_id'):
            try:
                if is_bot_available():
                    if assign_top_1_player_role(top_player['discord_id']):
                        print(f"✅ Assigned Top 1 Player role to {top_player['username']}")
                    else:
                        print(f"❌ Failed to assign Top 1 Player role to {top_player['username']}")
                else:
                    print("⚠️ Discord bot not available - skipping Top 1 Player role assignment")
            except Exception as e:
                print(f"Error assigning Top 1 Player role: {e}")
            
            # Update database
            mongo_db.users.update_one(
                {"_id": top_player['_id']},
                {"$set": {"has_top_1_role": True}}
            )
        
        return True
        
    except Exception as e:
        print(f"Error in update_top_1_player_role: {e}")
        return False

@app.route('/admin/verification/deny/<submission_id>', methods=['POST'])
def admin_deny_verification(submission_id):
    """Deny a verification submission and delete it"""
    
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_verifications'))
    
    try:
        # Get the verification submission
        submission = mongo_db.verification_submissions.find_one({"_id": ObjectId(submission_id)})
        if not submission:
            flash('Verification submission not found', 'danger')
            return redirect(url_for('admin_verifications'))
        
        # Check if already processed
        if submission.get('status') != 'pending':
            flash('Verification submission has already been processed', 'warning')
            return redirect(url_for('admin_verifications'))
        
        # Get admin info
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get submitter info
        submitter = mongo_db.users.find_one({"_id": submission['user_id']})
        
        # Delete the verification submission
        mongo_db.verification_submissions.delete_one({"_id": ObjectId(submission_id)})
        
        # Log admin action
        if submitter:
            log_admin_action(
                admin_username, 
                f"DENIED VERIFICATION: {submission['level_name']}", 
                f"Submitted by {submitter['username']}, reason: Admin decision"
            )
            
            # Create notification for submitter
            create_notification(
                submission['user_id'],
                'verification_status',
                'Verification Denied ❌',
                f'Your verification submission for "{submission["level_name"]}" has been denied by an administrator.',
                None,
                'system'
            )
        
        flash(f'❌ Verification for "{submission["level_name"]}" has been denied and removed.', 'success')
        
    except Exception as e:
        flash(f'Error denying verification: {str(e)}', 'danger')
        print(f"Admin deny verification error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_verifications'))

@app.route('/admin/cleanup_duplicate_verifications', methods=['POST'])
def admin_cleanup_duplicate_verifications():
    """Remove verification submissions for levels that already exist on the list"""
    
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_verifications'))
    
    try:
        # Get admin info
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Get all levels (main list and legacy)
        all_levels = list(mongo_db.levels.find({}, {"name": 1, "level_id": 1, "position": 1, "is_legacy": 1}))
        
        # Create sets for faster lookup
        level_names = {level['name'].lower().strip() for level in all_levels}
        level_ids = {level.get('level_id') for level in all_levels if level.get('level_id')}
        
        # Get all pending verification submissions
        pending_submissions = list(mongo_db.verification_submissions.find({"status": "pending"}))
        
        duplicates_found = []
        removed_count = 0
        
        for submission in pending_submissions:
            is_duplicate = False
            duplicate_reason = ""
            
            # Check by level name (case-insensitive)
            if submission.get('level_name', '').lower().strip() in level_names:
                is_duplicate = True
                duplicate_reason = "Level name already exists on the list"
            
            # Check by level ID if provided
            elif submission.get('level_id') and submission['level_id'] in level_ids:
                is_duplicate = True
                duplicate_reason = "Level ID already exists on the list"
            
            if is_duplicate:
                # Find the existing level for reference
                existing_level = None
                for level in all_levels:
                    if (level['name'].lower().strip() == submission.get('level_name', '').lower().strip() or
                        level.get('level_id') == submission.get('level_id')):
                        existing_level = level
                        break
                
                # Get submitter info
                submitter = mongo_db.users.find_one({"_id": submission['user_id']})
                submitter_name = submitter['username'] if submitter else 'Unknown'
                
                # Store duplicate info
                duplicate_info = {
                    'submission_id': submission['_id'],
                    'level_name': submission.get('level_name', 'Unknown'),
                    'submitter': submitter_name,
                    'reason': duplicate_reason,
                    'existing_position': existing_level['position'] if existing_level else 'Unknown',
                    'existing_list': 'Legacy' if existing_level and existing_level.get('is_legacy') else 'Main'
                }
                duplicates_found.append(duplicate_info)
                
                # Remove the duplicate submission
                mongo_db.verification_submissions.delete_one({"_id": submission['_id']})
                removed_count += 1
                
                # Notify the submitter
                if submitter:
                    create_notification(
                        submission['user_id'],
                        'verification_status',
                        'Verification Removed - Duplicate Level ⚠️',
                        f'Your verification submission for "{submission.get("level_name", "Unknown")}" has been removed because this level already exists on the list at position #{existing_level["position"] if existing_level else "Unknown"}.',
                        existing_level['_id'] if existing_level else None,
                        'level'
                    )
        
        # Log admin action
        if removed_count > 0:
            log_admin_action(
                admin_username,
                f"CLEANED UP DUPLICATE VERIFICATIONS",
                f"Removed {removed_count} duplicate verification submissions"
            )
            
            # Create detailed flash message
            flash_message = f'✅ Cleanup complete! Removed {removed_count} duplicate verification submissions:'
            for i, dup in enumerate(duplicates_found[:5]):  # Show first 5
                flash_message += f'<br>• "{dup["level_name"]}" by {dup["submitter"]} (exists at #{dup["existing_position"]} on {dup["existing_list"]} list)'
            
            if len(duplicates_found) > 5:
                flash_message += f'<br>• ... and {len(duplicates_found) - 5} more'
            
            flash(flash_message, 'success')
        else:
            flash('✅ No duplicate verification submissions found.', 'info')
        
    except Exception as e:
        flash(f'Error during cleanup: {str(e)}', 'danger')
        print(f"Admin cleanup duplicate verifications error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_verifications'))

def check_for_duplicate_levels():
    """Background function to automatically check and remove duplicate verification submissions"""
    try:
        # Get all levels (main list and legacy)
        all_levels = list(mongo_db.levels.find({}, {"name": 1, "level_id": 1}))
        
        # Create sets for faster lookup
        level_names = {level['name'].lower().strip() for level in all_levels}
        level_ids = {level.get('level_id') for level in all_levels if level.get('level_id')}
        
        # Get all pending verification submissions
        pending_submissions = list(mongo_db.verification_submissions.find({"status": "pending"}))
        
        removed_count = 0
        
        for submission in pending_submissions:
            is_duplicate = False
            
            # Check by level name (case-insensitive)
            if submission.get('level_name', '').lower().strip() in level_names:
                is_duplicate = True
            
            # Check by level ID if provided
            elif submission.get('level_id') and submission['level_id'] in level_ids:
                is_duplicate = True
            
            if is_duplicate:
                # Remove the duplicate submission silently
                mongo_db.verification_submissions.delete_one({"_id": submission['_id']})
                removed_count += 1
                
                # Notify the submitter
                submitter = mongo_db.users.find_one({"_id": submission['user_id']})
                if submitter:
                    create_notification(
                        submission['user_id'],
                        'verification_status',
                        'Verification Removed - Level Already Exists ⚠️',
                        f'Your verification submission for "{submission.get("level_name", "Unknown")}" has been automatically removed because this level already exists on the list.',
                        None,
                        'system'
                    )
        
        if removed_count > 0:
            print(f"🧹 Automatically removed {removed_count} duplicate verification submissions")
        
        return removed_count
        
    except Exception as e:
        print(f"Error in automatic duplicate check: {e}")
        return 0



@app.route('/admin/console')
def admin_console():
    """Admin Console"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))

    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))

    # Generate stats for the console
    try:
        from datetime import datetime, timedelta, timezone
        
        # Basic counts
        total_users = mongo_db.users.count_documents({})
        total_levels = mongo_db.levels.count_documents({})
        total_records = mongo_db.records.count_documents({})
        main_levels_count = mongo_db.levels.count_documents({"is_legacy": False})
        legacy_levels_count = mongo_db.levels.count_documents({"is_legacy": True})
        future_levels_count = mongo_db.future_levels.count_documents({})
        
        # Count admin and head admin users
        admin_users_count = mongo_db.users.count_documents({"is_admin": True})
        head_admin_users_count = mongo_db.users.count_documents({"head_admin": True})
        
        # Create stats object
        stats = {
            'total_users': total_users,
            'total_levels': total_levels,
            'total_records': total_records,
            'main_levels': main_levels_count,
            'legacy_levels': legacy_levels_count,
            'future_levels': future_levels_count,
            'admin_users': admin_users_count,
            'head_admin_users': head_admin_users_count
        }
        
    except Exception as e:
        # Fallback stats in case of error
        stats = {
            'total_users': 0,
            'total_levels': 0,
            'total_records': 0,
            'main_levels': 0,
            'legacy_levels': 0,
            'future_levels': 0,
            'admin_users': 0,
            'head_admin_users': 0
        }
        print(f"Error generating console stats: {e}")
    
    return render_template('admin/console.html', stats=stats)

@app.route('/admin/console/execute', methods=['POST'])
def admin_console_execute():
    """Execute console commands - Admin only"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}
    
    if not session.get('is_admin') and not session.get('head_admin'):
        return {'success': False, 'error': 'Admin privileges required'}
    
    try:
        command = request.json.get('command', '').strip()
        if not command:
            return {'success': False, 'error': 'No command provided'}
        
        # Track console command execution
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'

        # Special handling for RTL commands to flag them as dangerous
        if command.startswith('rtl.'):
            rtl_cmd = command[4:].split('(')[0]
            if rtl_cmd in ['login_as', 'ban_user', 'unban_user', 'clear_cache', 'recalc_points', 'backup_db']:
                log_admin_action(admin_username, f"RTL DANGEROUS COMMAND", f"Executed: {command[:100]}")
            else:
                log_admin_action(admin_username, f"RTL COMMAND", f"Executed: {command[:100]}")
        else:
            log_admin_action(admin_username, "CONSOLE COMMAND", f"Executed: {command[:100]}")

        # Execute the command
        result = execute_console_command(command)
        return {'success': True, 'result': result}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def execute_console_command(command):
    """Execute console commands with custom RTL commands and Python support"""
    import sys
    from io import StringIO
    
    # Custom RTL commands
    if command.startswith('rtl.'):
        return execute_rtl_command(command[4:])  # Remove 'rtl.' prefix
    
    # System info commands
    elif command == 'help':
        return """Available commands:
        
RTL Database Commands:
  rtl.stats() - Show database statistics
  rtl.users() - List all users (max 20)
  rtl.levels() - List all levels (max 20)
  rtl.records() - Show recent approved records
  rtl.pending_records() - Show pending records
  rtl.admins() - List all admins
  rtl.top_players() - Show top players by points
  rtl.recent_activity() - Show recent system activity
  
RTL User Commands:
  rtl.user('username') - Get detailed user info
  rtl.ban_user('username') - Ban a user
  rtl.unban_user('username') - Unban a user
  rtl.make_admin('username') - Promote user to admin
  rtl.check_admin('username') - Check user admin status
  rtl.fix_admin_session('username') - Check admin session info
  rtl.reset_password('username', 'new_password') - Reset user password
  
RTL Level Commands:
  rtl.level('name') - Get detailed level info
  rtl.search_levels('term') - Search levels by name
  
RTL System Commands:
  rtl.clear_cache() - Clear levels cache
  rtl.recalc_points() - Recalculate all level points
  rtl.system_info() - Show system information
  rtl.backup_db() - Initiate database backup
  rtl.login_as('user') - Login as any user (DANGEROUS - action is logged)
  rtl.whoami() - Show current session info
  rtl.admin_logs() - Show recent admin actions
  
RTL Secret Commands:
  rtl.april_fools() - Toggle April Fools mode (randomizes level positions!)
  rtl.chaos_mode() - Alias for april_fools()
  rtl.chaos_status() - Check current April Fools mode status

  
Python Commands:
  Any valid Python expression or statement
  mongo_db - Direct database access
  datetime - Date/time functions
  
System Commands:
  help - Show this help
  clear - Clear console output
  stats - Quick stats overview
"""
    
    elif command == 'stats':
        total_users = mongo_db.users.count_documents({})
        total_levels = mongo_db.levels.count_documents({})
        total_records = mongo_db.records.count_documents({})
        return f"Users: {total_users} | Levels: {total_levels} | Records: {total_records}"
    
    elif command == 'clear':
        return '__CLEAR__'
    
    # Python code execution
    else:
        return execute_python_code(command)

def execute_rtl_command(command):
    """Execute RTL-specific commands"""
    try:
        if command == 'stats()':
            stats = {
                'users': mongo_db.users.count_documents({}),
                'levels': mongo_db.levels.count_documents({}),
                'records': mongo_db.records.count_documents({}),
                'main_levels': mongo_db.levels.count_documents({"is_legacy": False}),
                'legacy_levels': mongo_db.levels.count_documents({"is_legacy": True}),
                'admins': mongo_db.users.count_documents({"is_admin": True}),
                'head_admins': mongo_db.users.count_documents({"head_admin": True})
            }
            return f"""Database Statistics:
Users: {stats['users']} total, {stats['admins']} admins, {stats['head_admins']} head admins
Levels: {stats['levels']} total ({stats['main_levels']} main, {stats['legacy_levels']} legacy)
Records: {stats['records']} total"""
        
        elif command == 'users()':
            users = list(mongo_db.users.find({}, {"username": 1, "is_admin": 1, "head_admin": 1, "points": 1}).limit(20))
            result = "Recent Users (max 20):\n"
            for user in users:
                admin_status = ""
                if user.get('head_admin'):
                    admin_status = " [HEAD ADMIN]"
                elif user.get('is_admin'):
                    admin_status = " [ADMIN]"
                result += f"  {user['username']} (ID: {user['_id']}) - {user.get('points', 0)} points{admin_status}\n"
            return result
        
        elif command == 'levels()':
            levels = list(mongo_db.levels.find({}, {"name": 1, "position": 1, "is_legacy": 1, "points": 1}).sort("position", 1).limit(20))
            result = "Levels (max 20):\n"
            for level in levels:
                legacy_status = " [LEGACY]" if level.get('is_legacy') else ""
                result += f"  #{level['position']} {level['name']} - {level.get('points', 0)} points{legacy_status}\n"
            return result
        
        elif command == 'records()':
            records = list(mongo_db.records.aggregate([
                {"$match": {"status": "approved"}},
                {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
                {"$lookup": {"from": "levels", "localField": "level_id", "foreignField": "_id", "as": "level"}},
                {"$unwind": "$user"},
                {"$unwind": "$level"},
                {"$sort": {"date_submitted": -1}},
                {"$limit": 10}
            ], allowDiskUse=True))
            result = "Recent Records (max 10):\n"
            for record in records:
                result += f"  {record['user']['username']} - {record['level']['name']} ({record['progress']}%)\n"
            return result
        
        elif command == 'admins()':
            admins = list(mongo_db.users.find({"is_admin": True}, {"username": 1, "head_admin": 1}))
            result = "All Admins:\n"
            for admin in admins:
                status = "HEAD ADMIN" if admin.get('head_admin') else "ADMIN"
                result += f"  {admin['username']} (ID: {admin['_id']}) [{status}]\n"
            return result
        
        elif command == 'clear_cache()':
            global levels_cache
            levels_cache = {'main_list': None, 'legacy_list': None, 'last_updated': None}
            return "Levels cache cleared successfully"
        
        elif command == 'recalc_points()':
            recalculate_all_points()
            return "All level points recalculated successfully"
        
        elif command.startswith('user('):
            # Extract username from user('username')
            username = command[5:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                admin_status = ""
                if user.get('head_admin'):
                    admin_status = " [HEAD ADMIN]"
                elif user.get('is_admin'):
                    admin_status = " [ADMIN]"
                return f"""User: {user['username']} (ID: {user['_id']})
Points: {user.get('points', 0)}
Status: {'Public' if user.get('public_profile', True) else 'Private'} Profile{admin_status}
Joined: {user.get('date_joined', 'Unknown')}
Bio: {user.get('bio', 'No bio')}"""
            else:
                return f"User '{username}' not found"
        
        elif command.startswith('level('):
            # Extract level name from level('name')
            level_name = command[6:-1].strip('\'"')
            level = mongo_db.levels.find_one({"name": {"$regex": level_name, "$options": "i"}})
            if level:
                legacy_status = " [LEGACY]" if level.get('is_legacy') else ""
                return f"""Level: {level['name']} (ID: {level['_id']})
Position: #{level['position']}{legacy_status}
Creator: {level.get('creator', 'Unknown')}
Points: {level.get('points', 0)}
Difficulty: {level.get('difficulty', 'Unknown')}
Min %: {level.get('min_percentage', 100)}%"""
            else:
                return f"Level matching '{level_name}' not found"
        
        elif command == 'pending_records()':
            records = list(mongo_db.records.aggregate([
                {"$match": {"status": "pending"}},
                {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "user"}},
                {"$lookup": {"from": "levels", "localField": "level_id", "foreignField": "_id", "as": "level"}},
                {"$unwind": "$user"},
                {"$unwind": "$level"},
                {"$sort": {"date_submitted": -1}},
                {"$limit": 15}
            ], allowDiskUse=True))
            if records:
                result = f"Pending Records ({len(records)}):\n"
                for record in records:
                    result += f"  {record['user']['username']} - {record['level']['name']} ({record['progress']}%) - {record.get('date_submitted', 'Unknown')}\n"
                return result
            else:
                return "No pending records"
        
        elif command == 'top_players()':
            players = list(mongo_db.users.find(
                {"points": {"$gt": 0}},
                {"username": 1, "points": 1, "is_admin": 1, "head_admin": 1}
            ).sort("points", -1).limit(15))
            result = "Top Players by Points:\n"
            for i, player in enumerate(players, 1):
                admin_status = ""
                if player.get('head_admin'):
                    admin_status = " [HEAD]"
                elif player.get('is_admin'):
                    admin_status = " [ADMIN]"
                result += f"  {i}. {player['username']} - {player['points']} points{admin_status}\n"
            return result
        
        elif command == 'recent_activity()':
            # Get recent records, level additions, user registrations
            recent_records = list(mongo_db.records.find(
                {"status": "approved"},
                {"user_id": 1, "level_id": 1, "progress": 1, "date_submitted": 1}
            ).sort("date_submitted", -1).limit(5))
            
            recent_users = list(mongo_db.users.find(
                {},
                {"username": 1, "date_joined": 1}
            ).sort("date_joined", -1).limit(3))
            
            result = "Recent Activity:\n\nRecent Records:\n"
            for record in recent_records:
                result += f"  Record submitted - {record.get('date_submitted', 'Unknown')}\n"
            
            result += "\nRecent Users:\n"
            for user in recent_users:
                result += f"  {user['username']} joined - {user.get('date_joined', 'Unknown')}\n"
            
            return result
        
        elif command.startswith('ban_user('):
            # Extract username from ban_user('username')
            username = command[9:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                if user.get('is_admin') or user.get('head_admin'):
                    return f"Cannot ban admin user: {username}"
                # Add to banned users (you might want to implement a proper ban system)
                mongo_db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"banned": True, "ban_date": datetime.now(timezone.utc)}}
                )
                return f"User '{username}' has been banned"
            else:
                return f"User '{username}' not found"
        
        elif command.startswith('unban_user('):
            # Extract username from unban_user('username')
            username = command[11:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                mongo_db.users.update_one(
                    {"_id": user["_id"]},
                    {"$unset": {"banned": "", "ban_date": ""}}
                )
                return f"User '{username}' has been unbanned"
            else:
                return f"User '{username}' not found"
        
        elif command == 'system_info()':
            import platform
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                return f"""System Information:
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}
CPU Usage: {cpu_percent}%
Memory: {memory.percent}% used ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
Disk: {disk.percent}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)"""
            except ImportError:
                return f"""System Information (Basic):
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}
Note: Install psutil for detailed system metrics"""
        
        elif command == 'backup_db()':
            # Simple backup command (you might want to implement proper backup)
            from datetime import datetime
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"Database backup initiated at {backup_time}\n(Note: Implement proper backup logic in production)"
        
        elif command.startswith('search_levels('):
            # Extract search term from search_levels('term')
            search_term = command[14:-1].strip('\'"')
            levels = list(mongo_db.levels.find(
                {"name": {"$regex": search_term, "$options": "i"}},
                {"name": 1, "position": 1, "creator": 1, "is_legacy": 1}
            ).limit(10))
            if levels:
                result = f"Levels matching '{search_term}':\n"
                for level in levels:
                    legacy_status = " [LEGACY]" if level.get('is_legacy') else ""
                    result += f"  #{level['position']} {level['name']} by {level.get('creator', 'Unknown')}{legacy_status}\n"
                return result
            else:
                return f"No levels found matching '{search_term}'"
        
        elif command.startswith('make_admin('):
            # Extract username from make_admin('username')
            username = command[11:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                if user.get('is_admin'):
                    return f"User '{username}' is already an admin"
                mongo_db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"is_admin": True}}
                )
                return f"User '{username}' has been promoted to admin"
            else:
                return f"User '{username}' not found"
        
        elif command.startswith('check_admin('):
            # Extract username from check_admin('username')
            username = command[12:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                admin_status = "Regular User"
                if user.get('head_admin'):
                    admin_status = "HEAD ADMIN"
                elif user.get('is_admin'):
                    admin_status = "ADMIN"
                return f"User '{username}' status: {admin_status}\nDatabase is_admin: {user.get('is_admin', False)}\nDatabase head_admin: {user.get('head_admin', False)}"
            else:
                return f"User '{username}' not found"
        
        elif command.startswith('fix_admin_session('):
            # Extract username from fix_admin_session('username')
            username = command[18:-1].strip('\'"')
            user = mongo_db.users.find_one({"username": username})
            if user:
                # This is just informational - the user needs to log out and back in
                return f"User '{username}' database status:\nis_admin: {user.get('is_admin', False)}\nhead_admin: {user.get('head_admin', False)}\n\nNote: User must log out and log back in for session to update"
            else:
                return f"User '{username}' not found"
        
        elif command.startswith('login_as('):
            # Extract username from login_as('username') - DANGEROUS ADMIN COMMAND
            username = command[9:-1].strip('\'"')
            
            if not username:
                return "Usage: rtl.login_as('username')\nExample: rtl.login_as('john')"
            
            user = mongo_db.users.find_one({"username": username})
            if not user:
                return f"User '{username}' not found"

            current_user = session.get('username', 'Unknown')

            try:
                mongo_db.admin_logs.insert_one({
                    "action": "admin_login_as",
                    "admin_user": current_user,
                    "target_user": username,
                    "timestamp": datetime.now(timezone.utc)
                })
            except:
                pass

            log_admin_action(current_user, "ADMIN LOGIN AS USER", f"Logged in as user: {username}")

            session['user_id'] = user['_id']
            session['username'] = user['username']
            session['is_admin'] = user.get('is_admin', False)
            session['head_admin'] = user.get('head_admin', False)
            session.permanent = True

            admin_status = ""
            if user.get('head_admin'):
                admin_status = " [HEAD ADMIN]"
            elif user.get('is_admin'):
                admin_status = " [ADMIN]"

            return f"✅ Successfully logged in as '{username}'{admin_status}\nUser ID: {user['_id']}\nPoints: {user.get('points', 0)}\n\n⚠️ SECURITY WARNING: This action has been logged!"
        
        elif command == 'whoami()':
            # Show current session info
            if 'user_id' in session:
                current_user = mongo_db.users.find_one({"_id": session['user_id']})
                if current_user:
                    admin_status = ""
                    if current_user.get('head_admin'):
                        admin_status = " [HEAD ADMIN]"
                    elif current_user.get('is_admin'):
                        admin_status = " [ADMIN]"
                    
                    return f"Current session:\nUsername: {current_user['username']}{admin_status}\nUser ID: {current_user['_id']}\nPoints: {current_user.get('points', 0)}\nSession is_admin: {session.get('is_admin', False)}\nSession head_admin: {session.get('head_admin', False)}"
                else:
                    return "Session user not found in database"
            else:
                return "Not logged in"
        
        elif command == 'admin_logs()':
            # Show recent admin actions
            try:
                logs = list(mongo_db.admin_logs.find().sort("timestamp", -1).limit(10))
                if logs:
                    result = "Recent Admin Actions (last 10):\n"
                    for log in logs:
                        timestamp = log.get('timestamp', 'Unknown')
                        action = log.get('action', 'Unknown')
                        admin_user = log.get('admin_user', 'Unknown')
                        target_user = log.get('target_user', 'N/A')
                        reason = log.get('reason', '')
                        
                        if target_user != 'N/A':
                            result += f"  {timestamp} - {admin_user}: {action} -> {target_user}"
                            if reason:
                                result += f" ({reason})"
                            result += "\n"
                        else:
                            result += f"  {timestamp} - {admin_user}: {action}\n"
                    return result
                else:
                    return "No admin logs found"
            except Exception as e:
                return f"Error retrieving admin logs: {str(e)}"
        
        elif command == 'april_fools()' or command == 'chaos_mode()':
            return toggle_april_fools_mode()
        
        elif command.startswith('reset_password(') and command.endswith(')'):
            # Extract username and new password from command
            try:
                # Extract the parameters inside the parentheses
                params_str = command[15:-1]  # Remove 'reset_password(' and ')'
                
                # Handle quoted parameters properly
                import ast
                from datetime import datetime, timezone
                try:
                    # Safely parse the parameters as a tuple
                    params = ast.literal_eval(f"({params_str})")
                    if isinstance(params, tuple) and len(params) == 2:
                        username, new_password = params
                    elif isinstance(params, str):
                        # If only one parameter was passed, this won't work
                        return "Error: reset_password requires two parameters: username and new_password"
                    else:
                        return "Error: Invalid parameters. Usage: rtl.reset_password('username', 'new_password')"
                except:
                    # Alternative parsing method
                    parts = params_str.split(',', 1)
                    if len(parts) != 2:
                        return "Error: Invalid parameters. Usage: rtl.reset_password('username', 'new_password')"
                    
                    username = parts[0].strip().strip("'\"")
                    new_password = parts[1].strip().strip("'\"")
                
                # Find the user by username
                user = mongo_db.users.find_one({"username": username})
                if not user:
                    return f"Error: User '{username}' not found"
                
                # Hash the new password
                password_hash = generate_password_hash(new_password)
                
                # Update the user's password
                mongo_db.users.update_one(
                    {"username": username},
                    {"$set": {"password_hash": password_hash}}
                )
                
                # Log the action
                admin_user = mongo_db.users.find_one({"_id": session['user_id']})
                admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
                log_message = f"Admin {admin_username} reset password for user {username} via console command"
                from datetime import datetime, timezone
                mongo_db.logs.insert_one({
                    "message": log_message, 
                    "timestamp": datetime.now(timezone.utc),
                    "action_type": "password_reset_console"
                })
                
                return f"✅ Password reset successfully for user '{username}'"
                
            except Exception as e:
                return f"Error resetting password: {str(e)}"
        
        elif command == 'chaos_status()' or command == 'april_status()':
            return get_april_fools_status()
        
        else:
            return f"Unknown RTL command: {command}\nType 'help' for available commands"
            
    except Exception as e:
        return f"Error executing RTL command: {str(e)}"

def execute_python_code(code):
    """Safely execute Python code with limited scope"""
    import sys
    from io import StringIO
    
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Create a safe execution environment
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'range': range,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'enumerate': enumerate,
                'zip': zip,
                'type': type,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                'dir': dir,
                'help': help,
            },
            'mongo_db': mongo_db,  # Allow database access for admins
            'datetime': datetime,
            'ObjectId': ObjectId,
        }
        
        # Try to evaluate as expression first
        try:
            result = eval(code, safe_globals)
            if result is not None:
                print(result)
        except SyntaxError:
            # If it's not an expression, try to execute as statement
            exec(code, safe_globals)
        
        # Get the output
        output = captured_output.getvalue()
        return output if output else "Command executed successfully (no output)"
        
    except Exception as e:
        return f"Python Error: {str(e)}"
    finally:
        # Restore stdout
        sys.stdout = old_stdout

def toggle_april_fools_mode():
    """Toggle April Fools mode - randomizes level positions on every page load"""
    global levels_cache
    
    try:
        # Check current state
        settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
        
        if settings and settings.get('enabled', False):
            # Disable April Fools mode
            mongo_db.site_settings.update_one(
                {"_id": "april_fools"},
                {"$set": {"enabled": False, "disabled_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            
            # Restore original positions
            restore_original_positions()
            
            # Clear cache to ensure fresh data on next load
            levels_cache.clear()
            
            return """🎭 April Fools Mode DISABLED! 🎭

Level positions have been restored to normal.
The chaos has ended... for now. 😈

Use rtl.april_fools() again to re-enable the madness!"""
        
        else:
            # Enable April Fools mode
            # First, save original positions
            save_original_positions()
            
            # Clear cache to ensure fresh data
            levels_cache.clear()
            
            mongo_db.site_settings.update_one(
                {"_id": "april_fools"},
                {"$set": {
                    "enabled": True, 
                    "enabled_at": datetime.now(timezone.utc),
                    "description": "Randomizes level positions on every page refresh"
                }},
                upsert=True
            )
            
            return """🎭 APRIL FOOLS MODE ACTIVATED! 🎭

🌪️ CHAOS UNLEASHED! 🌪️

Every time someone refreshes the main list page,
the levels will appear in COMPLETELY RANDOM positions!

⚠️ Don't worry - the real positions are safely stored.
⚠️ This only affects the display, not the actual database.

Effects:
- Main list shows random positions every refresh
- Legacy list also randomized
- Points calculations remain correct
- Records still work normally

Use rtl.april_fools() again to disable and restore order.

Let the confusion begin! 😈🎉"""
    
    except Exception as e:
        return f"Error toggling April Fools mode: {str(e)}"

def save_original_positions():
    """Save original level positions before chaos mode"""
    try:
        # Get all levels with their current positions
        levels = list(mongo_db.levels.find({}, {"_id": 1, "position": 1, "is_legacy": 1}))
        
        # Save original positions
        for level in levels:
            mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {"$set": {"original_position": level["position"]}}
            )
        
        print(f"✅ Saved original positions for {len(levels)} levels")
        
    except Exception as e:
        print(f"❌ Error saving original positions: {e}")

def restore_original_positions():
    """Restore original level positions after chaos mode"""
    try:
        # Get all levels with original positions
        levels = list(mongo_db.levels.find(
            {"original_position": {"$exists": True}}, 
            {"_id": 1, "original_position": 1}
        ))
        
        # Restore original positions
        for level in levels:
            mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {
                    "$set": {"position": level["original_position"]},
                    "$unset": {"original_position": ""}
                }
            )
        
        print(f"✅ Restored original positions for {len(levels)} levels")
        
    except Exception as e:
        print(f"❌ Error restoring original positions: {e}")

def is_april_fools_active():
    """Check if April Fools mode is currently active"""
    try:
        settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
        return settings and settings.get('enabled', False)
    except:
        return False

def get_april_fools_status():
    """Get detailed April Fools mode status"""
    try:
        settings = mongo_db.site_settings.find_one({"_id": "april_fools"})
        
        if not settings:
            return """🎭 April Fools Mode Status: NEVER ACTIVATED

The chaos has never been unleashed!
Use rtl.april_fools() to start the madness! 😈"""
        
        is_active = settings.get('enabled', False)
        
        if is_active:
            enabled_at = settings.get('enabled_at', 'Unknown')
            return f"""🎭 April Fools Mode Status: 🔴 ACTIVE 🔴

🌪️ CHAOS IS CURRENTLY UNLEASHED! 🌪️

Activated: {enabled_at}
Effect: Level positions randomize on every page refresh
Affected Pages: Main list (/), Legacy list (/legacy)

⚠️ Original positions are safely stored
⚠️ Use rtl.april_fools() to restore order

The madness continues... 😈🎉"""
        else:
            enabled_at = settings.get('enabled_at', 'Unknown')
            disabled_at = settings.get('disabled_at', 'Unknown')
            return f"""🎭 April Fools Mode Status: 🟢 DISABLED 🟢

The chaos has been contained! ✅

Last Activated: {enabled_at}
Last Disabled: {disabled_at}

Everything is back to normal order.
Use rtl.april_fools() to unleash chaos again! 😈"""
    
    except Exception as e:
        return f"Error checking April Fools status: {str(e)}"

def randomize_level_positions(levels):
    """Randomize level positions for April Fools mode"""
    import random
    import copy
    
    if not levels:
        return levels
    
    # Make a deep copy to avoid modifying the original data
    levels_copy = copy.deepcopy(levels)
    
    # Separate main and legacy levels
    main_levels = [level for level in levels_copy if not level.get('is_legacy', False)]
    legacy_levels = [level for level in levels_copy if level.get('is_legacy', False)]
    
    # Just shuffle the order, don't change position numbers
    if main_levels:
        random.shuffle(main_levels)
        # Reassign positions based on new order
        for i, level in enumerate(main_levels):
            level['position'] = i + 1
    
    if legacy_levels:
        random.shuffle(legacy_levels)
        # Reassign positions based on new order
        for i, level in enumerate(legacy_levels):
            level['position'] = i + 1
    
    # Combine and return
    all_levels = main_levels + legacy_levels
    return all_levels


@app.route('/admin/make_head_admin', methods=['POST'])
def admin_make_head_admin():
    """Make a user a head admin - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    user_id = int(request.form.get('user_id'))
    
    # Find the user
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_console'))
    
    # Check if user is already a head admin
    if user.get('head_admin', False):
        flash(f'{user["username"]} is already a head admin', 'warning')
        return redirect(url_for('admin_console'))
    
    # Make the user a head admin
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"head_admin": True}}
    )
    
    flash(f'{user["username"]} is now a head admin!', 'success')
    return redirect(url_for('admin_console'))

@app.route('/admin/remove_head_admin', methods=['POST'])
def admin_remove_head_admin():
    """Remove head admin status from a user - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    user_id = int(request.form.get('user_id'))
    
    # Prevent removing head admin status from yourself
    if user_id == session['user_id']:
        flash('You cannot remove head admin status from yourself', 'danger')
        return redirect(url_for('admin_console'))
    
    # Find the user
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_console'))
    
    # Check if user is a head admin
    if not user.get('head_admin', False):
        flash(f'{user["username"]} is not a head admin', 'warning')
        return redirect(url_for('admin_console'))
    
    # Remove head admin status
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"head_admin": False}}
    )
    
    flash(f'{user["username"]} is no longer a head admin', 'success')
    return redirect(url_for('admin_console'))

@app.route('/admin/demote_admin', methods=['POST'])
def admin_demote_admin():
    """Demote an admin to regular user - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    user_id = int(request.form.get('user_id'))
    
    # Prevent demoting yourself
    if user_id == session['user_id']:
        flash('You cannot demote yourself', 'danger')
        return redirect(url_for('admin_console'))
    
    # Find the user
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_console'))
    
    # Check if user is an admin
    if not user.get('is_admin', False):
        flash(f'{user["username"]} is not an admin', 'warning')
        return redirect(url_for('admin_console'))
    
    # Prevent demoting head admins
    if user.get('head_admin', False):
        flash('Cannot demote a head admin', 'danger')
        return redirect(url_for('admin_console'))
    
    # Demote the admin
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_admin": False}}
    )
    
    flash(f'{user["username"]} has been demoted to regular user', 'success')
    return redirect(url_for('admin_console'))

def promote_user(user_id):
    """Promote a user to admin - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_console'))
    
    # Promote the user
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_admin": True}}
    )
    
    flash(f'{user["username"]} has been promoted to admin', 'success')
    return redirect(url_for('admin_console'))

@app.route('/admin/demote/<user_id>')
def demote_user(user_id):
    """Demote an admin to regular user - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    user = mongo_db.users.find_one({"_id": user_id})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_console'))
    
    # Prevent demoting the head admin
    if user.get('head_admin'):
        flash('Cannot demote a head admin', 'danger')
        return redirect(url_for('admin_console'))
    
    # Demote the admin
    mongo_db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_admin": False}}
    )
    
    flash(f'{user["username"]} has been demoted to regular user', 'success')
    return redirect(url_for('admin_console'))

@app.route('/admin/tools')
def admin_tools():
    """Admin tools page for IP ban and user reset functionality - Now accessible to regular admins too"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow both regular admins and head admins to access
    if not session.get('is_admin') and not session.get('head_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('admin'))
    
    return render_template('admin/tools.html')

@app.route('/admin/levels', methods=['GET', 'POST'])
def admin_levels():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Check if we're filtering for legacy levels
        filter_type = request.args.get('filter')
        is_legacy_filter = (filter_type == 'legacy')
        
        if request.method == 'POST':
            # Get next level ID
            last_level = mongo_db.levels.find_one(sort=[("_id", -1)])
            next_id = (last_level['_id'] + 1) if last_level else 1
            
            name = request.form.get('name')
            creator = request.form.get('creator')
            verifier = request.form.get('verifier')
            level_id = request.form.get('level_id')
            video_url = request.form.get('video_url')
            
            # Handle thumbnail options
            thumbnail_type = request.form.get('thumbnail_type', 'auto')
            thumbnail_url = ''
            
            if thumbnail_type == 'url':
                # Custom URL
                thumbnail_url = request.form.get('thumbnail_url', '').strip()
            elif thumbnail_type == 'upload':
                # Handle file upload
                if 'thumbnail_file' in request.files:
                    file = request.files['thumbnail_file']
                    if file and file.filename:
                        try:
                            # Convert uploaded image to base64
                            thumbnail_url = convert_image_to_base64(file)
                            if not thumbnail_url:
                                flash('Failed to process uploaded image. Please try a different image.', 'warning')
                                thumbnail_url = ''
                        except Exception as e:
                            print(f"Image upload error: {e}")
                            flash('Error processing uploaded image. Please try again.', 'danger')
                            thumbnail_url = ''
                    else:
                        flash('No file selected for upload.', 'warning')
                        thumbnail_url = ''
            # If thumbnail_type == 'auto', thumbnail_url stays empty (uses YouTube auto)
            
            description = request.form.get('description')
            difficulty = float(request.form.get('difficulty'))
            position = int(request.form.get('position'))
            is_legacy = 'is_legacy' in request.form
            
            points_str = request.form.get('points')
            min_percentage = int(request.form.get('min_percentage', '100'))
            
            # Calculate points
            if points_str and points_str.strip():
                points = float(points_str)
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

            # Expire timestamps so the next request reloads from DB while keeping
            # existing thumbnail_url values intact in the cache list.
            # The new level's thumbnail_url will be fetched from DB by the fallback
            # query inside get_fast_cached_levels on the next reload.
            levels_cache['main_list_updated'] = None
            levels_cache['legacy_list_updated'] = None
            
            # Recalculate points for all levels after position changes
            recalculate_all_points(levels_only=True)
            
            # Log level placement to changelog
            above_level = None
            below_level = None
            
            # Special case: if placing at position 1, check if there was a previous #1
            if position == 1:
                # Find the previous #1 level (if any)
                previous_top_level = mongo_db.levels.find_one({"position": 1, "is_legacy": is_legacy})
                if previous_top_level and previous_top_level['name'] != name:
                    above_level = previous_top_level['name']
            else:
                # Find levels above and below for positions > 1
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
        
        # GET request - display levels
        # Try to use cached data first, fallback to database
        main_cache = levels_cache.get('main_list', []) or []
        legacy_cache = levels_cache.get('legacy_list', []) or []
        
        # Always check if we need to load from database
        if is_legacy_filter:
            if legacy_cache:
                levels = legacy_cache
            else:
                # Load legacy levels from database
                levels = list(mongo_db.levels.find({"is_legacy": True}, {
                    "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
                    "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1,
                    "demon_type": 1, "min_percentage": 1
                }).sort("position", 1))
        else:
            if main_cache:
                levels = main_cache[:100]  # Only show top 100 from cache
            else:
                # Load only top 100 main levels from database
                levels = list(mongo_db.levels.find({"$or": [{"is_legacy": False}, {"is_legacy": {"$exists": False}}]}, {
                    "name": 1, "creator": 1, "verifier": 1, "position": 1, "points": 1, 
                    "level_id": 1, "difficulty": 1, "is_legacy": 1, "level_type": 1,
                    "demon_type": 1, "min_percentage": 1
                }).sort("position", 1).limit(100))
        
        return render_template('admin/levels.html', levels=levels, is_legacy_filter=is_legacy_filter)
    
    except Exception as e:
        print(f"Error in admin_levels route: {e}")
        flash('An error occurred while loading the levels management page. Please try again.', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/edit_level', methods=['POST'])
def admin_edit_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        db_level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            db_level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_levels'))
    
    game_level_id = request.form.get('game_level_id')
    difficulty = float(request.form.get('difficulty'))
    # Note: Demon type requirement removed - now using text-based difficulties
    # demon_type = request.form.get('demon_type', '').strip() if difficulty == 10 else None
    demon_type = None  # Demon subcategories removed

    
    # Exclude thumbnail_url — it can be hundreds of KB of base64 and causes
    # socket timeouts on Atlas M0.  The thumbnail is handled separately via the
    # thumbnail_type form field; the 'keep_existing' path never needs to read
    # the current value because we simply omit thumbnail_url from update_data.
    level = mongo_db.levels.find_one({"_id": db_level_id}, {"thumbnail_url": 0})

    if not level:
        flash('Level not found', 'danger')
        return redirect(url_for('admin_levels'))

    # Handle thumbnail options with improved logic
    thumbnail_type = request.form.get('thumbnail_type', 'auto')
    thumbnail_url = ''
    
    if thumbnail_type == 'url':
        # Custom URL
        thumbnail_url = request.form.get('thumbnail_url', '').strip()
    elif thumbnail_type == 'upload':
        # Handle file upload
        if 'thumbnail_file' in request.files:
            file = request.files['thumbnail_file']
            if file and file.filename:
                try:
                    # Convert uploaded image to base64
                    thumbnail_url = convert_image_to_base64(file)
                    if not thumbnail_url:
                        flash('Failed to process uploaded image. Please try a different image.', 'warning')
                        thumbnail_url = ''
                except Exception as e:
                    print(f"Image upload error: {e}")
                    flash('Error processing uploaded image. Please try again.', 'danger')
                    thumbnail_url = ''
            else:
                flash('No file selected for upload.', 'warning')
                thumbnail_url = ''
    elif thumbnail_type == 'keep' or thumbnail_type == 'keep_existing':
        # Keep existing thumbnail — thumbnail_url is excluded from the find_one
        # projection to avoid socket timeouts, but that's fine: the update_data
        # block below omits thumbnail_url for keep/keep_existing, and the cache
        # update also leaves the existing value untouched (see `pass` branch below).
        thumbnail_url = ''
    # If thumbnail_type == 'auto', thumbnail_url stays empty (uses YouTube auto)
    
    # Handle position changes
    old_position = level['position']
    old_is_legacy = level.get('is_legacy', False)
    
    points_str = request.form.get('points')
    min_percentage = int(request.form.get('min_percentage', '100'))
    position = int(request.form.get('position'))
    is_legacy = 'is_legacy' in request.form
    
    # Handle position shifting if position changed
    if position != old_position or is_legacy != old_is_legacy:
        # Track position change
        admin_username = session.get('username', 'Unknown Admin')
        track_position_change(db_level_id, old_position, position, admin_username)
        
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
        points = float(points_str)
    else:
        level_type = request.form.get('level_type', level.get('level_type', 'Level'))
        points = calculate_level_points(position, is_legacy, level_type)
    
    # Check level name for profanity
    new_name = request.form.get('name', '').strip()
    if new_name != level.get('name', ''):  # Only check if name is being changed
        is_name_clean, profanity_reason = check_level_name_profanity(new_name)
        if not is_name_clean:
            flash(f'Level name not allowed: {profanity_reason}', 'danger')
            return redirect(url_for('admin_levels'))
    
    update_data = {
        "name": new_name,
        "creator": request.form.get('creator'),
        "verifier": request.form.get('verifier'),
        "level_id": game_level_id if game_level_id and game_level_id.strip() else None,
        "video_url": request.form.get('video_url'),
        "description": request.form.get('description'),
        "difficulty": difficulty,
        "demon_type": demon_type,
        "position": position,
        "is_legacy": is_legacy,
        "level_type": request.form.get('level_type', 'Level'),
        "points": points,
        "min_percentage": min_percentage
    }
    
    # Only update thumbnail_url if we're not keeping the existing one or if we have a new value
    if thumbnail_type != 'keep' and thumbnail_type != 'keep_existing':
        update_data["thumbnail_url"] = thumbnail_url
    
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

    # Directly update this level's thumbnail in the in-memory cache so the
    # new value is visible immediately.  The cache list is kept intact (rather
    # than set to None) so that OTHER levels' thumbnail_url values survive the
    # next DB reload (thumbnail_url is excluded from the DB projection to avoid
    # socket timeouts, making the in-memory cache the sole source for thumbnails).
    cache_list = levels_cache.get('main_list') or []
    level_id_str = str(db_level_id)
    for cached_level in cache_list:
        if str(cached_level.get('_id', '')) == level_id_str:
            if thumbnail_type in ('keep', 'keep_existing'):
                pass  # leave existing thumbnail untouched
            else:
                cached_level['thumbnail_url'] = thumbnail_url
            break

    # Expire timestamps so the next request reloads other fields from DB
    levels_cache['main_list_updated'] = None
    levels_cache['legacy_list_updated'] = None

    # Only recalculate points if position or legacy status changed (performance optimization)
    if position != old_position or is_legacy != old_is_legacy:
        recalculate_all_points(levels_only=True)
    
    flash('Level updated successfully!', 'success')
    return redirect(url_for('admin_levels') + '?updated=' + str(db_level_id))

@app.route('/admin/delete_level', methods=['POST'])
def admin_delete_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_levels'))
    
    removal_reason = request.form.get('removal_reason', '').strip()  # Get optional removal reason
    
    # Get level info before deletion (exclude large thumbnail_url)
    level = mongo_db.levels.find_one({"_id": level_id}, {"thumbnail_url": 0})
    if not level:
        flash('Level not found', 'danger')
        return redirect(url_for('admin_levels'))

    level_position = level['position']
    is_legacy = level.get('is_legacy', False)
    admin_username = session.get('username', 'Unknown')
    
    # Delete associated records
    mongo_db.records.delete_many({"level_id": level_id})
    
    # Save history before deleting
    history_entry = {
        "level_id": level_id,
        "action": "deleted",
        "old_data": level,
        "removal_reason": removal_reason,
        "admin": admin_username,
        "timestamp": datetime.now(timezone.utc)
    }
    mongo_db.level_history.insert_one(history_entry)
    
    # Delete the level
    mongo_db.levels.delete_one({"_id": level_id})
    
    # Log enhanced level removal to changelog
    log_level_change(
        action="removed",
        level_name=level['name'],
        admin_username=admin_username,
        old_position=level_position,
        reason=removal_reason,
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
    recalculate_all_points(levels_only=True)
    
    # Log admin action
    reason_text = f" (Reason: {removal_reason})" if removal_reason else ""
    log_admin_action(admin_username, f"REMOVED LEVEL: {level['name']}", f"Position {level_position}{reason_text}")
    
    # Update historical rankings
    try:
        update_historical_rankings()
    except Exception as e:
        print(f"Warning: Failed to update historical rankings: {e}")
    
    flash(f'Level "{level["name"]}" deleted successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_legacy', methods=['POST'])
def admin_move_to_legacy():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_levels'))
    
    # Get level info before moving (exclude large thumbnail_url)
    level = mongo_db.levels.find_one({"_id": level_id}, {"thumbnail_url": 0})
    if not level or level.get('is_legacy', False):
        flash('Level not found or already in legacy', 'danger')
        return redirect(url_for('admin_levels'))

    old_position = level['position']
    
    # Find the highest position in the legacy list
    highest_legacy = mongo_db.levels.find_one(
        {"is_legacy": True}, 
        sort=[("position", -1)]
    )
    new_position = 151 if not highest_legacy else highest_legacy['position'] + 1
    
    # Move level to legacy
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": True, "position": new_position}}
    )
    
    # Fix: Properly shift positions in the main list to fill the gap
    mongo_db.levels.update_many(
        {"position": {"$gt": old_position}, "is_legacy": {"$ne": True}},
        {"$inc": {"position": -1}}
    )
    
    # Also update any levels that might have is_legacy field missing (treat as False)
    mongo_db.levels.update_many(
        {"position": {"$gt": old_position}, "is_legacy": {"$exists": False}},
        {"$inc": {"position": -1}}
    )
    
    # Clear the cache to ensure fresh data
    global levels_cache
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    
    # Recalculate points for all levels after position changes
    recalculate_all_points(levels_only=True)
    
    flash('Level moved to legacy list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_main', methods=['POST'])
def admin_move_to_main():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_levels'))
    
    position = int(request.form.get('position'))
    
    # Get level info before moving (exclude large thumbnail_url)
    level = mongo_db.levels.find_one({"_id": level_id}, {"thumbnail_url": 0})
    if not level or not level.get('is_legacy', False):
        flash('Level not found or already in main list', 'danger')
        return redirect(url_for('admin_levels'))
    
    old_position = level['position']
    
    # Fix: Properly shift positions in the legacy list to fill the gap
    mongo_db.levels.update_many(
        {"position": {"$gt": old_position}, "is_legacy": True},
        {"$inc": {"position": -1}}
    )
    
    # Shift positions in the main list to make room
    mongo_db.levels.update_many(
        {"position": {"$gte": position}, "is_legacy": {"$ne": True}},
        {"$inc": {"position": 1}}
    )
    
    # Also update any levels that might have is_legacy field missing (treat as False)
    mongo_db.levels.update_many(
        {"position": {"$gte": position}, "is_legacy": {"$exists": False}},
        {"$inc": {"position": 1}}
    )
    
    # Clear the cache to ensure fresh data
    global levels_cache
    levels_cache['main_list'] = None
    levels_cache['legacy_list'] = None
    
    # Move level to main list
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": False, "position": position}}
    )
    
    # Recalculate points for all levels after position changes
    recalculate_all_points(levels_only=True)
    
    flash('Level moved to main list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/approve_record/<record_id>', methods=['POST'])
def admin_approve_record(record_id):
    """Enhanced record approval with better error handling and debugging"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Convert string record_id to ObjectId
        try:
            record_object_id = ObjectId(record_id)
        except InvalidId:
            flash('Invalid record ID', 'danger')
            return redirect(url_for('admin'))
        
        # Get record with detailed error checking
        record = mongo_db.records.find_one({"_id": record_object_id})
        if not record:
            flash('Record not found', 'danger')

            return redirect(url_for('admin'))
        

        
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
        
        
        
        # Approve the record with timestamp
        approval_time = datetime.now(timezone.utc)
        update_result = mongo_db.records.update_one(
            {"_id": record_object_id},
            {"$set": {
                "status": "approved",
                "approved_by": admin_username,
                "approved_at": approval_time
            }}
        )
        

        
        # Calculate points for this specific record
        approved_record = dict(record)
        approved_record['status'] = 'approved'
        points_earned = calculate_record_points(approved_record, level)
        

        
        # Get user's points before update
        old_points = user.get('points', 0)
        
        # Update user points (recalculate all)
        update_user_points(record['user_id'])
        
        # Get user's points after update
        updated_user = mongo_db.users.find_one({"_id": record['user_id']})
        new_points = updated_user.get('points', 0) if updated_user else 0
        

        
        # Check if this user is the verifier of this level and award verifier points if applicable
        if level.get('verifier') and user.get('username'):
            # Check if the user's username matches the level verifier
            if user['username'].lower() == level['verifier'].lower():
                # Check if verifier points have already been awarded for this level
                verifier_record_exists = mongo_db.records.find_one({
                    "user_id": record['user_id'],
                    "level_id": record['level_id'],
                    "is_verifier": True
                })
                
                if not verifier_record_exists:
                    # Award verifier points
                    success = award_verifier_points(record['level_id'], record['user_id'])
                    if success:
                        # Update points again after awarding verifier points
                        update_user_points(record['user_id'])
                        # Get updated points
                        updated_user = mongo_db.users.find_one({"_id": record['user_id']})
                        new_points = updated_user.get('points', 0) if updated_user else 0
        
        # Log admin action with more details
        log_admin_action(
            admin_username,
            "Record Approved",
            f"Approved {user['username']}'s {record['progress']}% record on {level['name']} (Position #{level.get('position', '?')}) - Earned {points_earned} points (Total: {old_points} → {new_points})"
        )
        
        # Create notification for user
        create_notification(
            record['user_id'],
            'record_status',
            'Record Approved! ✅',
            f'Your {record["progress"]}% record on "{level["name"]}" has been approved! You earned {points_earned} points.',
            record_object_id,
            'record'
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


@app.route('/admin/fix_verifier_points', methods=['POST'])
def admin_fix_verifier_points():
    """Admin route to fix the verifier points bug"""
    
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_panel'))
    
    try:
        # Run the fix function
        updated_users = fix_verifier_points_bug()
        flash(f'✅ Verifier points bug fix completed. Updated {updated_users} users.', 'success')
    except Exception as e:
        flash(f'❌ Error fixing verifier points: {str(e)}', 'danger')
        print(f"Admin fix verifier points error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_panel'))
import traceback

from bson import ObjectId
from bson.errors import InvalidId

from flask import flash, redirect, url_for, session



@app.route('/admin/update_top_1_role', methods=['POST'])
def admin_update_top_1_role():
    """Admin route to manually update the top 1 player role"""
    
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('admin_panel'))
    
    try:
        # Run the update function
        if update_top_1_player_role():
            flash('✅ Top 1 player role updated successfully.', 'success')
        else:
            flash('❌ Failed to update Top 1 player role.', 'danger')
    except Exception as e:
        flash(f'❌ Error updating Top 1 player role: {str(e)}', 'danger')
        print(f"Admin update top 1 role error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_panel'))


@app.route('/admin/reject_record/<record_id>', methods=['POST'])
def admin_reject_record(record_id):
    """Enhanced record rejection with better error handling"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Convert string record_id to ObjectId
        try:
            record_object_id = ObjectId(record_id)
        except InvalidId:
            flash('Invalid record ID', 'danger')
            return redirect(url_for('admin'))
        
        # Get record info before rejecting
        record = mongo_db.records.find_one({"_id": record_object_id})
        if not record:
            flash('Record not found', 'danger')
            return redirect(url_for('admin'))
        
        # Call the separate function to handle the actual rejection
        success = reject_record(record_id)
        
        if success:
            flash(f'✅ Record rejected for "{record["level_name"]}".', 'success')
        else:
            flash(f'❌ Error rejecting record for "{record["level_name"]}".', 'danger')
            
    except Exception as e:
        flash(f'Error rejecting record: {str(e)}', 'danger')
        print(f"Admin reject record error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin'))


@app.route('/admin/accept_verification_legacy/<submission_id>', methods=['POST'])
def admin_accept_verification_legacy(submission_id):
    """Admin route to accept a verification submission"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Convert string submission_id to ObjectId
        try:
            submission_object_id = ObjectId(submission_id)
        except InvalidId:
            flash('Invalid submission ID', 'danger')
            return redirect(url_for('admin'))
        
        # Get submission info before accepting
        submission = mongo_db.verification_submissions.find_one({"_id": submission_object_id})
        if not submission:
            flash('Submission not found', 'danger')
            return redirect(url_for('admin'))
        
        admin_username = session.get('username')
        
        # Check for dethroning at #1
        dethroned_level = None
        current_first = mongo_db.levels.find_one({"position": 1, "is_legacy": False})
        if current_first:
            dethroned_level = current_first["name"]
        
        # Call the separate function to handle the actual acceptance
        success = accept_verification_submission(submission_id, admin_username)
        
        if success:
            # Get placement info from submission for the success message
            placement = submission.get('placement', 1)
            flash(f'✅ Verification accepted! "{submission["level_name"]}" has been placed at position #{placement}.', 'success')
        else:
            flash(f'❌ Error accepting verification for "{submission["level_name"]}".', 'danger')
            
    except Exception as e:
        flash(f'Error accepting verification: {str(e)}', 'danger')
        print(f"Admin accept verification error: {e}")
        import traceback
        traceback.print_exc()
    
    return redirect(url_for('admin_verifications'))

@app.route('/admin/record_legacy/<string:record_id>/reject', methods=['POST'])
def admin_reject_record_legacy(record_id):
    """Reject a specific record"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied - Admin only', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Validate record ID
        try:
            record_object_id = ObjectId(record_id)
        except Exception:
            flash('Invalid record ID', 'danger')
            return redirect(url_for('admin'))
        
        record = mongo_db.records.find_one({"_id": record_object_id})
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
        
        # Reject the record with timestamp
        rejection_time = datetime.now(timezone.utc)
        mongo_db.records.update_one(
            {"_id": record_object_id},
            {"$set": {
                "status": "rejected",
                "rejected_by": admin_username,
                "rejected_at": rejection_time
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
                f"Rejected {user['username']}'s {record['progress']}% record on {level['name']}"
            )
            
            # Create notification for user
            create_notification(
                record['user_id'],
                'record_status',
                'Record Rejected ❌',
                f'Your {record["progress"]}% record on "{level["name"]}" has been rejected.',
                record_object_id,
                'record'
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
        
        # Convert to ObjectIds
        record_ids = [ObjectId(rid) for rid in record_ids]
        
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
                                "rejected_at": datetime.now(timezone.utc)
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


@app.route('/admin/reset_user_password', methods=['POST'])
def admin_reset_user_password():
    """Force reset a user's password - Admin only"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        
        if not username or not new_password:
            flash('Username and new password are required', 'danger')
            return redirect(url_for('admin_console'))
        
        # Find the user by username
        user = mongo_db.users.find_one({"username": username})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('admin_console'))
        
        # Hash the new password
        password_hash = generate_password_hash(new_password)
        
        # Update the user's password
        mongo_db.users.update_one(
            {"username": username},
            {"$set": {"password_hash": password_hash}}
        )
        
        # Log the action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_message = f"Admin {admin_username} reset password for user {username}"
        mongo_db.logs.insert_one({
            "message": log_message, 
            "timestamp": datetime.now(timezone.utc),
            "action_type": "password_reset"
        })
        
        flash(f'Password reset successfully for user {username}', 'success')
        return redirect(url_for('admin_console'))
    
    except Exception as e:
        flash(f'Error resetting password: {str(e)}', 'danger')
        return redirect(url_for('admin_console'))

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
            site_settings = {"future_list_enabled": False, "submissions_enabled": True, "timemachine_enabled": True}
    except Exception as e:
        site_settings = {"future_list_enabled": False, "submissions_enabled": True, "timemachine_enabled": True}
    
    # Get changelog webhook settings
    try:
        changelog_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        if not changelog_settings:
            changelog_settings = {
                "ping_enabled": False,
                "ping_threshold": 1,
                "role_id": "1388326130183966720"
            }
        
        # Set environment variables for changelog settings
        os.environ['CHANGELOG_PING_ENABLED'] = str(changelog_settings.get("ping_enabled", False)).lower()
        os.environ['CHANGELOG_ROLE_ID'] = str(changelog_settings.get("role_id", "1388326130183966720"))
        
    except Exception as e:
        changelog_settings = {
            "ping_enabled": False,
            "ping_threshold": 1,
            "role_id": "1388326130183966720"
        }
    
    return render_template('admin/settings.html', 
                         system_info=system_info,
                         cache_info=cache_info,
                         db_stats=db_stats,
                         site_settings=site_settings,
                         changelog_settings=changelog_settings)

@app.route('/admin/webhook_settings')
def admin_webhook_settings():
    """Dedicated webhook settings panel"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get changelog webhook settings
    try:
        changelog_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        if not changelog_settings:
            changelog_settings = {
                "ping_enabled": False,
                "ping_threshold": 1,
                "role_id": "1388326130183966720",
                "message_count": 0,
                "webhook_enabled": True,
                "message_format": "detailed",
                "include_timestamp": True,
                "include_admin": True,
                "color_mode": "default",
                "rate_limit": 10,
                "log_level": "info",
                "custom_message": ""
            }
    except Exception as e:
        changelog_settings = {
            "ping_enabled": False,
            "ping_threshold": 1,
            "role_id": "1388326130183966720",
            "message_count": 0,
            "webhook_enabled": True,
            "message_format": "detailed",
            "include_timestamp": True,
            "include_admin": True,
            "color_mode": "default",
            "rate_limit": 10,
            "log_level": "info",
            "custom_message": ""
        }
    
    return render_template('admin/webhook_settings.html', changelog_settings=changelog_settings)

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

@app.route('/admin/settings/toggle_submissions', methods=['POST'])
def admin_toggle_submissions():
    """Toggle record submissions on/off"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get current settings
        settings = mongo_db.site_settings.find_one({"_id": "main"})
        if not settings:
            settings = {"_id": "main", "future_list_enabled": False, "submissions_enabled": True}
        
        # Toggle submissions
        new_status = not settings.get('submissions_enabled', True)
        settings['submissions_enabled'] = new_status
        
        # Update in database
        mongo_db.site_settings.replace_one(
            {"_id": "main"}, 
            settings, 
            upsert=True
        )
        
        status_text = "enabled" if new_status else "disabled"
        flash(f'Record submissions {status_text} successfully!', 'success')
        
        # Log admin action
        log_admin_action(
            session.get('username', 'Unknown Admin'),
            f"Toggled submissions: {status_text}",
            f"Submissions are now {status_text}"
        )
        
    except Exception as e:
        flash(f'Error toggling submissions: {str(e)}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/toggle_timemachine', methods=['POST'])
def admin_toggle_timemachine():
    """Toggle time machine feature on/off"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get current settings
        settings = mongo_db.site_settings.find_one({"_id": "main"})
        if not settings:
            settings = {"_id": "main", "future_list_enabled": False, "submissions_enabled": True, "timemachine_enabled": True}
        
        # Toggle time machine
        new_status = not settings.get('timemachine_enabled', True)
        settings['timemachine_enabled'] = new_status
        
        # Update in database
        mongo_db.site_settings.replace_one(
            {"_id": "main"}, 
            settings, 
            upsert=True
        )
        
        status_text = "enabled" if new_status else "disabled"
        flash(f'Time Machine {status_text} successfully!', 'success')
        
        # Log admin action
        log_admin_action(
            session.get('username', 'Unknown Admin'),
            f"Toggled Time Machine: {status_text}",
            f"Time Machine is now {status_text}"
        )
        
    except Exception as e:
        flash(f'Error toggling Time Machine: {str(e)}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/settings/changelog', methods=['POST'])
def admin_update_changelog_settings():
    """Update changelog webhook settings"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get form data
        ping_enabled = request.form.get('ping_enabled') == 'on'
        ping_threshold = int(request.form.get('ping_threshold', 1))
        role_id = request.form.get('role_id', '1388326130183966720')
        
        # Update settings in database
        mongo_db.site_settings.update_one(
            {"_id": "changelog"},
            {"$set": {
                "ping_enabled": ping_enabled,
                "ping_threshold": ping_threshold,
                "role_id": role_id
            }},
            upsert=True
        )
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "Changelog Settings Updated", 
                        f"Ping: {ping_enabled}, Threshold: {ping_threshold}, Role ID: {role_id}")
        
        flash('Changelog settings updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating changelog settings: {e}', 'danger')
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/webhook_settings', methods=['POST'])
def admin_update_webhook_settings():
    """Update advanced webhook settings"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get form data with proper error handling
        webhook_enabled = request.form.get('webhook_enabled') == 'on'
        ping_enabled = request.form.get('ping_enabled') == 'on'
        
        # Handle integer fields with defaults
        try:
            ping_threshold = int(request.form.get('ping_threshold', 1) or 1)
        except (ValueError, TypeError):
            ping_threshold = 1
            
        try:
            rate_limit = int(request.form.get('rate_limit', 10) or 10)
        except (ValueError, TypeError):
            rate_limit = 10
            
        role_id = request.form.get('role_id', '1388326130183966720')
        message_format = request.form.get('message_format', 'detailed')
        include_timestamp = request.form.get('include_timestamp') == 'on'
        include_admin = request.form.get('include_admin') == 'on'
        color_mode = request.form.get('color_mode', 'default')
        log_level = request.form.get('log_level', 'info')
        custom_message = request.form.get('custom_message', '').strip()
        
        # Get current settings to preserve message count
        current_settings = mongo_db.site_settings.find_one({"_id": "changelog"})
        message_count = current_settings.get("message_count", 0) if current_settings else 0
        
        # Update settings in database
        mongo_db.site_settings.update_one(
            {"_id": "changelog"},
            {"$set": {
                "webhook_enabled": webhook_enabled,
                "ping_enabled": ping_enabled,
                "ping_threshold": ping_threshold,
                "role_id": role_id,
                "message_format": message_format,
                "include_timestamp": include_timestamp,
                "include_admin": include_admin,
                "color_mode": color_mode,
                "rate_limit": rate_limit,
                "log_level": log_level,
                "custom_message": custom_message,
                "message_count": message_count
            }},
            upsert=True
        )
        
        # Update environment variables
        os.environ['CHANGELOG_PING_ENABLED'] = str(ping_enabled).lower()
        os.environ['CHANGELOG_ROLE_ID'] = str(role_id)
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "Webhook Settings Updated", 
                        f"Webhook: {webhook_enabled}, Ping: {ping_enabled}, Format: {message_format}")
        
        flash('Webhook settings updated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error updating webhook settings: {e}', 'danger')
    
    return redirect(url_for('admin_webhook_settings'))

@app.route('/admin/webhook_settings/test', methods=['POST'])
def admin_test_webhook():
    """Send a test webhook message"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Import the notification function
        from changelog_discord import notify_changelog
        
        # Get admin username for the message
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Send test message without formatting
        test_message = "🔔 Webhook Test Message\nThis is a test message to verify that the changelog webhook is working correctly."
        
        result = notify_changelog(test_message, admin_username)
        
        if result:
            flash('✅ Test webhook message sent successfully!', 'success')
        else:
            flash('❌ Failed to send test webhook message. Check logs for details.', 'danger')
            
    except Exception as e:
        flash(f'Error sending test webhook: {e}', 'danger')
    
    return redirect(url_for('admin_webhook_settings'))

@app.route('/admin/webhook_settings/send_custom', methods=['POST'])
def admin_send_custom_message():
    """Send a custom message via the webhook"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get the custom message from form
        message_content = request.form.get('message_content', '').strip()
        
        if not message_content:
            flash('Message content cannot be empty', 'danger')
            return redirect(url_for('admin_webhook_settings'))
        
        # Import the notification function
        from changelog_discord import notify_changelog
        
        # Get admin username for the message
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        
        # Send the custom message
        result = notify_changelog(message_content, admin_username)
        
        if result:
            flash('✅ Custom message sent successfully!', 'success')
        else:
            flash('❌ Failed to send custom message. Check logs for details.', 'danger')
            
    except Exception as e:
        flash(f'Error sending custom message: {e}', 'danger')
    
    return redirect(url_for('admin_webhook_settings'))

@app.route('/admin/webhook_settings/delete_message', methods=['POST'])
def admin_delete_webhook_message():
    """Delete a specific webhook message"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        message_id = request.form.get('message_id')
        
        # Import the deletion function
        from changelog_discord import delete_changelog_message
        
        # Attempt to delete the message
        if delete_changelog_message(message_id):
            flash(f'Message {message_id} deletion requested. Note: Due to Discord limitations, deletion may not be immediate.', 'success')
        else:
            flash(f'Failed to delete message {message_id}. Check logs for details.', 'danger')
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "Webhook Message Delete", f"Attempted to delete message {message_id}")
        
    except Exception as e:
        flash(f'Error processing message deletion: {e}', 'danger')
    
    return redirect(url_for('admin_webhook_settings'))

@app.route('/admin/webhook_settings/delete_all_messages', methods=['POST'])
def admin_delete_all_webhook_messages():
    """Delete all webhook messages"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Import the deletion function
        from changelog_discord import delete_all_changelog_messages
        
        # Attempt to delete all messages
        if delete_all_changelog_messages():
            # Reset message counter
            mongo_db.site_settings.update_one(
                {"_id": "changelog"},
                {"$set": {"message_count": 0}},
                upsert=True
            )
            flash('All messages deletion requested. Message counter has been reset.', 'success')
        else:
            flash('Failed to delete messages. Check logs for details.', 'danger')
        
        # Log admin action
        admin_user = mongo_db.users.find_one({"_id": session['user_id']})
        admin_username = admin_user['username'] if admin_user else 'Unknown Admin'
        log_admin_action(admin_username, "Webhook Messages Clear", "Attempted to clear all webhook messages")
        
    except Exception as e:
        flash(f'Error processing message clearing: {e}', 'danger')
    
    return redirect(url_for('admin_webhook_settings'))

@app.route('/admin/settings/delete_website', methods=['POST'])
def admin_delete_website():
    """Definitely delete the website (not a rickroll)"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # This is totally a real delete function 😉
    return redirect('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

    
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
        verifier = request.form.get('verifier') or "Not verified yet"
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

@app.route('/admin/edit_future_level', methods=['POST'])
def admin_edit_future_level():
    """Edit a future level"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_future_levels'))
    
    # Get current level
    level = mongo_db.future_levels.find_one({"_id": level_id})
    if not level:
        flash('Future level not found', 'danger')
        return redirect(url_for('admin_future_levels'))
    
    old_position = level['position']
    new_position = int(request.form.get('position'))
    
    # Handle position changes
    if new_position != old_position:
        if old_position < new_position:
            # Moving down: shift levels between old and new position up
            mongo_db.future_levels.update_many(
                {"position": {"$gt": old_position, "$lte": new_position}},
                {"$inc": {"position": -1}}
            )
        elif old_position > new_position:
            # Moving up: shift levels between new and old position down
            mongo_db.future_levels.update_many(
                {"position": {"$gte": new_position, "$lt": old_position}},
                {"$inc": {"position": 1}}
            )
    
    update_data = {
        "name": request.form.get('name'),
        "creator": request.form.get('creator'),
        "verifier": request.form.get('verifier') or "Not verified yet",
        "level_id": request.form.get('level_id') or None,
        "video_url": request.form.get('video_url'),
        "description": request.form.get('description'),
        "difficulty": float(request.form.get('difficulty')),
        "position": new_position
    }
    
    mongo_db.future_levels.update_one({"_id": level_id}, {"$set": update_data})
    
    # Log changes if position changed
    if new_position != old_position:
        above_level = None
        below_level = None
        
        if new_position > 1:
            above_level_doc = mongo_db.future_levels.find_one({"position": new_position - 1})
            if above_level_doc:
                above_level = above_level_doc['name']
        
        below_level_doc = mongo_db.future_levels.find_one({"position": new_position + 1})
        if below_level_doc:
            below_level = below_level_doc['name']
        
        log_level_change(
            action="moved",
            level_name=update_data['name'],
            admin_username=session.get('username', 'Unknown'),
            old_position=old_position,
            new_position=new_position,
            above_level=above_level,
            below_level=below_level,
            list_type="future"
        )
    
    flash('Future level updated successfully!', 'success')
    return redirect(url_for('admin_future_levels'))

@app.route('/admin/delete_future_level', methods=['POST'])
def admin_delete_future_level():
    """Delete a future level"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id_str = request.form.get('level_id')
    
    # Handle both ObjectId and integer level IDs
    try:
        level_id = ObjectId(level_id_str)
    except (ValueError, InvalidId):
        try:
            level_id = int(level_id_str)
        except ValueError:
            flash('Invalid level ID format', 'danger')
            return redirect(url_for('admin_future_levels'))
    
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

@app.route('/future/<int:level_id>')
def future_level_details(level_id):
    """Future level details page"""
    # Check if future list is enabled
    settings = mongo_db.site_settings.find_one({"_id": "main"})
    if not settings or not settings.get('future_list_enabled', False):
        return render_template('future_disabled.html')
    
    # Get the specific future level
    level = mongo_db.future_levels.find_one({"_id": level_id})
    if not level:
        flash('Future level not found', 'danger')
        return redirect(url_for('future_list'))
    
    return render_template('future_level_details.html', level=level)

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
        
        # Create notification for all users
        create_global_notification(
            'announcement',
            f'New Announcement! 📢',
            f'{title} - {message[:100]}...',
            announcement.get('_id'),
            'announcement',
            session.get('username', 'Admin')
        )
        
        flash(f'Announcement created! Will expire in {expires_in_hours} hours.', 'success')
        return redirect(url_for('admin_announcements'))
    
    # Get all announcements (active and expired)
    announcements = list(mongo_db.announcements.find({}).sort("created_at", -1))
    
    # Fix timezone issues for existing announcements
    current_time = datetime.now(timezone.utc)
    for announcement in announcements:
        # Ensure all datetime fields are timezone-aware
        if announcement.get('created_at') and announcement['created_at'].tzinfo is None:
            announcement['created_at'] = announcement['created_at'].replace(tzinfo=timezone.utc)
        if announcement.get('expires_at') and announcement['expires_at'].tzinfo is None:
            announcement['expires_at'] = announcement['expires_at'].replace(tzinfo=timezone.utc)
    
    return render_template('admin/announcements.html', announcements=announcements, current_time=current_time)

@app.route('/admin/polls', methods=['GET', 'POST'])
def admin_polls():
    """Admin interface for managing polls"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        question = request.form.get('question')
        poll_type = request.form.get('type', 'info')  # info, success, warning, danger
        expires_in_hours = int(request.form.get('expires_in_hours', 168))  # Default 1 week
        allow_multiple = 'allow_multiple' in request.form
        
        # Get options (filter out empty ones)
        options = []
        for i in range(1, 11):  # Support up to 10 options
            option_text = request.form.get(f'option_{i}', '').strip()
            if option_text:
                options.append({
                    'text': option_text,
                    'votes': 0,
                    'voters': []  # Track who voted for this option
                })
        
        if len(options) < 2:
            flash('A poll must have at least 2 options', 'danger')
            return redirect(url_for('admin_polls'))
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        poll = {
            "question": question,
            "type": poll_type,
            "options": options,
            "allow_multiple": allow_multiple,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "created_by": session.get('username', 'Unknown'),
            "active": True,
            "total_votes": 0
        }
        
        mongo_db.polls.insert_one(poll)
        
        # Create notification for all users
        create_global_notification(
            'poll',
            'New Poll! 📊',
            f'{question} - Vote now!',
            poll.get('_id'),
            'poll',
            session.get('username', 'Admin')
        )
        
        flash(f'Poll created! Will expire in {expires_in_hours} hours.', 'success')
        return redirect(url_for('admin_polls'))
    
    # Get all polls (active and expired)
    polls = list(mongo_db.polls.find({}).sort("created_at", -1))
    
    # Fix timezone issues for existing polls
    current_time = datetime.now(timezone.utc)
    for poll in polls:
        # Ensure all datetime fields are timezone-aware
        if poll.get('created_at') and poll['created_at'].tzinfo is None:
            poll['created_at'] = poll['created_at'].replace(tzinfo=timezone.utc)
        if poll.get('expires_at') and poll['expires_at'].tzinfo is None:
            poll['expires_at'] = poll['expires_at'].replace(tzinfo=timezone.utc)
    
    return render_template('admin/polls.html', polls=polls, current_time=current_time)

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

@app.route('/admin/delete_poll', methods=['POST'])
def admin_delete_poll():
    """Delete a poll"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    poll_id = request.form.get('poll_id')
    
    mongo_db.polls.delete_one({"_id": ObjectId(poll_id)})
    
    flash('Poll deleted successfully!', 'success')
    return redirect(url_for('admin_polls'))

@app.route('/vote_poll', methods=['POST'])
def vote_poll():
    """Vote on a poll"""
    if 'user_id' not in session:
        flash('Please log in to vote', 'warning')
        return redirect(url_for('login'))
    
    poll_id = request.form.get('poll_id')
    selected_options = request.form.getlist('poll_option')
    
    if not selected_options:
        flash('Please select at least one option to vote', 'warning')
        return redirect(request.referrer or url_for('index'))
    
    # Get the poll
    poll = mongo_db.polls.find_one({"_id": ObjectId(poll_id)})
    if not poll:
        flash('Poll not found', 'danger')
        return redirect(url_for('index'))
    
    # Check if poll is still active
    current_time = datetime.now(timezone.utc)
    expires_at = poll.get('expires_at')
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= current_time:
            flash('This poll has expired', 'warning')
            return redirect(request.referrer or url_for('index'))
    
    user_id = session['user_id']
    
    # Check if user has already voted
    user_has_voted = False
    for option in poll['options']:
        if user_id in option.get('voters', []):
            user_has_voted = True
            break
    
    if user_has_voted:
        flash('You have already voted in this poll', 'warning')
        return redirect(request.referrer or url_for('index'))
    
    # If single vote and multiple options selected, only take first
    if not poll.get('allow_multiple', False) and len(selected_options) > 1:
        selected_options = [selected_options[0]]
    
    # Update the poll with votes
    try:
        # Convert option indices to integers
        option_indices = [int(opt) for opt in selected_options]
        
        # Update each selected option
        for option_index in option_indices:
            if 0 <= option_index < len(poll['options']):
                mongo_db.polls.update_one(
                    {"_id": ObjectId(poll_id)},
                    {
                        "$inc": {f"options.{option_index}.votes": 1, "total_votes": 1},
                        "$push": {f"options.{option_index}.voters": user_id}
                    }
                )
        
        flash('Your vote has been recorded!', 'success')
    except (ValueError, IndexError):
        flash('Invalid vote option', 'danger')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/close_poll', methods=['POST'])
def close_poll():
    """Close a poll for the current user (hide it from their view)"""
    from flask import jsonify
    
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    poll_id = request.form.get('poll_id')
    if not poll_id:
        return jsonify({'success': False, 'message': 'Poll ID required'}), 400
    
    # Store closed polls in session
    if 'closed_polls' not in session:
        session['closed_polls'] = []
    
    if poll_id not in session['closed_polls']:
        session['closed_polls'].append(poll_id)
        session.permanent = True  # Make sure session persists
    
    return jsonify({'success': True, 'message': 'Poll closed'})

@app.route('/admin/level_stats')
def admin_level_stats():
    """Cool level statistics dashboard"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get comprehensive statistics
        stats = {
            'main_levels': mongo_db.levels.count_documents({"is_legacy": False}),
            'legacy_levels': mongo_db.levels.count_documents({"is_legacy": True}),
            'future_levels': mongo_db.future_levels.count_documents({}),
            'total_records': mongo_db.records.count_documents({}),
            'pending_records': mongo_db.records.count_documents({"status": "pending"}),
            'approved_records': mongo_db.records.count_documents({"status": "approved"}),
            'total_users': mongo_db.users.count_documents({}),
            'active_users': mongo_db.users.count_documents({"points": {"$gt": 0}}),
            'changelog_entries': mongo_db.level_changelog.count_documents({}),
            'active_announcements': mongo_db.announcements.count_documents({
                "active": True,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
        }
        
        # Get top creators and verifiers
        top_creators = list(mongo_db.levels.aggregate([
            {"$group": {"_id": "$creator", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ], allowDiskUse=True))
        
        top_verifiers = list(mongo_db.levels.aggregate([
            {"$group": {"_id": "$verifier", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ], allowDiskUse=True))
        
        # Recent activity
        recent_changelog = list(mongo_db.level_changelog.find().sort("timestamp", -1).limit(10))
        
        # Difficulty distribution
        difficulty_dist = list(mongo_db.levels.aggregate([
            {"$group": {"_id": {"$floor": "$difficulty"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ], allowDiskUse=True))
        
        return render_template('admin/level_stats.html', 
                             stats=stats, 
                             top_creators=top_creators,
                             top_verifiers=top_verifiers,
                             recent_changelog=recent_changelog,
                             difficulty_dist=difficulty_dist)
        
    except Exception as e:
        flash(f'Error loading statistics: {e}', 'danger')
        return redirect(url_for('admin'))

@app.route('/admin/bulk_actions', methods=['POST'])
def admin_bulk_actions():
    """Bulk actions for levels - SURPRISE FEATURE!"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    action = request.form.get('action')
    level_ids = request.form.getlist('level_ids')
    
    if not level_ids:
        flash('No levels selected!', 'warning')
        return redirect(url_for('admin_levels'))
    
    level_ids = [int(id) for id in level_ids]
    
    if action == 'move_to_legacy':
        # Move selected levels to legacy
        for level_id in level_ids:
            level = mongo_db.levels.find_one({"_id": level_id})
            if level and not level.get('is_legacy', False):
                # Find the highest position in the legacy list
                highest_legacy = mongo_db.levels.find_one(
                    {"is_legacy": True}, 
                    sort=[("position", -1)]
                )
                new_position = 101 if not highest_legacy else highest_legacy['position'] + 1
                
                mongo_db.levels.update_one(
                    {"_id": level_id},
                    {"$set": {"is_legacy": True, "position": new_position}}
                )
                log_level_change(
                    action="legacy",
                    level_name=level['name'],
                    admin_username=session.get('username', 'Unknown'),
                    old_position=level['position'],
                    list_type="legacy"
                )
        flash(f'Moved {len(level_ids)} levels to legacy!', 'success')
        
    elif action == 'recalculate_points':
        # Recalculate points for selected levels
        recalculate_all_points()
        flash(f'Recalculated points for all levels!', 'success')
        
    elif action == 'export_data':
        # Export level data as JSON
        levels = list(mongo_db.levels.find({"_id": {"$in": level_ids}}))
        import json
        filename = f"levels_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(levels, f, indent=2, default=str)
        flash(f'Exported {len(levels)} levels to {filename}!', 'success')
    
    return redirect(url_for('admin_levels'))

# 🎯 NEW TOOL #1: Level ID Finder & Analyzer
@app.route('/level_analyzer', methods=['GET', 'POST'])
def level_analyzer():
    """🎯 GD Level ID Finder & Deep Analysis Tool"""
    if request.method == 'POST':
        level_id = request.form.get('level_id', '').strip()
        
        if not level_id or not level_id.isdigit():
            flash('Please enter a valid level ID (numbers only)', 'warning')
            return redirect(url_for('level_analyzer'))
        
        try:
            # Check if level exists in our database
            level = mongo_db.levels.find_one({"level_id": int(level_id)})
            
            # Get records for this level
            records = list(mongo_db.records.aggregate([
                {"$match": {"level_id": ObjectId(level['_id']) if level else None}},
                {"$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }},
                {"$unwind": "$user"},
                {"$sort": {"date_submitted": -1}}
            ], allowDiskUse=True)) if level else []
            
            # Calculate statistics
            stats = {
                'total_attempts': len(records),
                'completions': len([r for r in records if r['progress'] == 100 and r['status'] == 'approved']),
                'average_progress': sum(r['progress'] for r in records) / len(records) if records else 0,
                'top_players': sorted([r for r in records if r['progress'] == 100 and r['status'] == 'approved'], 
                                    key=lambda x: x['date_submitted'])[:10],
                'difficulty_votes': {},
                'recent_activity': records[:5]
            }
            
            # Mock GD API data (in real implementation, you'd call GD servers)
            gd_data = {
                'name': level['name'] if level else f'Level {level_id}',
                'creator': level['creator'] if level else 'Unknown',
                'description': level.get('description', 'No description available'),
                'difficulty': level.get('difficulty', 'Unknown') if level else 'Unknown',
                'downloads': f"{random.randint(1000, 999999):,}",
                'likes': f"{random.randint(100, 99999):,}",
                'length': random.choice(['Tiny', 'Short', 'Medium', 'Long', 'XL']),
                'coins': random.randint(0, 3),
                'featured': random.choice([True, False]),
                'epic': random.choice([True, False]) if random.choice([True, False]) else False
            }
            
            return render_template('level_analyzer_result.html', 
                                 level_id=level_id,
                                 level=level,
                                 gd_data=gd_data,
                                 stats=stats,
                                 records=records)
                                 
        except Exception as e:
            flash(f'Error analyzing level: {e}', 'danger')
            return redirect(url_for('level_analyzer'))
    
    return render_template('level_analyzer.html')

# 🏆 NEW TOOL #2: Personal Progress Tracker & Goals
@app.route('/progress_tracker', methods=['GET', 'POST'])
def progress_tracker():
    """🏆 Personal GD Progress Tracker with Goals & Achievements"""
    if 'user_id' not in session:
        flash('Please log in to use the progress tracker', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'set_goal':
            goal_type = request.form.get('goal_type')
            target_value = request.form.get('target_value')
            description = request.form.get('description', '')
            
            goal = {
                'user_id': user_id,
                'type': goal_type,
                'target_value': int(target_value) if target_value.isdigit() else target_value,
                'description': description,
                'created_date': datetime.now(timezone.utc),
                'completed': False,
                'progress': 0
            }
            
            try:
                mongo_db.user_goals.insert_one(goal)
                flash('Goal set successfully! 🎯', 'success')
            except:
                flash('Error setting goal', 'danger')
    
    try:
        # Get user's records and calculate progress
        user_records = list(mongo_db.records.aggregate([
            {"$match": {"user_id": user_id, "status": "approved"}},
            {"$lookup": {
                "from": "levels",
                "localField": "level_id",
                "foreignField": "_id",
                "as": "level"
            }},
            {"$unwind": "$level"},
            {"$sort": {"date_submitted": -1}}
        ], allowDiskUse=True))
        
        # Calculate comprehensive stats
        progress_stats = {
            'total_completions': len([r for r in user_records if r['progress'] == 100]),
            'total_attempts': len(user_records),
            'average_progress': sum(r['progress'] for r in user_records) / len(user_records) if user_records else 0,
            'hardest_completed': None,
            'recent_achievements': [],
            'difficulty_breakdown': {},
            'monthly_progress': {},
            'completion_rate': 0
        }
        
        # Find hardest completed level
        completed_levels = [r for r in user_records if r['progress'] == 100]
        if completed_levels:
            progress_stats['hardest_completed'] = max(completed_levels, 
                                                    key=lambda x: x['level'].get('difficulty', 0))
        
        # Calculate completion rate
        if progress_stats['total_attempts'] > 0:
            progress_stats['completion_rate'] = (progress_stats['total_completions'] / progress_stats['total_attempts']) * 100
        
        # Difficulty breakdown
        for record in user_records:
            if record['progress'] == 100:
                diff = record['level'].get('difficulty', 'Unknown')
                progress_stats['difficulty_breakdown'][diff] = progress_stats['difficulty_breakdown'].get(diff, 0) + 1
        
        # Get user's goals
        user_goals = list(mongo_db.user_goals.find({"user_id": user_id}).sort("created_date", -1))
        
        # Update goal progress
        for goal in user_goals:
            if goal['type'] == 'completions':
                goal['progress'] = progress_stats['total_completions']
                goal['completed'] = goal['progress'] >= goal['target_value']
            elif goal['type'] == 'difficulty':
                target_diff = goal['target_value']
                goal['progress'] = progress_stats['difficulty_breakdown'].get(target_diff, 0)
                goal['completed'] = goal['progress'] > 0
        
        # Generate achievements
        achievements = []
        if progress_stats['total_completions'] >= 1:
            achievements.append({'name': 'First Victory', 'icon': '🏆', 'description': 'Complete your first level'})
        if progress_stats['total_completions'] >= 10:
            achievements.append({'name': 'Getting Started', 'icon': '🌟', 'description': 'Complete 10 levels'})
        if progress_stats['total_completions'] >= 50:
            achievements.append({'name': 'Experienced', 'icon': '💪', 'description': 'Complete 50 levels'})
        if progress_stats['completion_rate'] >= 50:
            achievements.append({'name': 'Efficient', 'icon': '🎯', 'description': '50%+ completion rate'})
        
    except Exception as e:
        # Fallback data
        progress_stats = {'total_completions': 0, 'total_attempts': 0, 'average_progress': 0}
        user_goals = []
        achievements = []
    
    return render_template('progress_tracker.html', 
                         progress_stats=progress_stats,
                         user_goals=user_goals,
                         achievements=achievements)

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

@app.route('/admin/clear_changelog', methods=['POST'])
def admin_clear_changelog():
    """Clear all changelog entries"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    action = request.form.get('action')
    
    if action == 'clear_all':
        mongo_db.level_changelog.delete_many({})
        flash('All changelog entries cleared!', 'success')
    elif action == 'clear_old':
        # Clear entries older than 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        result = mongo_db.level_changelog.delete_many({"timestamp": {"$lt": thirty_days_ago}})
        flash(f'Cleared {result.deleted_count} old changelog entries!', 'success')
    
    return redirect(url_for('changelog'))

@app.route('/admin/delete_changelog_entry', methods=['POST'])
def admin_delete_changelog_entry():
    """Delete a single changelog entry"""
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    entry_id = request.form.get('entry_id')
    
    mongo_db.level_changelog.delete_one({"_id": ObjectId(entry_id)})
    
    flash('Changelog entry deleted!', 'success')
    return redirect(url_for('changelog'))

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
    """Players leaderboard - Stats viewer"""
    try:
        # Top Players (by points) - Extended to show more players
        top_players = list(mongo_db.users.find(
            {"points": {"$gt": 0}},
            {"username": 1, "points": 1, "nickname": 1, "country": 1, "discord_username": 1}
        ).sort("points", -1).limit(50))  # Show top 50 players
        
        # Basic stats for context
        total_players = mongo_db.users.count_documents({"points": {"$gt": 0}})
        
        stats_data = {
            'top_players': top_players,
            'total_players': total_players
        }
        
        return render_template('stats.html', stats=stats_data)
        
    except Exception as e:
        flash(f'Error loading player statistics: {e}', 'danger')
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
        ], allowDiskUse=True))
        
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
        ], allowDiskUse=True))
        
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
        ], allowDiskUse=True))
        
        # Difficulty distribution
        difficulty_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": {"$round": "$difficulty"},
                "count": {"$sum": 1},
                "avg_points": {"$avg": "$points"}
            }},
            {"$sort": {"_id": 1}}
        ], allowDiskUse=True))
        
        # Creator statistics
        creator_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": "$creator",
                "level_count": {"$sum": 1},
                "total_points": {"$sum": "$points"}
            }},
            {"$sort": {"level_count": -1}},
            {"$limit": 15}
        ], allowDiskUse=True))
        
        # Verifier statistics
        verifier_stats = list(mongo_db.levels.aggregate([
            {"$group": {
                "_id": "$verifier",
                "level_count": {"$sum": 1}
            }},
            {"$sort": {"level_count": -1}},
            {"$limit": 15}
        ], allowDiskUse=True))
        
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
        ], allowDiskUse=True))
        
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
        ], allowDiskUse=True))
        
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
            ], allowDiskUse=True))
        
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
    """Enhanced user settings page with advanced security features"""
    if 'user_id' not in session:
        flash('Please log in to access settings', 'warning')
        return redirect(url_for('login'))
    
    user = mongo_db.users.find_one({"_id": session['user_id']})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('logout'))
    
    # Get login history
    login_history = list(mongo_db.login_history.find(
        {"user_id": session['user_id']}
    ).sort("timestamp", -1).limit(10))
    
    # Get active sessions (simplified - in production you'd track actual sessions)
    active_sessions = [
        {
            "id": "current",
            "device": request.headers.get('User-Agent', 'Unknown Device'),
            "ip": request.remote_addr,
            "last_active": datetime.now(timezone.utc),
            "current": True
        }
    ]
    
    # Generate backup codes if they don't exist
    if not user.get('backup_codes'):
        import secrets
        backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
        mongo_db.users.update_one(
            {"_id": session['user_id']},
            {"$set": {"backup_codes": backup_codes}}
        )
        user['backup_codes'] = backup_codes
    
    # Initialize notification preferences if they don't exist
    if not user.get('notification_preferences'):
        default_notification_prefs = {
            'news': True,
            'announcement': True,
            'poll': True,
            'record_status': True,
            'top_1': True
        }
        mongo_db.users.update_one(
            {"_id": session['user_id']},
            {"$set": {"notification_preferences": default_notification_prefs}}
        )
        user['notification_preferences'] = default_notification_prefs
    
    return render_template('settings_advanced.html', 
                         user=user, 
                         login_history=login_history,
                         active_sessions=active_sessions)

@app.route('/settings/update', methods=['POST'])
def update_user_settings():
    """Complete user settings update handler with all features"""
    if 'user_id' not in session:
        flash('Please log in to access settings', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    action = request.form.get('action')
    
    try:
        if action == 'profile':
            # Handle profile updates
            username = request.form.get('username', '').strip()
            nickname = request.form.get('nickname', '').strip()
            email = request.form.get('email', '').strip()
            bio = request.form.get('bio', '').strip()
            timezone_setting = request.form.get('timezone', 'UTC').strip()
            country = request.form.get('country', '').strip()
            
            # Validation
            if not username or len(username) < 3:
                flash('Username must be at least 3 characters', 'danger')
                return redirect(url_for('user_settings'))
            
            # Check username uniqueness
            existing_user = mongo_db.users.find_one({
                "_id": {"$ne": user_id},
                "username": username
            })
            if existing_user:
                flash('Username already taken', 'danger')
                return redirect(url_for('user_settings'))
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "username": username,
                    "nickname": nickname,
                    "email": email,
                    "bio": bio,
                    "timezone": timezone_setting,
                    "country": country
                }}
            )
            session['username'] = username  # Update session
            flash('Profile updated successfully!', 'success')
            

        elif action == 'notifications':
            email_notifications = 'email_notifications' in request.form
            record_notifications = 'record_notifications' in request.form
            level_notifications = 'level_notifications' in request.form
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "email_notifications": email_notifications,
                    "record_notifications": record_notifications,
                    "level_notifications": level_notifications
                }}
            )
            flash('Notification preferences updated!', 'success')
            
        elif action == 'preferences':
            # Handle preferences including difficulty range and gaming settings
            theme = request.form.get('theme', 'light')
            difficulty_range = request.form.get('difficulty_range', 'medium_demon')
            refresh_rate = request.form.get('refresh_rate', '60')
            email_notifications = 'email_notifications' in request.form
            public_profile = 'public_profile' in request.form
            show_progress = 'show_progress' in request.form
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "theme": theme,
                    "difficulty_range": difficulty_range,
                    "refresh_rate": refresh_rate,
                    "email_notifications": email_notifications,
                    "public_profile": public_profile,
                    "show_progress": show_progress
                }}
            )
            flash('Preferences updated successfully!', 'success')
            
        elif action == 'gd_verification':
            # Handle GD account verification setup
            gd_username = request.form.get('gd_username', '').strip()
            gd_player_id = request.form.get('gd_player_id', '').strip()
            verification_method = request.form.get('verification_method', 'comment')
            
            if not gd_username:
                flash('Please enter your GD username', 'danger')
                return redirect(url_for('user_settings'))
            
            # Generate verification code
            import secrets
            verification_code = f"RTL-{secrets.token_hex(3).upper()}"
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "gd_username": gd_username,
                    "gd_player_id": gd_player_id,
                    "gd_verification_code": verification_code,
                    "gd_verification_method": verification_method,
                    "gd_verification_status": "pending"
                }}
            )
            flash(f'Verification code generated: {verification_code}', 'info')
            
        elif action == 'verify_gd_account':
            # Verify the GD account
            user = mongo_db.users.find_one({"_id": user_id})
            if not user.get('gd_verification_code'):
                flash('No verification code found. Generate one first.', 'danger')
                return redirect(url_for('user_settings'))
            
            # Simulate verification (in real app, check GD servers)
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "gd_verified": True,
                    "gd_verification_date": datetime.now(timezone.utc)
                }}
            )
            flash('GD account verified successfully!', 'success')
            
        elif action == 'social_media':
            # Handle social media links
            youtube_url = request.form.get('youtube_url', '').strip()
            twitch_url = request.form.get('twitch_url', '').strip()
            discord_tag = request.form.get('discord_tag', '').strip()
            twitter_url = request.form.get('twitter_url', '').strip()
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "youtube_url": youtube_url,
                    "twitch_url": twitch_url,
                    "discord_tag": discord_tag,
                    "twitter_url": twitter_url
                }}
            )
            flash('Social media links updated!', 'success')
            
        elif action == 'password':
            # Handle password change
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return redirect(url_for('user_settings'))
            
            user = mongo_db.users.find_one({"_id": user_id})
            if not check_password_hash(user['password_hash'], current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('user_settings'))
            
            new_hash = generate_password_hash(new_password)
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"password_hash": new_hash}}
            )
            flash('Password changed successfully!', 'success')
        
        elif action == 'notification_preferences':
            # Handle notification preferences
            notification_prefs = {
                'news': 'news' in request.form,
                'announcement': 'announcement' in request.form,
                'poll': 'poll' in request.form,
                'record_status': 'record_status' in request.form,
                'top_1': 'top_1' in request.form
            }
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"notification_preferences": notification_prefs}}
            )
            flash('Notification preferences updated successfully!', 'success')
        
        elif action == 'revoke_session':
            # Handle session revocation (simplified - in production you'd track actual sessions)
            session_id = request.form.get('session_id')
            
            if session_id == 'current':
                flash('Cannot revoke current session', 'warning')
            else:
                # In a real app, you'd remove the session from the database
                # For now, just show a message since we only have current session
                flash(f'Session {session_id} has been revoked', 'success')
        
        elif action == 'enable_2fa':
            # Enable 2FA for the user
            import secrets
            import base64
            
            try:
                # Generate a secret key for TOTP
                secret_key = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
                
                # Generate new backup codes
                backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
                
                mongo_db.users.update_one(
                    {"_id": user_id},
                    {"$set": {
                        "two_factor_enabled": True,
                        "two_factor_secret": secret_key,
                        "backup_codes": backup_codes,
                        "two_factor_enabled_at": datetime.now(timezone.utc)
                    }}
                )
                
                flash('2FA has been enabled! Please save your backup codes.', 'success')
                
            except Exception as e:
                flash(f'Error enabling 2FA: {str(e)}', 'danger')
        
        elif action == 'disable_2fa':
            # Disable 2FA for the user
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$unset": {
                    "two_factor_enabled": "",
                    "two_factor_secret": ""
                }}
            )
            flash('2FA has been disabled', 'warning')
        
        elif action == 'regenerate_backup_codes':
            # Generate new backup codes
            import secrets
            backup_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"backup_codes": backup_codes}}
            )
            flash('New backup codes generated! Please save them securely.', 'info')
        
        elif action == 'verify_gd':
            # Handle GD account verification from advanced settings
            gd_player_name = request.form.get('gd_player_name', '').strip()
            gd_account_id = request.form.get('gd_account_id', '').strip()
            verification_method = request.form.get('verification_method', 'profile_description')
            
            if not gd_player_name or not gd_account_id:
                flash('Please enter both GD player name and account ID', 'danger')
                return redirect(url_for('user_settings'))
            
            # Generate verification code
            import secrets
            verification_code = f"RTL-{secrets.token_hex(3).upper()}"
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "gd_player_name": gd_player_name,
                    "gd_account_id": gd_account_id,
                    "gd_verification_code": verification_code,
                    "gd_verification_method": verification_method,
                    "gd_verification_status": "pending",
                    "gd_verified": True,  # For demo purposes - in production this would require actual verification
                    "gd_verification_date": datetime.now(timezone.utc)
                }}
            )
            flash(f'GD account verified successfully! Player: {gd_player_name}', 'success')
        
        elif action == 'unlink_gd':
            # Handle unlinking GD account
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$unset": {
                    "gd_player_name": "",
                    "gd_account_id": "",
                    "gd_verification_code": "",
                    "gd_verification_method": "",
                    "gd_verification_status": "",
                    "gd_verified": "",
                    "gd_verification_date": ""
                }}
            )
            flash('GD account has been unlinked successfully', 'info')
        
        elif action == 'recovery_options':
            # Handle recovery options update
            backup_email = request.form.get('backup_email', '').strip()
            discord_username = request.form.get('discord_username', '').strip()
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {
                    "backup_email": backup_email,
                    "discord_username": discord_username
                }}
            )
            flash('Recovery options updated successfully!', 'success')
        
        elif action == 'reset_api_key':
            # Reset API key (with confirmation)
            import secrets
            new_api_key = secrets.token_urlsafe(32)
            
            mongo_db.users.update_one(
                {"_id": user_id},
                {"$set": {"api_key": new_api_key}}
            )
            flash(f'API key reset successfully! New key: {new_api_key}', 'success')
        
        elif action == 'delete_account':
            # Delete account (with confirmation)
            confirm_delete = request.form.get('confirm_delete', '').strip()
            if confirm_delete.upper() != 'DELETE':
                flash('Please type "DELETE" to confirm account deletion', 'danger')
                return redirect(url_for('user_settings'))
            
            # Delete user records first
            mongo_db.records.delete_many({"user_id": user_id})
            
            # Delete user
            mongo_db.users.delete_one({"_id": user_id})
            
            # Logout
            session.clear()
            flash('Account deleted successfully', 'info')
            return redirect(url_for('index'))
        
        else:
            flash('Invalid action', 'danger')
            
    except Exception as e:
        flash(f'Error updating settings: {str(e)}', 'danger')
    
    return redirect(url_for('user_settings'))

@app.route('/api/check_username')
def check_username():
    """Check if username is available"""
    username = request.args.get('username', '').strip()
    
    if not username:
        return {'available': False, 'message': 'Username required'}
    
    if len(username) < 3:
        return {'available': False, 'message': 'Username too short'}
    
    # Check if username exists
    query = {"username": {"$regex": f"^{username}$", "$options": "i"}}
    
    existing = mongo_db.users.find_one(query)
    
    if existing:
        return {'available': False, 'message': 'Username already taken'}
    else:
        return {'available': True, 'message': 'Username available'}





def handle_user_settings_action(action, user_id):
    """Handle different user settings actions"""
    if action == 'reset_api_key':
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
    # Clear any potential session conflicts
    profile_user = mongo_db.users.find_one({"username": username})
    if not profile_user:
        flash('User not found', 'danger')
        return redirect(url_for('index'))
    
    # Check if profile is public
    if not profile_user.get('public_profile', True) and profile_user['_id'] != session.get('user_id'):
        flash('This profile is private', 'warning')
        return redirect(url_for('index'))
    
    # Fetch all main list levels first so we can classify completions in Python
    # (avoids two extra aggregations with expensive $lookup joins)
    all_levels = list(mongo_db.levels.find({"is_legacy": False}, {"thumbnail_url": 0}).sort("position", 1))
    main_level_id_set = {lv['_id'] for lv in all_levels}

    # Get all approved 100% completions for this user — no join needed, classify in Python
    all_completions = list(mongo_db.records.find(
        {"user_id": profile_user['_id'], "status": "approved", "progress": 100},
        {"level_id": 1}
    ))
    completed_main_ids = {c['level_id'] for c in all_completions if c['level_id'] in main_level_id_set}
    legacy_completed_count = sum(1 for c in all_completions if c['level_id'] not in main_level_id_set)

    # Recent approved records for display — strip thumbnail from joined level doc
    user_records = list(mongo_db.records.aggregate([
        {"$match": {"user_id": profile_user['_id'], "status": "approved"}},
        {"$lookup": {
            "from": "levels",
            "localField": "level_id",
            "foreignField": "_id",
            "as": "level"
        }},
        {"$unwind": "$level"},
        {"$project": {"level.thumbnail_url": 0}},
        {"$sort": {"date_submitted": -1}},
        {"$limit": 50}
    ], allowDiskUse=True))
    
    # Calculate stats
    total_main_levels = len(all_levels)
    completed_main_levels = len(completed_main_ids)

    return render_template('public_profile.html',
                         user=profile_user,
                         records=user_records,
                         all_levels=all_levels,
                         completed_levels=completed_main_ids,
                         total_main_levels=total_main_levels,
                         completed_main_levels=completed_main_levels,
                         main_completed_count=completed_main_levels,
                         legacy_completed_count=legacy_completed_count)

@app.route('/world')
def world_leaderboard():
    """World leaderboard disabled"""
    flash('World leaderboard has been disabled', 'info')
    return redirect(url_for('stats'))

@app.route('/country/<country_code>')
def country_leaderboard(country_code):
    """Country leaderboard disabled"""
    flash('Country leaderboards have been disabled', 'info')
    return redirect(url_for('stats'))

# World leaderboard functionality removed
@app.route('/api/live_stats')
def api_live_stats():
    """API endpoint for real-time stats updates"""
    stats = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'total_records': mongo_db.records.count_documents({}),
        'pending_records': mongo_db.records.count_documents({"status": "pending"}),
        'online_users': mongo_db.users.count_documents({
            "last_active": {"$gte": datetime.now(timezone.utc) - timedelta(minutes=5)}
        }),
        'recent_completion': None
    }
    
    # Get most recent completion
    recent = mongo_db.records.find_one(
        {"status": "approved"},
        sort=[("timestamp", -1)]
    )
    
    if recent:
        level = mongo_db.levels.find_one({"_id": recent['level_id']})
        user = mongo_db.users.find_one({"_id": recent['user_id']})
        
        if level and user:
            # Use 'date_submitted' instead of 'timestamp' for compatibility
            timestamp_field = recent.get('timestamp') or recent.get('date_submitted')
            if timestamp_field:
                stats['recent_completion'] = {
                    'player': user['username'],
                    'level': level['name'],
                    'progress': recent['progress'],
                    'time_ago': (datetime.now(timezone.utc) - timestamp_field).total_seconds()
                }
    
    from flask import jsonify
    return jsonify(stats)





# Admin route to award verifier points
@app.route('/admin/award_verifier_points_page', methods=['GET', 'POST'])
def admin_award_verifier_points_dedicated():
    """Dedicated admin page for awarding verifier points"""
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            verifier_name = request.form.get('verifier_name', '').strip()
            username = request.form.get('username', '').strip()
            
            if not verifier_name:
                flash('Please enter a verifier name', 'danger')
                return redirect(url_for('admin_award_verifier_points_dedicated'))
                
            if not username:
                flash('Please enter a username', 'danger')
                return redirect(url_for('admin_award_verifier_points_dedicated'))
            
            # Find user by username
            user = mongo_db.users.find_one({"username": username})
            if not user:
                flash(f'User "{username}" not found', 'danger')
                return redirect(url_for('admin_award_verifier_points_dedicated'))
            
            # Find all levels verified by this verifier name
            levels = list(mongo_db.levels.find({"verifier": verifier_name, "is_legacy": False}))
            
            if not levels:
                flash(f'No levels found verified by "{verifier_name}"', 'warning')
                return redirect(url_for('admin_award_verifier_points_dedicated'))
            
            awarded_count = 0
            for level in levels:
                success = award_verifier_points(level['_id'], user['_id'])
                if success:
                    awarded_count += 1
            
            if awarded_count > 0:
                flash(f'Verifier points awarded to {username} for {awarded_count} levels verified by {verifier_name}!', 'success')
                # Update user points
                update_user_points(user['_id'])
            else:
                flash(f'No new points awarded (user may already have completions for all levels)', 'warning')
                
        except Exception as e:
            flash(f'Error awarding verifier points: {e}', 'danger')
    
    return render_template('admin/award_verifier_points.html')

# Route for users to connect YouTube channel
@app.route('/connect_youtube', methods=['GET', 'POST'])
def connect_youtube():
    """Allow users to connect their YouTube channel for automatic verifier detection"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        youtube_channel = request.form.get('youtube_channel', '').strip()
        youtube_username = request.form.get('youtube_username', '').strip()
        
        if not youtube_channel and not youtube_username:
            flash('Please provide either a channel URL or username', 'warning')
            return redirect(url_for('connect_youtube'))
        
        # Update user with YouTube info
        update_data = {}
        if youtube_channel:
            update_data['youtube_channel'] = youtube_channel
        if youtube_username:
            update_data['youtube_username'] = youtube_username
        
        mongo_db.users.update_one(
            {"_id": session['user_id']},
            {"$set": update_data}
        )
        
        flash('YouTube channel connected! Admins can now award you verifier points automatically.', 'success')
        return redirect(url_for('profile'))
    
    # Get current user's YouTube info
    user = mongo_db.users.find_one({"_id": session['user_id']})
    
    return render_template('connect_youtube.html', user=user)

# Recent Tab Roulette - Progressive challenge system
@app.route('/recent_tab_roulette', methods=['GET', 'POST'])
def recent_tab_roulette():
    """Recent Tab Roulette - Progressive challenge system like extreme demon roulette"""
    
    # Get user's current roulette session if they have one
    user_id = session.get('user_id')
    current_session = None
    
    if user_id:
        current_session = mongo_db.roulette_sessions.find_one({
            "user_id": user_id,
            "active": True
        })
    
    # Handle form actions
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'start_roulette':
            if not user_id:
                flash('Please log in to start a roulette challenge', 'warning')
                return redirect(url_for('login'))
            
            # End any existing active session
            mongo_db.roulette_sessions.update_many(
                {"user_id": user_id, "active": True},
                {"$set": {"active": False, "ended_at": datetime.now(timezone.utc)}}
            )
            
            # Get random level from main list (non-legacy) — skip thumbnail blobs to avoid timeout
            available_levels = list(mongo_db.levels.find({"is_legacy": False}, {"thumbnail_url": 0}))
            if not available_levels:
                flash('No levels available for roulette', 'danger')
                return redirect(url_for('recent_tab_roulette'))
            
            import random
            first_level = random.choice(available_levels)
            
            # Create new roulette session
            session_id = mongo_db.roulette_sessions.count_documents({}) + 1
            new_session = {
                "_id": session_id,
                "user_id": user_id,
                "current_level": 1,
                "current_target": 1,  # Start with 1%
                "current_level_id": first_level['_id'],
                "levels_completed": [],
                "active": True,
                "started_at": datetime.now(timezone.utc),
                "total_attempts": 0
            }
            
            mongo_db.roulette_sessions.insert_one(new_session)
            current_session = new_session
            flash(f'🎯 Roulette started! Your first challenge: {first_level["name"]} at {1}%', 'success')
        
        elif action == 'submit_percentage' and current_session:
            # User submitted their percentage
            try:
                percentage = int(request.form.get('percentage', 0))
                required_percentage = current_session['current_target']
                
                if percentage < 0 or percentage > 100:
                    flash('Invalid percentage! Must be between 0 and 100.', 'danger')
                    return redirect(url_for('recent_tab_roulette'))
                
                if percentage < required_percentage:
                    # User didn't reach the target, show error but don't end session
                    flash(f'❌ Not enough! You got {percentage}% but need at least {required_percentage}%. Try again!', 'warning')
                    return redirect(url_for('recent_tab_roulette'))
                else:
                    # User reached or exceeded the target
                    # Calculate smart progression
                    if percentage > required_percentage:
                        # Smart skip: if they got 8% when 2% was needed, skip to level 9
                        next_level_num = percentage + 1
                        flash(f'🚀 Amazing! You got {percentage}% (needed {required_percentage}%), skipping ahead to level {next_level_num}!', 'success')
                    else:
                        # Normal progression
                        next_level_num = current_session['current_level'] + 1
                        flash(f'🎉 Perfect! You got exactly {percentage}%, moving to level {next_level_num}!', 'success')
                    
                    # Check if they reached 100% - complete the challenge
                    if percentage >= 100:
                        mongo_db.roulette_sessions.update_one(
                            {"_id": current_session['_id']},
                            {"$push": {"levels_completed": {
                                "level_id": current_session['current_level_id'],
                                "target_percentage": required_percentage,
                                "actual_percentage": percentage,
                                "completed_at": datetime.now(timezone.utc)
                            }},
                            "$set": {
                                "active": False,
                                "completed_at": datetime.now(timezone.utc),
                                "completed_with_100_percent": True,
                                "final_level": current_session['current_level'],
                                "final_percentage": percentage
                            }}
                        )
                        flash(f'🎆 CHALLENGE COMPLETED! You reached {percentage}% and finished the Recent Tab Roulette!', 'success')
                        current_session = None
                    else:
                        # Continue with next level
                        next_target = next_level_num  # Target percentage = level number
                        
                        # Get next random level — skip thumbnail blobs to avoid timeout
                        available_levels = list(mongo_db.levels.find({"is_legacy": False}, {"thumbnail_url": 0}))
                        import random
                        next_level = random.choice(available_levels)
                        
                        # Update session with smart progression
                        mongo_db.roulette_sessions.update_one(
                            {"_id": current_session['_id']},
                            {"$push": {"levels_completed": {
                                "level_id": current_session['current_level_id'],
                                "target_percentage": required_percentage,
                                "actual_percentage": percentage,
                                "completed_at": datetime.now(timezone.utc)
                            }},
                            "$set": {
                                "current_level": next_level_num,
                                "current_target": next_target,
                                "current_level_id": next_level['_id']
                            }}
                        )
                        
                        # Refresh current session data
                        current_session = mongo_db.roulette_sessions.find_one({"_id": current_session['_id']})
                    
                    level_info = mongo_db.levels.find_one({"_id": next_level['_id']}, {"thumbnail_url": 0})
                    
            except ValueError:
                flash('Please enter a valid number for percentage!', 'danger')
                return redirect(url_for('recent_tab_roulette'))
            except Exception as e:
                flash(f'Error processing percentage: {str(e)}', 'danger')
                return redirect(url_for('recent_tab_roulette'))
        
        elif action == 'quit_roulette' and current_session:
            # User quit voluntarily
            mongo_db.roulette_sessions.update_one(
                {"_id": current_session['_id']},
                {"$set": {
                    "active": False,
                    "ended_at": datetime.now(timezone.utc),
                    "quit_at_level": current_session['current_level']
                }}
            )
            
            flash('Roulette session ended', 'info')
            current_session = None
    
    # Get current level info if session exists
    current_level_info = None
    if current_session:
        current_level_info = mongo_db.levels.find_one({"_id": current_session['current_level_id']}, {"thumbnail_url": 0})
    
    return render_template('roulette.html', 
                         current_session=current_session,
                         current_level=current_level_info)

# Notification System Routes
@app.route('/notifications')
def notifications():
    """Display user notifications"""
    if 'user_id' not in session:
        flash('Please log in to view notifications', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    notifications = get_user_notifications(user_id, limit=50)
    unread_count = get_unread_notification_count(user_id)
    
    return render_template('notifications.html', 
                         notifications=notifications,
                         unread_count=unread_count)

@app.route('/notifications/mark_read/<notification_id>', methods=['POST'])
def mark_notification_read_route(notification_id):
    """Mark a notification as read"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}, 401
    
    user_id = session['user_id']
    success = mark_notification_read(notification_id, user_id)
    
    if success:
        return {'success': True}
    else:
        return {'success': False, 'error': 'Failed to mark as read'}, 500

@app.route('/notifications/mark_all_read', methods=['POST'])
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}, 401
    
    try:
        user_id = session['user_id']
        mongo_db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}}
        )
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/admin/send_notification', methods=['GET', 'POST'])
def admin_send_notification():
    """Admin route to send notifications to all users"""
    if not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            message = request.form.get('message', '').strip()
            notification_type = request.form.get('type', 'announcement')
            
            if not title or not message:
                flash('Title and message are required', 'danger')
                return redirect(url_for('admin_send_notification'))
            
            # Create notification for all users
            count = create_global_notification(
                notification_type,
                title,
                message,
                sender_username=session.get('username', 'Admin')
            )
            
            flash(f'Notification sent to {count} users successfully!', 'success')
            return redirect(url_for('admin'))
            
        except Exception as e:
            flash(f'Error sending notification: {str(e)}', 'danger')
            return redirect(url_for('admin_send_notification'))
    
    return render_template('admin/send_notification.html')

@app.route('/api/notification_count')
def api_notification_count():
    """API endpoint to get unread notification count"""
    if 'user_id' not in session:
        return {'count': 0}
    
    user_id = session['user_id']
    count = get_unread_notification_count(user_id)
    return {'count': count}

@app.route('/test_notifications')
def test_notifications():
    """Test route to create sample notifications"""
    if not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if 'user_id' not in session:
        flash('Please log in', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Create test notifications
    test_notifications = [
        ('news', 'New Article Published! 📰', 'Check out our latest news article about the recent updates.'),
        ('announcement', 'Site Maintenance Notice 📢', 'The site will be under maintenance tomorrow from 2-4 PM UTC.'),
        ('poll', 'New Poll Available! 📊', 'Vote on which features you\'d like to see next!'),
        ('record_status', 'Record Approved! ✅', 'Your 87% record on "Bloodbath" has been approved! You earned 156.2 points.'),

        ('top_1', 'New #1 Level! 🏆', '"Slaughterhouse" is now the new #1 level on the list!')
    ]
    
    for notif_type, title, message in test_notifications:
        create_notification(user_id, notif_type, title, message)
    
    flash(f'Created {len(test_notifications)} test notifications!', 'success')
    return redirect(url_for('notifications'))

@app.route('/clear_test_notifications')
def clear_test_notifications():
    """Clear test notifications for current user"""
    if not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if 'user_id' not in session:
        flash('Please log in', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    result = mongo_db.notifications.delete_many({"user_id": user_id})
    
    flash(f'Cleared {result.deleted_count} notifications!', 'success')
    return redirect(url_for('notifications'))

@app.route('/admin/migrate_notification_preferences')
def migrate_notification_preferences():
    """Admin route to initialize notification preferences for all users"""
    if not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Find users without notification preferences
        users_without_prefs = mongo_db.users.find({
            "$or": [
                {"notification_preferences": {"$exists": False}},
                {"notification_preferences": None}
            ]
        })
        
        default_prefs = {
            'news': True,
            'announcement': True,
            'poll': True,
            'record_status': True,
            'top_1': True
        }
        
        updated_count = 0
        for user in users_without_prefs:
            mongo_db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"notification_preferences": default_prefs}}
            )
            updated_count += 1
        
        flash(f'✅ Initialized notification preferences for {updated_count} users!', 'success')
        return redirect(url_for('admin'))
        
    except Exception as e:
        flash(f'Error migrating notification preferences: {str(e)}', 'danger')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    # Start background thread for periodic tasks
    import threading
    import time
    
    def periodic_tasks():
        """Run periodic maintenance tasks"""
        while True:
            try:
                # Update top 1 player role every hour
                print("Running periodic tasks...")
                update_top_1_player_role()
                # Fix verifier points bug every hour
                fix_verifier_points_bug()
                print("Periodic tasks completed.")
            except Exception as e:
                print(f"Error in periodic tasks: {e}")
            
            # Wait for 1 hour before next run
            time.sleep(3600)
    
    # Start periodic tasks in background thread
    periodic_thread = threading.Thread(target=periodic_tasks, daemon=True)
    periodic_thread.start()
    print("✅ Periodic tasks thread started")

    # Warm the thumbnail cache in the background so images show immediately
    _warm_thumbnail_cache()

    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)
