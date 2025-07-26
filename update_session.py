from main import app, db, User
import os
import json

def update_session_file():
    # Path to the Flask session directory
    session_dir = os.path.join(os.getcwd(), 'flask_session')
    
    # If using filesystem sessions, update the session file
    if os.path.exists(session_dir):
        for filename in os.listdir(session_dir):
            if filename.startswith('session:'):
                session_path = os.path.join(session_dir, filename)
                try:
                    with open(session_path, 'r') as f:
                        session_data = json.load(f)
                    
                    if 'user_id' in session_data:
                        user_id = session_data['user_id']
                        with app.app_context():
                            user = User.query.get(user_id)
                            if user and user.is_admin:
                                session_data['is_admin'] = True
                                with open(session_path, 'w') as f:
                                    json.dump(session_data, f)
                                print(f"Updated session for user {user.username}")
                except Exception as e:
                    print(f"Error updating session: {e}")
    else:
        print("Session directory not found. Flask might be using a different session type.")
        print("Please log out and log back in to update your session.")

if __name__ == "__main__":
    print("Attempting to update session...")
    update_session_file()
    print("Done. If this doesn't work, please log out and log back in.")