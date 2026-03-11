#!/usr/bin/env python3
"""
MongoDB Connection Health Check
Run this periodically to monitor your MongoDB Atlas connection quality
"""

import os
import time
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# MongoDB configuration
mongodb_uri = os.environ.get('MONGODB_URI')
mongodb_db = os.environ.get('MONGODB_DB', 'rtl_database')

def run_health_check():
    """Comprehensive MongoDB health check"""
    print("=" * 70)
    print(f"MongoDB Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    metrics = {
        'connection_time': None,
        'ping_time': None,
        'query_time': None,
        'total_levels': None,
        'total_users': None,
        'total_records': None,
        'errors': []
    }
    
    try:
        # Test 1: Connection Time
        print("\n[1/4] Testing connection time...")
        start = time.time()
        
        client = MongoClient(
            mongodb_uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True,
            serverSelectionTimeoutMS=30000,
            socketTimeoutMS=45000,
            connectTimeoutMS=30000,
            maxPoolSize=10,
            minPoolSize=2,
            retryWrites=True,
            retryReads=True,
            directConnection=False,
            connect=False
        )
        
        db = client[mongodb_db]
        metrics['connection_time'] = time.time() - start
        print(f"✅ Connected in {metrics['connection_time']:.2f}s")
        
        # Rate connection quality
        if metrics['connection_time'] < 5:
            print("   Quality: ⭐⭐⭐⭐⭐ Excellent (<5s)")
        elif metrics['connection_time'] < 10:
            print("   Quality: ⭐⭐⭐⭐ Good (<10s)")
        elif metrics['connection_time'] < 20:
            print("   Quality: ⭐⭐⭐ Acceptable (<20s)")
        elif metrics['connection_time'] < 30:
            print("   Quality: ⭐⭐ Fair (approaching timeout)")
        else:
            print("   Quality: ⭐ Poor (risk of timeout)")
        
        # Test 2: Ping Time
        print("\n[2/4] Testing ping response...")
        start = time.time()
        client.admin.command('ping', maxTimeMS=30000)
        metrics['ping_time'] = time.time() - start
        print(f"✅ Ping: {metrics['ping_time']*1000:.0f}ms")
        
        # Test 3: Query Performance
        print("\n[3/4] Testing query performance...")
        start = time.time()
        
        metrics['total_levels'] = db.levels.count_documents({})
        metrics['total_users'] = db.users.count_documents({})
        metrics['total_records'] = db.records.count_documents({})
        
        metrics['query_time'] = time.time() - start
        total_docs = metrics['total_levels'] + metrics['total_users'] + metrics['total_records']
        print(f"✅ Counted {total_docs:,} documents in {metrics['query_time']:.2f}s")
        
        # Test 4: Sample Query
        print("\n[4/4] Testing sample query...")
        start = time.time()
        
        levels = list(db.levels.find({}, max_time_ms=60000).limit(10))
        sample_query_time = time.time() - start
        print(f"✅ Retrieved {len(levels)} levels in {sample_query_time:.2f}s")
        
        # Overall Assessment
        print("\n" + "=" * 70)
        print("HEALTH ASSESSMENT")
        print("=" * 70)
        
        issues = []
        
        if metrics['connection_time'] > 25:
            issues.append("⚠️  Connection time is very high (near timeout)")
        elif metrics['connection_time'] > 15:
            issues.append("⚠️  Connection time is elevated")
            
        if metrics['query_time'] > 5:
            issues.append("⚠️  Query performance is slow")
            
        if sample_query_time > 3:
            issues.append("⚠️  Individual queries are slow")
        
        if issues:
            print("\nIssues Detected:")
            for issue in issues:
                print(f"  {issue}")
            print("\nRecommendations:")
            if "Connection time" in str(issues):
                print("  - Check MongoDB Atlas network access settings")
                print("  - Verify IP whitelist includes your location")
                print("  - Consider upgrading MongoDB Atlas tier")
            if "Query" in str(issues) or "queries" in str(issues):
                print("  - Review database indexes")
                print("  - Check MongoDB Atlas cluster load")
                print("  - Consider query optimization")
        else:
            print("\n✅ All systems healthy!")
            print("   Connection and query times are within acceptable ranges.")
        
        # Database Stats
        print("\n" + "=" * 70)
        print("DATABASE STATISTICS")
        print("=" * 70)
        print(f"Levels:   {metrics['total_levels']:,}")
        print(f"Users:    {metrics['total_users']:,}")
        print(f"Records:  {metrics['total_records']:,}")
        
        # Performance Summary
        print("\n" + "=" * 70)
        print("PERFORMANCE SUMMARY")
        print("=" * 70)
        print(f"Connection Time:  {metrics['connection_time']:.2f}s")
        print(f"Ping Time:        {metrics['ping_time']*1000:.0f}ms")
        print(f"Count Query Time: {metrics['query_time']:.2f}s")
        print(f"Sample Query Time:{sample_query_time:.2f}s")
        
        return len(issues) == 0
        
    except Exception as e:
        error_msg = f"❌ Health check failed: {e}"
        print(error_msg)
        metrics['errors'].append(str(e))
        
        print("\n" + "=" * 70)
        print("CRITICAL ERROR")
        print("=" * 70)
        print("MongoDB connection test failed!")
        print("\nTroubleshooting steps:")
        print("  1. Check MongoDB Atlas cluster status")
        print("  2. Verify network access whitelist")
        print("  3. Check internet connection")
        print("  4. Restart MongoDB Atlas cluster if needed")
        
        return False
    
    finally:
        # Cleanup
        try:
            if 'client' in locals():
                client.close()
        except:
            pass

if __name__ == "__main__":
    success = run_health_check()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Health check completed successfully")
    else:
        print("❌ Health check detected issues")
    print("=" * 70)
    
    # Exit with appropriate code
    exit(0 if success else 1)
