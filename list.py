from sqlalchemy import desc

# Import db at the function level to avoid circular imports
def get_db():
    from main import db
    return db

# Import models at the function level to avoid circular imports
def get_models():
    from main import Level, Record, User
    return Level, Record, User

def get_main_list():
    """Get the main demon list sorted by position"""
    db = get_db()
    Level, _, _ = get_models()
    return Level.query.filter_by(is_legacy=False).order_by(Level.position).all()

def get_legacy_list():
    """Get the legacy demon list sorted by position"""
    db = get_db()
    Level, _, _ = get_models()
    return Level.query.filter_by(is_legacy=True).order_by(Level.position).all()

def get_level_by_id(level_id):
    """Get a level by its ID"""
    Level, _, _ = get_models()
    return Level.query.get(level_id)

def get_level_by_position(position, is_legacy=False):
    """Get a level by its position in the list"""
    Level, _, _ = get_models()
    return Level.query.filter_by(position=position, is_legacy=is_legacy).first()

def add_level(name, creator, verifier, level_id, video_url, description, difficulty, position, is_legacy=False):
    """Add a new level to the list"""
    db = get_db()
    Level, _, _ = get_models()
    
    # Shift positions of other levels if needed
    if position > 0:
        levels_to_shift = Level.query.filter(
            Level.position >= position,
            Level.is_legacy == is_legacy
        ).all()
        
        for level in levels_to_shift:
            level.position += 1
    
    # Create new level
    new_level = Level(
        name=name,
        creator=creator,
        verifier=verifier,
        level_id=level_id,
        video_url=video_url,
        description=description,
        difficulty=difficulty,
        position=position,
        is_legacy=is_legacy
    )
    
    db.session.add(new_level)
    db.session.commit()
    return new_level

def update_level(level_id, **kwargs):
    """Update a level's information"""
    Level, _, _ = get_models()
    db = get_db()
    level = Level.query.get(level_id)
    if not level:
        return None
    
    # Handle position change separately if it exists
    new_position = kwargs.pop('position', None)
    if new_position is not None and new_position != level.position:
        move_level_position(level_id, new_position)
    
    # Update other attributes
    for key, value in kwargs.items():
        if hasattr(level, key):
            setattr(level, key, value)
    
    db.session.commit()
    return level

def delete_level(level_id):
    """Delete a level from the list"""
    try:
        # Import inside function to avoid circular imports
        from main import db, Level, Record, User
        
        # Use raw SQL to avoid SQLAlchemy session issues
        from sqlalchemy import text
        
        # Get level info before deletion
        level_result = db.session.execute(text("""
            SELECT position, is_legacy FROM level WHERE id = :level_id
        """), {'level_id': level_id}).fetchone()
        
        if not level_result:
            return False
            
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
        return True
        
    except Exception as e:
        print(f"Error deleting level: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return False

def move_level_position(level_id, new_position):
    """Move a level to a new position in the list"""
    try:
        # Import inside function to avoid circular imports
        from main import db
        
        # Use raw SQL to avoid SQLAlchemy session issues
        from sqlalchemy import text
        
        # Get level info before moving
        level_result = db.session.execute(text("""
            SELECT position, is_legacy FROM level WHERE id = :level_id
        """), {'level_id': level_id}).fetchone()
        
        if not level_result:
            return False
            
        old_position = level_result[0]
        is_legacy = level_result[1]
        
        # No change needed if position is the same
        if old_position == new_position:
            return True
        
        # Shift positions of other levels
        if old_position < new_position:
            # Moving down in the list
            db.session.execute(text("""
                UPDATE level SET position = position - 1
                WHERE position > :old_position AND position <= :new_position AND is_legacy = :is_legacy
            """), {'old_position': old_position, 'new_position': new_position, 'is_legacy': is_legacy})
        else:
            # Moving up in the list
            db.session.execute(text("""
                UPDATE level SET position = position + 1
                WHERE position < :old_position AND position >= :new_position AND is_legacy = :is_legacy
            """), {'old_position': old_position, 'new_position': new_position, 'is_legacy': is_legacy})
        
        # Update the level's position
        db.session.execute(text("""
            UPDATE level SET position = :new_position
            WHERE id = :level_id
        """), {'new_position': new_position, 'level_id': level_id})
        
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error moving level position: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return False

def move_to_legacy(level_id):
    """Move a level from the main list to the legacy list"""
    try:
        # Import inside function to avoid circular imports
        from main import db
        
        # Use raw SQL to avoid SQLAlchemy session issues
        from sqlalchemy import text
        
        # Get level info before moving
        level_result = db.session.execute(text("""
            SELECT position, is_legacy FROM level WHERE id = :level_id
        """), {'level_id': level_id}).fetchone()
        
        if not level_result:
            return False
            
        old_position, is_legacy = level_result
        
        # If already legacy, nothing to do
        if is_legacy:
            return False
        
        # Find the highest position in the legacy list
        highest_legacy = db.session.execute(text("""
            SELECT MAX(position) FROM level WHERE is_legacy = 1
        """)).scalar()
        
        new_position = 1 if highest_legacy is None else highest_legacy + 1
        
        # Update the level
        db.session.execute(text("""
            UPDATE level SET is_legacy = 1, position = :new_position
            WHERE id = :level_id
        """), {'new_position': new_position, 'level_id': level_id})
        
        # Shift positions in the main list
        db.session.execute(text("""
            UPDATE level SET position = position - 1
            WHERE position > :old_position AND is_legacy = 0
        """), {'old_position': old_position})
        
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error moving level to legacy: {e}")
        try:
            db.session.rollback()
        except:
            pass
        return False

def get_top_players(limit=100):
    """Get the top players based on points"""
    from sqlalchemy import func
    db = get_db()
    _, Record, User = get_models()
    
    try:
        # Get players sorted by points
        top_players = User.query\
            .filter(User.points > 0)\
            .order_by(desc(User.points))\
            .limit(limit)\
            .all()
        
        # Format the result to include username, points, and record count
        result = []
        for player in top_players:
            # Count approved records
            record_count = db.session.query(func.count(Record.id))\
                .filter(Record.user_id == player.id, Record.status == 'approved')\
                .scalar()
            
            result.append({
                'id': player.id,
                'username': player.username,
                'points': player.points,
                'record_count': record_count
            })
        
        return result
    except Exception as e:
        # If there's an error, return an empty list
        print(f"Error in get_top_players: {e}")
        return []

def search_levels(query):
    """Search for levels by name, creator, or verifier"""
    search = f"%{query}%"
    Level, _, _ = get_models()
    return Level.query.filter(
        (Level.name.ilike(search)) |
        (Level.creator.ilike(search)) |
        (Level.verifier.ilike(search))
    ).all()