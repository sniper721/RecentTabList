import os
from pymongo import MongoClient
from dotenv import load_dotenv
import time

def get_mongodb_connection():
    """
    Enhanced MongoDB connection with better error handling and fallback options
    """
    load_dotenv()
    
    mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')
    
    # Enhanced URI with extended timeout options for better reliability
    if 'mongodb.net' in mongodb_uri and '?' not in mongodb_uri:
        mongodb_uri = f"{mongodb_uri}?retryWrites=true&w=majority&connectTimeoutMS=30000&socketTimeoutMS=30000&serverSelectionTimeoutMS=30000&maxIdleTimeMS=60000"
    
    connection_configs = [
        # Config 1: Standard connection with relaxed SSL and extended timeouts
        {
            'name': 'Relaxed SSL Connection',
            'params': {
                'tls': True,
                'tlsAllowInvalidCertificates': True,
                'tlsAllowInvalidHostnames': True,
                'serverSelectionTimeoutMS': 30000,
                'socketTimeoutMS': 30000,
                'connectTimeoutMS': 30000,
                'maxPoolSize': 5,
                'minPoolSize': 1,
                'maxIdleTimeMS': 60000,
                'waitQueueTimeoutMS': 10000,
                'retryWrites': True,
                'retryReads': True,
                'directConnection': False,
                'connect': False
            }
        },
        # Config 2: Direct connection to primary (if known) with extended timeouts
        {
            'name': 'Direct Primary Connection',
            'params': {
                'tls': True,
                'tlsAllowInvalidCertificates': True,
                'serverSelectionTimeoutMS': 15000,
                'socketTimeoutMS': 15000,
                'connectTimeoutMS': 15000,
                'maxPoolSize': 3,
                'directConnection': True,
                'connect': True
            }
        },
        # Config 3: Fallback to localhost
        {
            'name': 'Localhost Fallback',
            'uri': 'mongodb://localhost:27017/',
            'params': {
                'serverSelectionTimeoutMS': 3000,
                'socketTimeoutMS': 3000,
                'connectTimeoutMS': 3000,
                'maxPoolSize': 3
            }
        }
    ]
    
    for i, config in enumerate(connection_configs, 1):
        try:
            print(f"🔄 Attempting MongoDB connection - Config {i}: {config['name']}")
            
            # Use custom URI if provided
            uri_to_use = config.get('uri', mongodb_uri)
            client = MongoClient(uri_to_use, **config['params'])
            
            db = client[mongodb_db]
            
            # Test connection
            client.admin.command('ping', maxTimeMS=5000)
            print(f"✅ MongoDB connected successfully with {config['name']}")
            return client, db
            
        except Exception as e:
            print(f"❌ Config {i} failed: {str(e)[:100]}...")
            if i < len(connection_configs):
                print(f"   Retrying with next configuration...")
                time.sleep(1)
            continue
    
    # If all configs fail, return None for fallback mode
    print("⚠️ All MongoDB connection attempts failed - using fallback mode")
    return None, None

# Example usage:
# mongo_client, mongo_db = get_mongodb_connection()
# if mongo_client is None:
#     # Use fallback data or SQLite
#     pass