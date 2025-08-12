#!/usr/bin/env python3
"""
Script to import levels from Google Sheets to MongoDB database
"""

import requests
import csv
from io import StringIO
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def get_google_sheets_data(sheet_id):
    """Download CSV data from Google Sheets"""
    # Convert the sharing URL to CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error downloading sheet: {e}")
        return None

def calculate_level_points(position, is_legacy=False):
    """Calculate points based on position using exponential formula"""
    if is_legacy:
        return 0
    # p = 250(0.9475)^(position-1)
    return int(250 * (0.9475 ** (position - 1)))

def parse_csv_data(csv_text):
    """Parse CSV text and return list of level dictionaries"""
    levels = []
    csv_reader = csv.reader(StringIO(csv_text))
    rows = list(csv_reader)
    
    # Skip header row
    for i, row in enumerate(rows[1:], 1):
        # Skip empty rows or rows without enough data
        if len(row) < 5 or not row[1].strip():
            continue
            
        # Extract data from row based on your sheet structure
        position_str = row[0].strip().rstrip('.')  # Remove the dot from "1."
        name = row[1].strip()
        level_id = row[2].strip()
        verifier = row[3].strip()
        rating_str = row[4].strip()  # "10* (Extreme)"
        points_str = row[5].strip() if len(row) > 5 else ""
        
        # Skip if no name
        if not name:
            continue
            
        # Parse position
        try:
            position = int(position_str)
        except (ValueError, TypeError):
            position = i
            
        # Parse difficulty from rating string
        difficulty = 10.0  # Default
        if "Extreme" in rating_str:
            difficulty = 10.0
        elif "Insane" in rating_str:
            difficulty = 9.0
        elif "Hard" in rating_str:
            difficulty = 7.0
        elif "Medium" in rating_str:
            difficulty = 5.0
        elif "Easy" in rating_str:
            difficulty = 3.0
            
        # Parse points
        try:
            points = int(points_str) if points_str else calculate_level_points(position, False)
        except (ValueError, TypeError):
            points = calculate_level_points(position, False)
        
        # Set creator as "Unknown" since it's not in the sheet
        creator = "Unknown"
        
        # Set minimum percentage based on difficulty
        if difficulty >= 9:
            min_percentage = 100  # Extreme/Insane levels require 100%
        else:
            min_percentage = 50   # Others can be 50%
        
        level = {
            'name': name,
            'creator': creator,
            'verifier': verifier,
            'level_id': level_id if level_id else None,
            'video_url': '',  # Not in sheet
            'thumbnail_url': '',  # Not in sheet
            'description': f'Rating: {rating_str}',
            'difficulty': difficulty,
            'position': position,
            'is_legacy': False,  # All current levels
            'level_type': 'Level',
            'date_added': datetime.utcnow(),
            'points': points,
            'min_percentage': min_percentage
        }
        
        levels.append(level)
        print(f"Parsed level: {name} by {verifier} (Position: {position}, Points: {points})")
    
    return levels

def import_to_mongodb(levels):
    """Import levels to MongoDB database"""
    try:
        # Connect to MongoDB
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=5000
        )
        db = client[mongodb_db]
        
        # Test connection
        client.admin.command('ping')
        print("✓ Connected to MongoDB")
        
        # Get the next available ID
        last_level = db.levels.find_one(sort=[("_id", -1)])
        next_id = (last_level['_id'] + 1) if last_level else 1
        
        # Add IDs to levels
        for i, level in enumerate(levels):
            level['_id'] = next_id + i
            
        # Clear existing levels (optional - comment out if you want to keep existing)
        # db.levels.delete_many({})
        # print("Cleared existing levels")
        
        # Insert levels
        if levels:
            result = db.levels.insert_many(levels)
            print(f"✓ Imported {len(result.inserted_ids)} levels successfully")
            
            # Create indexes
            db.levels.create_index([("is_legacy", 1), ("position", 1)])
            print("✓ Created database indexes")
        else:
            print("No levels to import")
            
    except Exception as e:
        print(f"Error importing to MongoDB: {e}")
        return False
        
    finally:
        if 'client' in locals():
            client.close()
            
    return True

def main():
    """Main import function"""
    # Extract sheet ID from the URL
    sheet_url = "https://docs.google.com/spreadsheets/d/1zuLQsMNaSz78le7Jdu5_rF6tw3pYmHapoCYM5T0JMUU/edit?usp=drivesdk"
    sheet_id = "1zuLQsMNaSz78le7Jdu5_rF6tw3pYmHapoCYM5T0JMUU"
    
    print("Starting level import process...")
    print(f"Sheet ID: {sheet_id}")
    
    # Download CSV data
    print("Downloading data from Google Sheets...")
    csv_data = get_google_sheets_data(sheet_id)
    
    if not csv_data:
        print("Failed to download sheet data")
        return
        
    print("✓ Downloaded sheet data")
    
    # Parse CSV data
    print("Parsing level data...")
    levels = parse_csv_data(csv_data)
    
    if not levels:
        print("No levels found in sheet")
        return
        
    print(f"✓ Parsed {len(levels)} levels")
    
    # Show preview of first few levels
    print("\nPreview of levels to import:")
    for i, level in enumerate(levels[:5]):
        print(f"{i+1}. {level['name']} by {level['creator']} (Position: {level['position']})")
    
    if len(levels) > 5:
        print(f"... and {len(levels) - 5} more levels")
    
    # Auto-confirm import
    print(f"\nProceeding to import {len(levels)} levels to database...")
        
    # Import to database
    print("Importing to MongoDB...")
    success = import_to_mongodb(levels)
    
    if success:
        print("✓ Import completed successfully!")
    else:
        print("✗ Import failed")

if __name__ == "__main__":
    main()