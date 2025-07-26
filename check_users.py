from main import app, db, User

with app.app_context():
    users = User.query.all()
    print(f"Total users in database: {len(users)}")
    for user in users:
        print(f"- {user.username} ({user.email}) - Admin: {user.is_admin}")