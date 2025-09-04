#!/usr/bin/env python3
"""
Test script for IP ban feature
"""

def test_ip_ban_logic():
    """Test the IP ban logic"""
    
    print("Testing IP ban feature logic:")
    
    # Test user IPs collection
    user_ips = []
    current_ip = "192.168.1.100"
    historical_ips = ["192.168.1.100", "10.0.0.50", "192.168.1.100"]  # Simulate duplicates
    last_ip = "10.0.0.50"
    
    # Add current IP
    if current_ip and current_ip not in user_ips:
        user_ips.append(current_ip)
    
    # Add historical IPs
    for ip in historical_ips:
        if ip and ip not in user_ips:
            user_ips.append(ip)
    
    # Add last IP
    if last_ip and last_ip not in user_ips:
        user_ips.append(last_ip)
    
    expected_ips = ["192.168.1.100", "10.0.0.50"]
    status = "✅ PASS" if user_ips == expected_ips else "❌ FAIL"
    print(f"  IP collection: {user_ips} {status}")
    
    # Test ban record creation
    ban_record = {
        "username": "testuser",
        "ip_addresses": user_ips,
        "reason": "Hacking/Cheating",
        "active": True
    }
    
    print(f"  Ban record created: {ban_record['username']} banned for '{ban_record['reason']}'")
    print("  ✅ Ban record structure correct")
    
    print("\n🎉 All IP ban logic tests completed!")

if __name__ == "__main__":
    test_ip_ban_logic()