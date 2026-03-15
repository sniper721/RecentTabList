from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

# Create minimal app
app = Flask(__name__)
app.secret_key = 'test-key'

# Test MongoDB connection
try:
    print("Testing MongoDB connection...")
    MONGODB_URI = os.environ.get('MONGODB_URI')
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI not set in environment/.env")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    db = client.rtl_database
    # Test a simple query
    test_result = db.users.find_one()
    print("✅ MongoDB connection successful")
    print(f"Test query result: {test_result}")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

@app.route('/')
def index():
    return "<h1>Main App Test</h1><p>MongoDB test completed. Check console for results.</p>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Starting Flask app on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
