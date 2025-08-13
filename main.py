from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime, timezone
from discord_integration import notify_record_submitted, notify_record_approved, notify_record_rejected
from dotenv import load_dotenv
from bson.objectid import ObjectId
from bson.errors import InvalidId

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
try:
    print(f"MongoDB URI: {mongodb_uri[:50]}...")
    print(f"MongoDB DB: {mongodb_db}")
    mongo_client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=2000,
        socketTimeoutMS=2000,
        connectTimeoutMS=2000
    )
    mongo_db = mongo_client[mongodb_db]
    # Test connection
    mongo_client.admin.command('ping')
    print("✓ MongoDB initialized successfully")
    # Create indexes for better performance
    try:
        mongo_db.levels.create_index([("is_legacy", 1), ("position", 1)])
        print("✓ Database indexes created")
    except Exception as e:
        print(f"Index creation warning: {e}")
except Exception as e:
    print(f"MongoDB initialization error: {e}")
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

# Helper functions
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
    
    # Get current theme from session
    current_theme = session.get('theme', 'light')
    
    return dict(
        format_points=format_points, 
        get_video_embed_info=get_video_embed_info,
        current_theme=current_theme
    )

def calculate_level_points(position, is_legacy=False, level_type="Level"):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    # Position 1 = exponent 0, Position 2 = exponent 1, etc.
    return int(250 * (0.9475 ** (position - 1)))

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    if record['status'] != 'approved' or level.get('is_legacy', False):
        return 0
    
    # Full completion
    if record['progress'] == 100:
        return level['points']
    
    # List% completion (10% of full points for any progress >= min_percentage)
    if record['progress'] >= level.get('min_percentage', 100):
        return level['points'] * 0.1
    
    return 0

def update_user_points(user_id):
    """Recalculate and update user's total points"""
    records = list(mongo_db.records.find({"user_id": user_id, "status": "approved"}))
    total_points = 0
    
    for record in records:
        level = mongo_db.levels.find_one({"_id": record['level_id']})
        if level:
            total_points += calculate_record_points(record, level)
    
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
    """Recalculate points for all levels based on their current positions"""
    levels = list(mongo_db.levels.find())
    for level in levels:
        new_points = calculate_level_points(level['position'], level.get('is_legacy', False))
        if level.get('points') != new_points:
            mongo_db.levels.update_one(
                {"_id": level['_id']},
                {"$set": {"points": new_points}}
            )

print("Setting up routes...")

@app.route('/test')
def test():
    return "<h1>Test route works!</h1>"

@app.route('/')
def index():
    print("Index route accessed")
    try:
        print("Querying database...")
        # Quick test query first
        mongo_db.levels.find_one()
        print("Database responsive")
        main_list = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
        print(f"Found {len(main_list)} levels")
        print("Rendering template...")
        result = render_template('index.html', levels=main_list)
        print("Template rendered successfully")
        return result
    except Exception as e:
        print(f"Error in index: {e}")
        return render_template('index.html', levels=[])

# Routes

@app.route('/legacy')
def legacy():
    legacy_list = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1))
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
            }).sort("position", 1))
        except ValueError:
            flash('Invalid date format', 'danger')
    
    return render_template('timemachine.html', levels=levels, selected_date=selected_date)

@app.route('/level/<level_id>')
def level_detail(level_id):
    try:
        level = mongo_db.levels.find_one({"_id": int(level_id)})
        if not level:
            flash('Level not found', 'danger')
            return redirect(url_for('index'))
        
        # Get approved records with user info
        records = list(mongo_db.records.aggregate([
            {"$match": {"level_id": int(level_id), "status": "approved"}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user"
            }},
            {"$unwind": "$user"}
        ]))
        
        return render_template('level_detail.html', level=level, records=records)
    except (ValueError, InvalidId):
        flash('Invalid level ID', 'danger')
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = mongo_db.users.find_one({"username": username})
        
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
        if mongo_db.users.find_one({"username": username}):
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if mongo_db.users.find_one({"email": email}):
            flash('Email already exists', 'danger')
            return render_template('register.html')
        
        # Get next user ID
        last_user = mongo_db.users.find_one(sort=[("_id", -1)])
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
    
    user = mongo_db.users.find_one({"_id": session['user_id']})
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
        
        # Check for empty fields
        if not level_id_str:
            flash('Please select a level', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
            
        if not progress_str:
            flash('Please enter your progress percentage', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
            
        if not video_url:
            flash('Please provide a video URL', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
        
        # Convert to integers
        try:
            level_id = int(level_id_str)
            progress = int(progress_str)
        except ValueError:
            flash('Invalid level ID or progress value', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
        
        # Validate progress range
        if progress < 1 or progress > 100:
            flash('Progress must be between 1 and 100', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
        
        # Check if level exists
        level = mongo_db.levels.find_one({"_id": level_id})
        if not level:
            flash('Selected level does not exist', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
            return render_template('submit_record.html', levels=levels)
        
        # Check minimum progress requirement
        min_progress = level.get('min_percentage', 100)
        if progress < min_progress:
            flash(f'This level requires at least {min_progress}% progress', 'danger')
            levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
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
            notify_record_submitted(username, level['name'], progress, video_url)
        except Exception as e:
            print(f"Discord notification error: {e}")
        
        flash('Record submitted successfully! It will be reviewed by moderators.', 'success')
        return redirect(url_for('profile'))
    
    levels = list(mongo_db.levels.find({"is_legacy": {"$ne": True}}).sort("position", 1))
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
        
        # Recalculate points for all levels after position changes
        recalculate_all_points()
        
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
    
    levels = list(mongo_db.levels.find().sort([("is_legacy", 1), ("position", 1)]))
    
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
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    record = mongo_db.records.find_one({"_id": record_id})
    if record:
        mongo_db.records.update_one(
            {"_id": record_id},
            {"$set": {"status": "approved"}}
        )
        
        # Update user points
        update_user_points(record['user_id'])
        
        # Send Discord notification
        try:
            user = mongo_db.users.find_one({"_id": record['user_id']})
            level = mongo_db.levels.find_one({"_id": record['level_id']})
            if user and level:
                points_earned = calculate_record_points(record, level)
                notify_record_approved(
                    user['username'], 
                    level['name'], 
                    record['progress'], 
                    points_earned
                )
        except Exception as e:
            print(f"Discord notification error: {e}")
        
        flash('Record approved successfully!', 'success')
    
    return redirect(url_for('admin'))

@app.route('/admin/reject_record/<int:record_id>', methods=['POST'])
def admin_reject_record(record_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get record info before rejecting for Discord notification
    record = mongo_db.records.find_one({"_id": record_id})
    
    mongo_db.records.update_one(
        {"_id": record_id},
        {"$set": {"status": "rejected"}}
    )
    
    # Send Discord notification
    if record:
        try:
            user = mongo_db.users.find_one({"_id": record['user_id']})
            level = mongo_db.levels.find_one({"_id": record['level_id']})
            if user and level:
                notify_record_rejected(
                    user['username'], 
                    level['name'], 
                    record['progress']
                )
        except Exception as e:
            print(f"Discord notification error: {e}")
    
    flash('Record rejected!', 'warning')
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
    
    users = list(mongo_db.users.find().sort("date_joined", -1))
    return render_template('admin/users.html', users=users)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)