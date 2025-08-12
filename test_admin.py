#!/usr/bin/env python3
"""
Test script to check admin functionality
"""
import sys
import os
sys.path.append('.')

from main import app, mongo_db
from flask import session

def test_admin_levels():
    """Test the admin levels route"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Mock admin session
            sess['user_id'] = 1
            sess['is_admin'] = True
        
        try:
            response = client.get('/admin/levels')
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.data.decode()[:500]}...")
            return response.status_code == 200
        except Exception as e:
            print(f"Error testing admin levels: {e}")
            return False

def test_database_connection():
    """Test database connection and level retrieval"""
    try:
        # Test basic connection
        mongo_db.levels.find_one()
        print("✓ Database connection successful")
        
        # Test level retrieval
        levels = list(mongo_db.levels.find().limit(5))
        print(f"✓ Found {len(levels)} levels (showing first 5)")
        
        for level in levels:
            print(f"  - {level.get('name', 'Unknown')} (Position: {level.get('position', 'N/A')})")
        
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

if __name__ == '__main__':
    print("Testing admin functionality...")
    print("=" * 50)
    
    print("\n1. Testing database connection...")
    db_ok = test_database_connection()
    
    print("\n2. Testing admin levels route...")
    admin_ok = test_admin_levels()
    
    print("\n" + "=" * 50)
    print(f"Database: {'✓ OK' if db_ok else '✗ FAILED'}")
    print(f"Admin Route: {'✓ OK' if admin_ok else '✗ FAILED'}")