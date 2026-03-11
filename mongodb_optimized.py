"""
MongoDB Performance Optimization Helper
Provides optimized database connection settings and query helpers
"""
from pymongo import MongoClient
import os
import time
from functools import wraps

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

# Optimized MongoDB configuration for production
OPTIMIZED_CONFIG = {
    'tls': True,
    'tlsAllowInvalidCertificates': True,
    'tlsAllowInvalidHostnames': True,
    'serverSelectionTimeoutMS': 60000,      # 60 seconds - maximum for slow connections
    'socketTimeoutMS': 120000,               # 120 seconds - maximum for long queries
    'connectTimeoutMS': 60000,               # 60 seconds - maximum for initial connection
    'maxPoolSize': 20,                       # Maximum pool size for high concurrency
    'minPoolSize': 5,                        # Keep minimum connections alive
    'maxIdleTimeMS': 60000,                  # 60 seconds idle time
    'waitQueueTimeoutMS': 30000,             # 30 seconds wait in queue
    'retryWrites': True,
    'retryReads': True,
    'directConnection': False,               # Use replica set discovery
    'connect': False                         # Don't connect immediately
}

def get_optimized_client():
    """Create a MongoDB client with optimized settings"""
    try:
        print("🔧 Creating optimized MongoDB client...")
        client = MongoClient(mongodb_uri, **OPTIMIZED_CONFIG)
        
        # Test connection
        start_time = time.time()
        client.admin.command('ping', maxTimeMS=60000)
        elapsed = time.time() - start_time
        
        print(f"✅ MongoDB connected successfully in {elapsed:.2f}s")
        return client
        
    except Exception as e:
        print(f"❌ Failed to create optimized MongoDB client: {e}")
        raise

def retry_on_timeout(max_retries=3, delay=2):
    """Decorator to retry database operations on timeout"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    
                    # Only retry on timeout errors
                    if 'timed out' in error_msg or 'timeout' in error_msg:
                        last_exception = e
                        print(f"⚠️ Timeout on attempt {attempt}/{max_retries}: {e}")
                        
                        if attempt < max_retries:
                            print(f"🔄 Retrying in {delay} seconds...")
                            time.sleep(delay)
                        continue
                    else:
                        # Re-raise non-timeout errors immediately
                        raise
            
            # All retries failed
            print(f"❌ All {max_retries} retry attempts failed")
            raise last_exception
            
        return wrapper
    return decorator

def optimize_query_performance(collection, query, max_time_ms=120000, limit=None):
    """Execute a query with optimized performance settings"""
    try:
        cursor = collection.find(query, max_time_ms=max_time_ms)
        
        if limit:
            cursor = cursor.limit(limit)
        
        return list(cursor)
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        raise

def safe_update(collection, filter_query, update_query, upsert=False):
    """Safely execute an update operation with error handling"""
    try:
        result = collection.update_one(filter_query, update_query, upsert=upsert)
        return result.modified_count
        
    except Exception as e:
        print(f"❌ Update failed: {e}")
        raise

def safe_find_one(collection, query, sort=None, max_time_ms=60000):
    """Safely find one document with timeout protection"""
    try:
        if sort:
            return collection.find_one(query, sort=sort, max_time_ms=max_time_ms)
        else:
            return collection.find_one(query, max_time_ms=max_time_ms)
            
    except Exception as e:
        print(f"❌ Find operation failed: {e}")
        raise

def test_connection_quality(client):
    """Test MongoDB connection quality and provide recommendations"""
    print("\n" + "="*70)
    print("MongoDB Connection Quality Test")
    print("="*70)
    
    metrics = {
        'ping_time': None,
        'connection_stable': False,
        'recommendations': []
    }
    
    try:
        # Test ping multiple times
        ping_times = []
        for i in range(3):
            start = time.time()
            client.admin.command('ping', maxTimeMS=60000)
            ping_time = (time.time() - start) * 1000  # Convert to ms
            ping_times.append(ping_time)
            print(f"✓ Ping {i+1}: {ping_time:.0f}ms")
        
        avg_ping = sum(ping_times) / len(ping_times)
        metrics['ping_time'] = avg_ping
        
        # Rate connection quality
        if avg_ping < 100:
            print(f"\n⭐⭐⭐⭐⭐ Excellent connection ({avg_ping:.0f}ms)")
            metrics['connection_stable'] = True
        elif avg_ping < 500:
            print(f"\n⭐⭐⭐⭐ Good connection ({avg_ping:.0f}ms)")
            metrics['connection_stable'] = True
        elif avg_ping < 2000:
            print(f"\n⭐⭐⭐ Acceptable connection ({avg_ping:.0f}ms)")
            metrics['connection_stable'] = True
            metrics['recommendations'].append("Consider using a closer MongoDB region")
        elif avg_ping < 5000:
            print(f"\n⭐⭐ Fair connection ({avg_ping:.0f}ms) - approaching timeout risk")
            metrics['connection_stable'] = False
            metrics['recommendations'].append("High latency detected - consider upgrading MongoDB tier")
            metrics['recommendations'].append("Enable connection pooling")
        else:
            print(f"\n⭐ Poor connection ({avg_ping:.0f}ms) - HIGH TIMEOUT RISK")
            metrics['connection_stable'] = False
            metrics['recommendations'].append("CRITICAL: Connection is unstable")
            metrics['recommendations'].append("Upgrade MongoDB Atlas tier immediately")
            metrics['recommendations'].append("Check network/firewall settings")
        
        # Print recommendations
        if metrics['recommendations']:
            print("\n💡 Recommendations:")
            for rec in metrics['recommendations']:
                print(f"   • {rec}")
        
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        metrics['connection_stable'] = False
    
    print("="*70 + "\n")
    
    return metrics

if __name__ == "__main__":
    # Test the optimized connection
    print("Testing MongoDB connection with optimized settings...\n")
    
    try:
        client = get_optimized_client()
        db = client[mongodb_db]
        
        # Run connection quality test
        test_connection_quality(client)
        
        # Quick data check
        print("\n📊 Database Statistics:")
        total_levels = db.levels.count_documents({})
        total_users = db.users.count_documents({})
        total_records = db.records.count_documents({})
        
        print(f"   • Levels: {total_levels:,}")
        print(f"   • Users: {total_users:,}")
        print(f"   • Records: {total_records:,}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
