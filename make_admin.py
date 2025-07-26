from main import app, db, User

def make_user_admin(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"User '{username}' has been granted admin privileges!")
        else:
            print(f"User '{username}' not found. Please make sure the username exists.")

if __name__ == "__main__":
    make_user_admin("ENGINE")