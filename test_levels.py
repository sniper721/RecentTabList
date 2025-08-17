from main import app, mongo_db

with app.app_context():
    # Test the index route
    with app.test_client() as client:
        print("Testing index route...")
        response = client.get('/')
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            level_cards = content.count('level-card')
            print(f"Found {level_cards} level cards in HTML")
            
            # Check if we have the expected number of levels
            main_levels = mongo_db.levels.count_documents({"is_legacy": False})
            print(f"Expected {main_levels} main levels from database")
            
            if level_cards == 0:
                print("❌ No level cards found in HTML - there might be a template issue")
                # Check if levels are being passed to template
                if 'levels' in content:
                    print("✅ 'levels' found in HTML content")
                else:
                    print("❌ 'levels' not found in HTML content")
            else:
                print(f"✅ Found {level_cards} level cards")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.get_data(as_text=True)[:500])

        # Test legacy route
        print("\nTesting legacy route...")
        response = client.get('/legacy')
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            level_rows = content.count('level-row')
            print(f"Found {level_rows} level rows in legacy HTML")
            
            legacy_levels = mongo_db.levels.count_documents({"is_legacy": True})
            print(f"Expected {legacy_levels} legacy levels from database")
        else:
            print(f"❌ Legacy error: {response.status_code}")