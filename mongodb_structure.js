// Select the database to use.
use('rtl_database');

// Insert users collection
db.getCollection('users').insertMany([
  {
    '_id': 1,
    'username': 'admin',
    'email': 'admin@example.com',
    'password_hash': '$2b$12$example_hash',
    'is_admin': true,
    'points': 0,
    'date_joined': new Date('2024-01-01T00:00:00Z'),
    'google_id': null
  },
  {
    '_id': 2,
    'username': 'player1',
    'email': 'player1@example.com',
    'password_hash': '$2b$12$example_hash2',
    'is_admin': false,
    'points': 150.5,
    'date_joined': new Date('2024-01-15T10:30:00Z'),
    'google_id': null
  }
]);

// Insert levels collection
db.getCollection('levels').insertMany([
  {
    '_id': 1,
    'name': 'Bloodbath',
    'creator': 'Riot',
    'verifier': 'Riot',
    'level_id': '10565740',
    'video_url': 'https://www.youtube.com/watch?v=example1',
    'thumbnail_url': null,
    'description': 'Extreme demon level',
    'difficulty': 10.0,
    'position': 1,
    'is_legacy': false,
    'date_added': new Date('2024-01-01T00:00:00Z'),
    'points': 10.0,
    'min_percentage': 100
  },
  {
    '_id': 2,
    'name': 'Sonic Wave',
    'creator': 'Cyclic',
    'verifier': 'Sunix',
    'level_id': '26681070',
    'video_url': 'https://www.youtube.com/watch?v=example2',
    'thumbnail_url': null,
    'description': 'Another extreme demon',
    'difficulty': 9.8,
    'position': 2,
    'is_legacy': false,
    'date_added': new Date('2024-01-02T00:00:00Z'),
    'points': 9.9,
    'min_percentage': 100
  }
]);

// Insert records collection
db.getCollection('records').insertMany([
  {
    '_id': 1,
    'user_id': 2,
    'level_id': 1,
    'progress': 100,
    'video_url': 'https://www.youtube.com/watch?v=record1',
    'status': 'approved',
    'date_submitted': new Date('2024-01-20T15:30:00Z')
  },
  {
    '_id': 2,
    'user_id': 2,
    'level_id': 2,
    'progress': 87,
    'video_url': 'https://www.youtube.com/watch?v=record2',
    'status': 'pending',
    'date_submitted': new Date('2024-01-25T12:00:00Z')
  }
]);

// Create indexes
db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "google_id": 1 }, { unique: true, sparse: true });

db.levels.createIndex({ "position": 1 });
db.levels.createIndex({ "is_legacy": 1 });

db.records.createIndex({ "user_id": 1 });
db.records.createIndex({ "level_id": 1 });
db.records.createIndex({ "status": 1 });