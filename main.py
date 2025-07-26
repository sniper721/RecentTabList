from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///demonlist.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Google OAuth configuration
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Initialize database and OAuth
db = SQLAlchemy(app)
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Function to check if a column exists in a table
def column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
            return True
    except Exception:
        return False

# Function to add missing columns
def add_missing_columns():
    """Add missing columns to the database"""
    try:
        with db.engine.connect() as conn:
            # Check and add points column to level table
            if not column_exists('level', 'points'):
                conn.execute("ALTER TABLE level ADD COLUMN points FLOAT DEFAULT 0.0")
                conn.execute("UPDATE level SET points = (100 - position + 1) / 10.0 WHERE is_legacy = 0")
            
            # Check and add min_percentage column to level table
            if not column_exists('level', 'min_percentage'):
                conn.execute("ALTER TABLE level ADD COLUMN min_percentage INTEGER DEFAULT 100")
            
            # Check and add points column to user table
            if not column_exists('user', 'points'):
                conn.execute("ALTER TABLE user ADD COLUMN points FLOAT DEFAULT 0.0")
            
            # Check and add points column to record table
            if not column_exists('record', 'points'):
                conn.execute("ALTER TABLE record ADD COLUMN points FLOAT DEFAULT 0.0")
            
            # Commit the changes
            conn.commit()
            print("Database schema updated successfully!")
            return True
    except Exception as e:
        print(f"Error updating database schema: {e}")
        return False

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
        from list import get_top_players as get_players
        return get_players(limit)
    
    return dict(
        get_difficulty_color=get_difficulty_color,
        top_players=get_top_players()
    )

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Float, default=0.0, nullable=True)  # Total points earned from records
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def calculate_points(self):
        """Calculate total points from approved records"""
        total_points = 0
        for record in self.records:
            if record.status == 'approved':
                total_points += record.points
        self.points = total_points
        return total_points

class Level(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    creator = db.Column(db.String(80), nullable=False)
    verifier = db.Column(db.String(80), nullable=False)
    level_id = db.Column(db.String(20))
    video_url = db.Column(db.String(200))
    description = db.Column(db.Text)
    difficulty = db.Column(db.Float, nullable=False)  # For precise ranking
    position = db.Column(db.Integer, nullable=False)  # Current position in the list
    is_legacy = db.Column(db.Boolean, default=False)  # Whether it's in the legacy list
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Float, default=0.0, nullable=True)  # Points awarded for completing the level
    min_percentage = db.Column(db.Integer, default=100, nullable=True)  # Minimum percentage required for points
    
    def calculate_points(self):
        """Calculate points based on position if not manually set"""
        if self.is_legacy:
            return 0  # Legacy levels don't award points by default
        return (100 - self.position + 1) / 10

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    level_id = db.Column(db.Integer, db.ForeignKey('level.id'), nullable=False)
    progress = db.Column(db.Integer, nullable=False)  # Percentage completed
    video_url = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    points = db.Column(db.Float, default=0.0, nullable=True)  # Points earned from this record
    
    user = db.relationship('User', backref=db.backref('records', lazy=True))
    level = db.relationship('Level', backref=db.backref('records', lazy=True))
    
    def calculate_points(self):
        """Calculate points earned from this record based on level and progress"""
        if self.status != 'approved':
            return 0
            
        level = self.level
        if level.is_legacy:
            return 0
            
        # Full completion
        if self.progress == 100:
            return level.points
            
        # Partial completion (if progress meets minimum percentage)
        if self.progress >= level.min_percentage:
            # Calculate partial points based on progress
            percentage_factor = self.progress / 100
            return level.points * percentage_factor
            
        return 0

# Routes
@app.route('/')
def index():
    try:
        # Try to run fix_db.py first
        import fix_db
        fix_db.fix_database()
        
        # Then try to load the levels
        main_list = Level.query.filter_by(is_legacy=False).order_by(Level.position).all()
        return render_template('index.html', levels=main_list)
    except Exception as e:
        # If there's an error, try a simpler query that doesn't use the new columns
        print(f"Error loading index page: {e}")
        try:
            # Use raw SQL to get only the columns that definitely exist
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT id, name, creator, verifier, level_id, video_url, description,
                       difficulty, position, is_legacy, date_added
                FROM level
                WHERE is_legacy = 0
                ORDER BY position
            """))
            
            # Convert the result to a list of dictionaries
            main_list = []
            for row in result:
                level = {
                    'id': row[0],
                    'name': row[1],
                    'creator': row[2],
                    'verifier': row[3],
                    'level_id': row[4],
                    'video_url': row[5],
                    'description': row[6],
                    'difficulty': row[7],
                    'position': row[8],
                    'is_legacy': row[9],
                    'date_added': row[10],
                    'points': (100 - row[8] + 1) / 10,  # Calculate points based on position
                    'min_percentage': 100  # Default value
                }
                main_list.append(level)
            
            return render_template('index.html', levels=main_list)
        except Exception as e2:
            # If still failing, return an error page
            print(f"Error loading index page with simplified query: {e2}")
            return render_template('error.html', error=str(e2))

@app.route('/legacy')
def legacy():
    try:
        legacy_list = Level.query.filter_by(is_legacy=True).order_by(Level.position).all()
        return render_template('legacy.html', levels=legacy_list)
    except Exception as e:
        # If there's an error, try a simpler query that doesn't use the new columns
        print(f"Error loading legacy page: {e}")
        try:
            # Use raw SQL to get only the columns that definitely exist
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT id, name, creator, verifier, level_id, video_url, description,
                       difficulty, position, is_legacy, date_added
                FROM level
                WHERE is_legacy = 1
                ORDER BY position
            """))
            
            # Convert the result to a list of dictionaries
            legacy_list = []
            for row in result:
                level = {
                    'id': row[0],
                    'name': row[1],
                    'creator': row[2],
                    'verifier': row[3],
                    'level_id': row[4],
                    'video_url': row[5],
                    'description': row[6],
                    'difficulty': row[7],
                    'position': row[8],
                    'is_legacy': row[9],
                    'date_added': row[10],
                    'points': 0,  # Legacy levels don't award points
                    'min_percentage': 100  # Default value
                }
                legacy_list.append(level)
            
            return render_template('legacy.html', levels=legacy_list)
        except Exception as e2:
            # If still failing, return an error page
            print(f"Error loading legacy page with simplified query: {e2}")
            return render_template('error.html', error=str(e2))

@app.route('/level/<int:level_id>')
def level_detail(level_id):
    try:
        level = Level.query.get_or_404(level_id)
        records = Record.query.filter_by(level_id=level_id, status='approved').all()
        return render_template('level_detail.html', level=level, records=records)
    except Exception as e:
        # If there's an error, try a simpler query that doesn't use the new columns
        print(f"Error loading level detail page: {e}")
        try:
            # Use raw SQL to get only the columns that definitely exist
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT id, name, creator, verifier, level_id, video_url, description,
                       difficulty, position, is_legacy, date_added
                FROM level
                WHERE id = :level_id
            """), {'level_id': level_id})
            
            # Convert the result to a dictionary
            level_data = None
            for row in result:
                level_data = {
                    'id': row[0],
                    'name': row[1],
                    'creator': row[2],
                    'verifier': row[3],
                    'level_id': row[4],
                    'video_url': row[5],
                    'description': row[6],
                    'difficulty': row[7],
                    'position': row[8],
                    'is_legacy': row[9],
                    'date_added': row[10],
                    'points': (100 - row[8] + 1) / 10,  # Calculate points based on position
                    'min_percentage': 100  # Default value
                }
                break
            
            if not level_data:
                return render_template('error.html', error="Level not found")
            
            # Get records
            record_result = db.session.execute(text("""
                SELECT r.id, r.user_id, r.level_id, r.progress, r.video_url, r.status, r.date_submitted,
                       u.username
                FROM record r
                JOIN user u ON r.user_id = u.id
                WHERE r.level_id = :level_id AND r.status = 'approved'
            """), {'level_id': level_id})
            
            # Convert the result to a list of dictionaries
            records = []
            for row in record_result:
                record = {
                    'id': row[0],
                    'user_id': row[1],
                    'level_id': row[2],
                    'progress': row[3],
                    'video_url': row[4],
                    'status': row[5],
                    'date_submitted': row[6],
                    'user': {'username': row[7]},
                    'points': 0  # Default value
                }
                records.append(record)
            
            # Create a class-like object for level to mimic the SQLAlchemy model
            class LevelObj:
                pass
            
            level = LevelObj()
            for key, value in level_data.items():
                setattr(level, key, value)
            
            return render_template('level_detail.html', level=level, records=records)
        except Exception as e2:
            # If still failing, return an error page
            print(f"Error loading level detail page with simplified query: {e2}")
            return render_template('error.html', error=str(e2))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
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
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
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
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if user_info:
        google_id = user_info['sub']
        email = user_info['email']
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists with this Google ID
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            # Check if user exists with this email
            user = User.query.filter_by(email=email).first()
            if user:
                # Link Google account to existing user
                user.google_id = google_id
            else:
                # Create new user
                username = name
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{name}{counter}"
                    counter += 1
                
                user = User(
                    username=username,
                    email=email,
                    google_id=google_id
                )
                db.session.add(user)
        
        db.session.commit()
        
        # Log in the user
        session['user_id'] = user.id
        session['is_admin'] = user.is_admin
        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('index'))
    
    flash('Google login failed', 'danger')
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    user_records = Record.query.filter_by(user_id=user.id).all()
    
    return render_template('profile.html', user=user, records=user_records)

@app.route('/submit_record', methods=['GET', 'POST'])
def submit_record():
    if 'user_id' not in session:
        flash('Please log in to submit a record', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        level_id = request.form.get('level_id')
        progress = request.form.get('progress')
        video_url = request.form.get('video_url')
        
        new_record = Record(
            user_id=session['user_id'],
            level_id=level_id,
            progress=progress,
            video_url=video_url
        )
        
        db.session.add(new_record)
        db.session.commit()
        
        flash('Record submitted successfully! It will be reviewed by moderators.', 'success')
        return redirect(url_for('profile'))
    
    levels = Level.query.all()
    return render_template('submit_record.html', levels=levels)

# Admin routes
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow any logged-in user to access the admin panel
    pending_records = Record.query.filter_by(status='pending').all()
    return render_template('admin/index.html', pending_records=pending_records)

@app.route('/admin/levels', methods=['GET', 'POST'])
def admin_levels():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    # Allow any logged-in user to access the admin levels page
    
    if request.method == 'POST':
        name = request.form.get('name')
        creator = request.form.get('creator')
        verifier = request.form.get('verifier')
        level_id = request.form.get('level_id')
        video_url = request.form.get('video_url')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        position = request.form.get('position')
        is_legacy = 'is_legacy' in request.form
        
        # Get points and min_percentage from form
        points_str = request.form.get('points')
        min_percentage = request.form.get('min_percentage', '100')
        
        # Create new level
        new_level = Level(
            name=name,
            creator=creator,
            verifier=verifier,
            level_id=level_id,
            video_url=video_url,
            description=description,
            difficulty=float(difficulty),
            position=int(position),
            is_legacy=is_legacy,
            min_percentage=int(min_percentage)
        )
        
        # Set points if provided, otherwise calculate based on position
        if points_str and points_str.strip():
            new_level.points = float(points_str)
        else:
            new_level.points = new_level.calculate_points()
        
        db.session.add(new_level)
        db.session.commit()
        
        flash('Level added successfully!', 'success')
        return redirect(url_for('admin_levels'))
    
    levels = Level.query.order_by(Level.is_legacy, Level.position).all()
    return render_template('admin/levels.html', levels=levels)

@app.route('/admin/edit_level', methods=['POST'])
def admin_edit_level():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    level_id = request.form.get('level_id')
    level = Level.query.get_or_404(level_id)
    
    level.name = request.form.get('name')
    level.creator = request.form.get('creator')
    level.verifier = request.form.get('verifier')
    level.level_id = request.form.get('level_id')
    level.video_url = request.form.get('video_url')
    level.description = request.form.get('description')
    level.difficulty = float(request.form.get('difficulty'))
    
    # Update points and min_percentage
    points_str = request.form.get('points')
    min_percentage = request.form.get('min_percentage', '100')
    
    level.min_percentage = int(min_percentage)
    
    # Set points if provided, otherwise calculate based on position
    if points_str and points_str.strip():
        level.points = float(points_str)
    else:
        level.points = level.calculate_points()
    
    # Handle position change
    new_position = int(request.form.get('position'))
    if new_position != level.position:
        from list import move_level_position
        move_level_position(level_id, new_position)
    
    db.session.commit()
    flash('Level updated successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/delete_level', methods=['POST'])
def admin_delete_level():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    level_id = request.form.get('level_id')
    
    try:
        # Use raw SQL to avoid SQLAlchemy session issues
        from sqlalchemy import text
        
        # Get level info before deletion
        level_result = db.session.execute(text("""
            SELECT position, is_legacy FROM level WHERE id = :level_id
        """), {'level_id': level_id}).fetchone()
        
        if not level_result:
            flash('Level not found', 'danger')
            return redirect(url_for('admin_levels'))
            
        position, is_legacy = level_result
        
        # Get records associated with this level
        records = db.session.execute(text("""
            SELECT id, user_id, points, status FROM record WHERE level_id = :level_id
        """), {'level_id': level_id}).fetchall()
        
        # Update user points for each deleted record
        for record in records:
            record_id, user_id, points, status = record
            
            if status == 'approved' and points and points > 0:
                # Subtract points from user
                db.session.execute(text("""
                    UPDATE user SET points = GREATEST(points - :points, 0)
                    WHERE id = :user_id
                """), {'points': points, 'user_id': user_id})
            
            # Delete the record
            db.session.execute(text("""
                DELETE FROM record WHERE id = :record_id
            """), {'record_id': record_id})
        
        # Delete the level
        db.session.execute(text("""
            DELETE FROM level WHERE id = :level_id
        """), {'level_id': level_id})
        
        # Shift positions of other levels
        db.session.execute(text("""
            UPDATE level SET position = position - 1
            WHERE position > :position AND is_legacy = :is_legacy
        """), {'position': position, 'is_legacy': is_legacy})
        
        db.session.commit()
        flash('Level deleted successfully!', 'success')
        
    except Exception as e:
        print(f"Error deleting level: {e}")
        try:
            db.session.rollback()
        except:
            pass
        flash('Failed to delete level', 'danger')
    
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_legacy', methods=['POST'])
def admin_move_to_legacy():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    level_id = request.form.get('level_id')
    from list import move_to_legacy
    
    if move_to_legacy(level_id):
        flash('Level moved to legacy list successfully!', 'success')
    else:
        flash('Failed to move level to legacy list', 'danger')
    
    return redirect(url_for('admin_levels'))

@app.route('/admin/move_to_main', methods=['POST'])
def admin_move_to_main():
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    level_id = request.form.get('level_id')
    position = int(request.form.get('position'))
    
    level = Level.query.get_or_404(level_id)
    
    # Shift positions of other levels
    levels_to_shift = Level.query.filter(
        Level.position >= position,
        Level.is_legacy == False
    ).all()
    
    for lvl in levels_to_shift:
        lvl.position += 1
    
    # Update the level
    level.is_legacy = False
    level.position = position
    
    db.session.commit()
    flash('Level moved to main list successfully!', 'success')
    return redirect(url_for('admin_levels'))

@app.route('/admin/approve_record/<int:record_id>', methods=['POST'])
def admin_approve_record(record_id):
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    record = Record.query.get_or_404(record_id)
    record.status = 'approved'
    
    # Calculate points for this record
    record.points = record.calculate_points()
    
    # Update user's total points
    user = record.user
    user.calculate_points()
    
    db.session.commit()
    
    flash('Record approved successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/reject_record/<int:record_id>', methods=['POST'])
def admin_reject_record(record_id):
    if 'user_id' not in session:
        flash('Please log in to access admin panel', 'warning')
        return redirect(url_for('login'))
    
    record = Record.query.get_or_404(record_id)
    record.status = 'rejected'
    db.session.commit()
    
    flash('Record rejected!', 'warning')
    return redirect(url_for('admin'))

# Initialize database
with app.app_context():
    db.create_all()
    add_missing_columns()

if __name__ == '__main__':
    app.run(debug=True)