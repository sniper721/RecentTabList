"""
Non-blocking MongoDB Connection Manager
Starts Flask immediately, connects to MongoDB in background
"""
from pymongo import MongoClient
import threading
import time
import os
import json
from datetime import datetime, timezone

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

class NonBlockingMongoDB:
    """MongoDB connection manager with non-blocking initialization"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        self.connection_thread = None
        self.load_from_fallback = True  # Start with fallback mode
        self.cache_file_main = 'cache_main_levels.json'
        self.cache_file_legacy = 'cache_legacy_levels.json'
        
    def connect_async(self):
        """Start MongoDB connection in background thread"""
        print("\n🚀 Starting Flask server IMMEDIATELY (MongoDB connecting in background...)")
        self.connection_thread = threading.Thread(target=self._connect_background, daemon=True)
        self.connection_thread.start()
        
    def _connect_background(self):
        """Background connection with retry logic"""
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                print(f"\n🔧 MongoDB connection attempt {retry_count + 1}/{max_retries}...")
                
                # Use maximum timeouts for reliability
                config = {
                    'tls': True,
                    'tlsAllowInvalidCertificates': True,
                    'tlsAllowInvalidHostnames': True,
                    'serverSelectionTimeoutMS': 60000,
                    'socketTimeoutMS': 120000,
                    'connectTimeoutMS': 60000,
                    'maxPoolSize': 20,
                    'minPoolSize': 5,
                    'maxIdleTimeMS': 60000,
                    'waitQueueTimeoutMS': 30000,
                    'retryWrites': True,
                    'retryReads': True,
                    'directConnection': False,
                    'connect': False
                }
                
                start_time = time.time()
                self.client = MongoClient(mongodb_uri, **config)
                
                # Test connection
                self.client.admin.command('ping', maxTimeMS=60000)
                elapsed = time.time() - start_time
                
                self.db = self.client[mongodb_db]
                self.connected = True
                self.load_from_fallback = False  # Switch to live data
                
                print(f"✅ MongoDB connected successfully in {elapsed:.2f}s")
                print("🌐 Site is now using LIVE database")
                
                # Preload cache in background
                self._preload_cache_async()
                
                return True
                
            except Exception as e:
                retry_count += 1
                print(f"❌ MongoDB connection failed (attempt {retry_count}): {e}")
                
                if retry_count < max_retries:
                    wait_time = min(5 * retry_count, 30)  # Exponential backoff, max 30s
                    print(f"🔄 Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print("⚠️ MongoDB connection failed after all retries")
                    print("📁 Site will continue using cached/fallback data")
                    self.load_from_fallback = True
                    return False
    
    def get_db(self):
        """Get database instance (returns None if not connected yet)"""
        if self.connected and self.db:
            return self.db
        return None
    
    def is_connected(self):
        """Check if MongoDB is connected"""
        return self.connected
    
    def is_ready(self):
        """Check if database is ready for queries"""
        return self.connected and self.db is not None
    
    def _preload_cache_async(self):
        """Preload cache in background"""
        try:
            print("📦 Preloading cache from database...")
            
            if not self.db:
                return
            
            # Load main levels
            main_levels = list(self.db.levels.find(
                {"is_legacy": {"$ne": True}},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1, 
                 "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1, 
                 "image_base64": 1}
            ).sort("position", 1))
            
            # Save to cache
            cache_data = {
                'levels': main_levels,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.cache_file_main, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            print(f"✅ Cached {len(main_levels)} main levels")
            
            # Load legacy levels
            legacy_levels = list(self.db.levels.find(
                {"is_legacy": True},
                {"_id": 1, "name": 1, "creator": 1, "verifier": 1, "position": 1,
                 "points": 1, "level_id": 1, "difficulty": 1, "thumbnail_url": 1,
                 "image_base64": 1}
            ).sort("position", 1))
            
            cache_data = {
                'levels': legacy_levels,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.cache_file_legacy, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
            
            print(f"✅ Cached {len(legacy_levels)} legacy levels")
            print("✨ Cache preloaded successfully!")
            
        except Exception as e:
            print(f"⚠️ Cache preload failed: {e}")
    
    def load_from_cache(self, is_legacy=False):
        """Load levels from cache file (instant, no database needed)"""
        try:
            cache_file = self.cache_file_legacy if is_legacy else self.cache_file_main
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                levels = cache_data.get('levels', [])
                last_updated = cache_data.get('last_updated', 'unknown')
                
                print(f"📁 Loaded {len(levels)} levels from cache ({'legacy' if is_legacy else 'main'})")
                return levels
            else:
                print(f"⚠️ Cache file not found: {cache_file}")
                return []
                
        except Exception as e:
            print(f"❌ Failed to load cache: {e}")
            return []
    
    def query_with_fallback(self, collection, query, sort=None, timeout_ms=30000):
        """Execute query with automatic fallback to cache on timeout"""
        try:
            # If not connected, use cache
            if not self.is_ready():
                print("📁 Using cache (MongoDB not connected yet)")
                return self.load_from_cache()
            
            # Try database query
            cursor = collection.find(query)
            if sort:
                cursor = cursor.sort(sort)
            cursor.max_time_ms(timeout_ms)
            
            result = list(cursor)
            print(f"✅ Database query returned {len(result)} results")
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # On any timeout or error, fallback to cache
            if 'timed out' in error_msg or 'timeout' in error_msg or 'connection' in error_msg:
                print(f"⚠️ Query timeout/error, using cache: {e}")
                return self.load_from_cache()
            else:
                # Re-raise other errors
                raise

# Global instance
mongo_manager = NonBlockingMongoDB()

def get_mongo_manager():
    """Get the global MongoDB manager instance"""
    return mongo_manager

def init_mongodb_async():
    """Initialize MongoDB connection asynchronously (non-blocking)"""
    mongo_manager.connect_async()
    return mongo_manager

if __name__ == "__main__":
    # Test the non-blocking connection
    print("="*80)
    print("Testing Non-Blocking MongoDB Connection")
    print("="*80)
    
    # Start connection
    init_mongodb_async()
    
    # Show status while connecting
    for i in range(10):
        time.sleep(1)
        status = "✅ Connected" if mongo_manager.is_connected() else "⏳ Connecting..."
        print(f"[{i+1}s] Status: {status}")
        
        if mongo_manager.is_connected():
            break
    
    # Wait for connection
    time.sleep(5)
    
    # Final status
    print("\n" + "="*80)
    print(f"Final Status: {'✅ Connected' if mongo_manager.is_connected() else '⏳ Still connecting'}")
    print(f"Cache available: {os.path.exists(mongo_manager.cache_file_main)}")
    print("="*80)
