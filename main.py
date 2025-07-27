from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime
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
try:
    mongo_client = MongoClient(
        mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        tlsAllowInvalidHostnames=True,
        serverSelectionTimeoutMS=5000
    )
    mongo_db = mongo_client[mongodb_db]
    # Test connection
    mongo_client.admin.command('ping')
    print("✓ MongoDB initialized successfully")
except Exception as e:
    print(f"MongoDB initialization error: {e}")
    print("Falling back to SQLite...")
    # Fall back to SQLite if MongoDB fails
    import subprocess
    subprocess.run(['python', 'main_sqlite_backup.py'])
    exit()
    
oauth = OAuth(app)

# Configure Google OAuth only if credentials are provided
google = None
if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Context processors
@app.context_processor
def utility_processor():
    def get_difficulty_color(difficulty):
        """Convert difficulty value to a color"""
        if difficulty >= 9.5:
            return "#ff0000"  # Extreme
        elif difficulty >= 8.0:
            return "#ff5500"  # Insane
        elif difficulty >= 6.5:
            return "#ffaa00"  # Hard
        elif difficulty >= 5.0:
            return "#ffff00"  # Medium
        else:
            return "#00ff00"  # Easy
    
    def get_top_players(limit=5):
        """Get top players for sidebar"""
        users = list(mongo_db.users.find({"points": {"$gt": 0}}).sort("points", -1).limit(limit))
        return users
    
    return dict(
        get_difficulty_color=get_difficulty_color,
        top_players=get_top_players()
    )

# Helper functions
def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position"""
    if is_legacy:
        return 0
    return (100 - position + 1) / 10

def calculate_record_points(record, level):
    """Calculate points earned from a record"""
    if record['status'] != 'approved' or level['is_legacy']:
        return 0
    
    # Full completion
    if record['progress'] == 100:
        return level['points']
    
    # Partial completion
    if record['progress'] >= level.get('min_percentage', 100):
        percentage_factor = record['progress'] / 100
        return level['points'] * percentage_factor
    
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

# Routes
@app.route('/')
def index():
    main_list = list(mongo_db.levels.find({"is_legacy": False}).sort("position", 1))
    return render_template('index.html', levels=main_list)

@app.route('/legacy')
def legacy():
    legacy_list = list(mongo_db.levels.find({"is_legacy": True}).sort("position", 1))
    return render_template('legacy.html', levels=legacy_list)

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
            "date_joined": datetime.utcnow(),
            "google_id": None
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
                    "date_joined": datetime.utcnow()
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
        level_id = int(request.form.get('level_id'))
        progress = int(request.form.get('progress'))
        video_url = request.form.get('video_url')
        
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
            "date_submitted": datetime.utcnow()
        }
        
        mongo_db.records.insert_one(new_record)
        flash('Record submitted successfully! It will be reviewed by moderators.', 'success')
        return redirect(url_for('profile'))
    
    levels = list(mongo_db.levels.find().sort("position", 1))
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
        
        # Handle file upload
        if 'thumbnail_file' in request.files:
            file = request.files['thumbnail_file']
            if file and file.filename:
                import os
                from werkzeug.utils import secure_filename
                
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                thumbnail_url = f'/static/uploads/{filename}'
        
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
            points = calculate_level_points(position, is_legacy)
        
        new_level = {
            "_id": next_id,
            "name": name,
            "creator": creator,
            "verifier": verifier,
            "level_id": level_id,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "description": description,
            "difficulty": difficulty,
            "position": position,
            "is_legacy": is_legacy,
            "date_added": datetime.utcnow(),
            "points": points,
            "min_percentage": min_percentage
        }
        
        mongo_db.levels.insert_one(new_level)
        flash('Level added successfully!', 'success')
        return redirect(url_for('admin_levels'))
    
    levels = list(mongo_db.levels.find().sort([("is_legacy", 1), ("position", 1)]))
    return render_template('admin/levels.html', levels=levels)

@app.route('/admin/edit_level', methods=['POST'])
def admin_edit_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    thumbnail_url = request.form.get('thumbnail_url')
    
    # Handle file upload
    if 'thumbnail_file' in request.files:
        file = request.files['thumbnail_file']
        if file and file.filename:
            import os
            from werkzeug.utils import secure_filename
            
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            thumbnail_url = f'/static/uploads/{filename}'
    
    points_str = request.form.get('points')
    min_percentage = int(request.form.get('min_percentage', '100'))
    position = int(request.form.get('position'))
    
    # Calculate points
    if points_str and points_str.strip():
        points = float(points_str)
    else:
        is_legacy = 'is_legacy' in request.form
        points = calculate_level_points(position, is_legacy)
    
    update_data = {
        "name": request.form.get('name'),
        "creator": request.form.get('creator'),
        "verifier": request.form.get('verifier'),
        "level_id": request.form.get('level_id'),
        "video_url": request.form.get('video_url'),
        "thumbnail_url": thumbnail_url,
        "description": request.form.get('description'),
        "difficulty": float(request.form.get('difficulty')),
        "position": position,
        "points": points,
        "min_percentage": min_percentage
    }
    
    mongo_db.levels.update_one({"_id": level_id}, {"$set": update_data})
    flash('Level updated successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/delete_level', methods=['POST'])
def admin_delete_level():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    # Delete associated records
    mongo_db.records.delete_many({"level_id": level_id})
    
    # Delete the level
    mongo_db.levels.delete_one({"_id": level_id})
    
    flash('Level deleted successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_legacy', methods=['POST'])
def admin_move_to_legacy():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    
    # Move level to legacy
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": True}}
    )
    
    flash('Level moved to legacy list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_main', methods=['POST'])
def admin_move_to_main():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    level_id = int(request.form.get('level_id'))
    position = int(request.form.get('position'))
    
    # Move level to main list
    mongo_db.levels.update_one(
        {"_id": level_id},
        {"$set": {"is_legacy": False, "position": position}}
    )
    
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
        
        flash('Record approved successfully!', 'success')
    
    return redirect(url_for('admin'))

@app.route('/admin/reject_record/<int:record_id>', methods=['POST'])
def admin_reject_record(record_id):
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    mongo_db.records.update_one(
        {"_id": record_id},
        {"$set": {"status": "rejected"}}
    )
    
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
                "date_joined": datetime.utcnow(),
                "google_id": None
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
        new_admin_status = not user.get('is_admin', False)
        mongo_db.users.update_one(
            {"_id": user_id},
            {"$set": {"is_admin": new_admin_status}}
        )
        
        status = 'granted' if new_admin_status else 'revoked'
        flash(f'Admin privileges {status} for {user["username"]}', 'success')
    
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)