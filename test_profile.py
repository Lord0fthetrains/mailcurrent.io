#!/usr/bin/env python3
"""
Test script to verify profile functionality
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:3099"
API_BASE = f"{BASE_URL}/api/v1"

def test_profile_functionality():
    """Test the profile functionality"""
    
    # Test data
    test_user = {
        "email": "profile_test@example.com",
        "password": "testpass123",
        "password_confirm": "testpass123",
        "first_name": "Profile",
        "last_name": "Test",
        "company_name": "Test Company",
        "phone": "+1234567890"
    }
    
    print("🧪 Testing Profile Functionality")
    print("=" * 50)
    
    # Step 1: Register a new user
    print("1. Registering new user...")
    register_response = requests.post(f"{API_BASE}/accounts/register/", json=test_user)
    
    if register_response.status_code == 201:
        register_data = register_response.json()
        token = register_data['token']
        print(f"   ✅ User registered successfully")
        print(f"   📧 Email: {test_user['email']}")
        print(f"   🔑 Token: {token[:20]}...")
    else:
        print(f"   ❌ Registration failed: {register_response.status_code}")
        print(f"   Response: {register_response.text}")
        return
    
    # Step 2: Test profile API
    print("\n2. Testing profile API...")
    headers = {"Authorization": f"Token {token}"}
    profile_response = requests.get(f"{API_BASE}/accounts/profile/", headers=headers)
    
    if profile_response.status_code == 200:
        profile_data = profile_response.json()
        print(f"   ✅ Profile API working")
        print(f"   👤 Name: {profile_data['first_name']} {profile_data['last_name']}")
        print(f"   📧 Email: {profile_data['email']}")
        print(f"   🏢 Company: {profile_data['company_name']}")
        print(f"   📞 Phone: {profile_data['phone']}")
        print(f"   ✅ Verified: {profile_data['is_verified']}")
        print(f"   📅 Joined: {profile_data['date_joined']}")
    else:
        print(f"   ❌ Profile API failed: {profile_response.status_code}")
        print(f"   Response: {profile_response.text}")
        return
    
    # Step 3: Test profile update
    print("\n3. Testing profile update...")
    update_data = {
        "email": test_user['email'],
        "first_name": "Updated",
        "last_name": "Profile",
        "company_name": "Updated Company",
        "phone": "+9876543210"
    }
    
    update_response = requests.put(f"{API_BASE}/accounts/profile/", 
                                 json=update_data, headers=headers)
    
    if update_response.status_code == 200:
        print(f"   ✅ Profile updated successfully")
        
        # Verify the update
        verify_response = requests.get(f"{API_BASE}/accounts/profile/", headers=headers)
        if verify_response.status_code == 200:
            updated_profile = verify_response.json()
            print(f"   👤 Updated Name: {updated_profile['first_name']} {updated_profile['last_name']}")
            print(f"   🏢 Updated Company: {updated_profile['company_name']}")
            print(f"   📞 Updated Phone: {updated_profile['phone']}")
    else:
        print(f"   ❌ Profile update failed: {update_response.status_code}")
        print(f"   Response: {update_response.text}")
    
    # Step 4: Test verification email
    print("\n4. Testing verification email...")
    verify_response = requests.post(f"{API_BASE}/accounts/send-verification/", headers=headers)
    
    if verify_response.status_code == 200:
        verify_data = verify_response.json()
        print(f"   ✅ Verification email sent: {verify_data['message']}")
    else:
        print(f"   ❌ Verification email failed: {verify_response.status_code}")
        print(f"   Response: {verify_response.text}")
    
    # Step 5: Test API keys
    print("\n5. Testing API keys...")
    api_keys_response = requests.get(f"{API_BASE}/accounts/api-keys/", headers=headers)
    
    if api_keys_response.status_code == 200:
        api_keys_data = api_keys_response.json()
        print(f"   ✅ API keys retrieved: {len(api_keys_data['api_keys'])} keys")
        for key in api_keys_data['api_keys']:
            print(f"   🔑 Key: {key['name']} - {key['key'][:10]}...")
    else:
        print(f"   ❌ API keys failed: {api_keys_response.status_code}")
        print(f"   Response: {api_keys_response.text}")
    
    print("\n" + "=" * 50)
    print("🎉 Profile functionality test completed!")
    print(f"📧 Test user: {test_user['email']}")
    print(f"🔑 Token: {token[:20]}...")

if __name__ == "__main__":
    test_profile_functionality()
