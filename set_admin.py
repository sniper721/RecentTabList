from main import app, db, User

def set_admin(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"✓ {username} is now an admin")
        else:
            print(f"✗ User {username} not found")

if __name__ == "__main__":
    username = input("Enter username to make admin: ")
    set_admin(username)