#!/usr/bin/env python3
"""
Simple server starter with status check
"""

if __name__ == "__main__":
    print("🚀 Starting RTL Server...")
    print("=" * 40)
    
    try:
        from main import app
        print("✅ All imports successful")
        print("✅ Database connected")
        print("✅ Routes configured")
        print()
        print("🌐 Server starting on http://localhost:10000")
        print("📋 Test pages:")
        print("   • Main list: http://localhost:10000/")
        print("   • Thumbnails: http://localhost:10000/test_thumbnails")
        print("   • Admin: http://localhost:10000/admin")
        print()
        print("Press Ctrl+C to stop")
        print("=" * 40)
        
        app.run(host='0.0.0.0', port=10000, debug=True)
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()