#!/usr/bin/env python3
"""
Debug script to check Google Sheets data format
"""

import requests
import csv
from io import StringIO

def get_google_sheets_data(sheet_id):
    """Download CSV data from Google Sheets"""
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        response = requests.get(csv_url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error downloading sheet: {e}")
        return None

def debug_csv_data(csv_text):
    """Debug CSV data to see the structure"""
    print("Raw CSV data (first 1000 chars):")
    print(csv_text[:1000])
    print("\n" + "="*50 + "\n")
    
    # Try to parse as CSV
    try:
        csv_reader = csv.reader(StringIO(csv_text))
        rows = list(csv_reader)
        
        print(f"Total rows: {len(rows)}")
        
        if rows:
            print(f"Headers (first row): {rows[0]}")
            print(f"Number of columns: {len(rows[0])}")
            
            if len(rows) > 1:
                print(f"First data row: {rows[1]}")
                
            if len(rows) > 2:
                print(f"Second data row: {rows[2]}")
                
    except Exception as e:
        print(f"Error parsing CSV: {e}")

def main():
    sheet_id = "1zuLQsMNaSz78le7Jdu5_rF6tw3pYmHapoCYM5T0JMUU"
    
    print("Downloading and debugging Google Sheets data...")
    csv_data = get_google_sheets_data(sheet_id)
    
    if csv_data:
        debug_csv_data(csv_data)
    else:
        print("Failed to download data")

if __name__ == "__main__":
    main()