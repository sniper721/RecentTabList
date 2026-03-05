from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

# MongoDB setup
try:
    MONGODB_URI = os.environ.get('MONGODB_URI')
    client = MongoClient(MONGODB_URI)
    mongo_db = client[os.environ.get('MONGODB_DB', 'rtl_database')]
    print("✅ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongo_db = None

# OAuth setup
oauth = OAuth(app)

# Configure Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    print("✅ Google OAuth configured")

# Configure Discord OAuth
DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')

if DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET:
    discord = oauth.register(
        name='discord',
        client_id=DISCORD_CLIENT_ID,
        client_secret=DISCORD_CLIENT_SECRET,
        access_token_url='https://discord.com/api/oauth2/token',
        authorize_url='https://discord.com/api/oauth2/authorize',
        api_base_url='https://discord.com/api/',
        client_kwargs={
            'scope': 'identify email guilds'
        }
    )
    print("✅ Discord OAuth configured")

# Simple cache for levels
levels_cache = {
    'main_list': [],
    'legacy_list': [],
    'last_updated': None
}

def get_cached_levels(is_legacy=False):
    """Get cached levels list"""
    cache_key = 'legacy_list' if is_legacy else 'main_list'
    if levels_cache[cache_key] and levels_cache['last_updated']:
        # Cache is valid for 5 minutes
        if datetime.now(timezone.utc) - levels_cache['last_updated'] < timedelta(minutes=5):
            return levels_cache[cache_key]
    return []

@app.route('/')
def index():
    """Simple index route"""
    try:
        # Try to get some basic data
        if mongo_db:
            user_count = mongo_db.users.count_documents({})
            level_count = mongo_db.levels.count_documents({"is_legacy": False})
            record_count = mongo_db.records.count_documents({})
        else:
            user_count = 0
            level_count = 0
            record_count = 0
            
        return f"""
        <h1>Recent Tab List</h1>
        <p>Welcome to the Recent Tab List website!</p>
        <div style="margin: 20px 0;">
            <h2>Statistics</h2>
            <ul>
                <li>Users: {user_count}</li>
                <li>Levels: {level_count}</li>
                <li>Records: {record_count}</li>
            </ul>
        </div>
        <div style="margin: 20px 0;">
            <h2>Quick Links</h2>
            <ul>
                <li><a href="/login">Login</a></li>
                <li><a href="/register">Register</a></li>
                <li><a href="/levels">View Levels</a></li>
            </ul>
        </div>
        """
    except Exception as e:
        return f"<h1>Recent Tab List</h1><p>Site is running but encountered an error: {str(e)}</p>"

@app.route('/login')
def login():
    return "<h1>Login Page</h1><p>Login functionality would go here.</p>"

@app.route('/register')
def register():
    return "<h1>Register Page</h1><p>Registration functionality would go here.</p>"

@app.route('/levels')
def levels():
    return "<h1>Levels Page</h1><p>Levels would be displayed here.</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"✅ Starting Flask app on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)