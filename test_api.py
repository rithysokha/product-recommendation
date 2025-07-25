import requests
import json
import time

API_BASE_URL = "http://localhost:5000"

def test_api():
    """Test the recommendation API endpoints"""
    
    print("🚀 Testing Product Recommendation API")
    print("=" * 50)
    
    # Test health check
    try:
        print("\n1. Testing Health Check...")
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Status: {response.json()}")
        else:
            print("❌ Health check failed")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure the API is running on localhost:5000")
        return
    
    # Test stats endpoint
    print("\n2. Testing Statistics...")
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print("✅ Statistics retrieved successfully")
            print(f"   Total users: {stats.get('total_users', 0)}")
            print(f"   Total unique products: {stats.get('total_unique_products', 0)}")
            print(f"   Average recommendations per user: {stats.get('average_recommendations_per_user', 0)}")
            
            if stats.get('model_metrics'):
                print(f"   Model RMSE: {stats['model_metrics'].get('rmse', 'N/A')}")
        else:
            print("❌ Failed to get statistics")
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
    
    # Test users list
    print("\n3. Testing Users List...")
    try:
        response = requests.get(f"{API_BASE_URL}/users?per_page=5")
        if response.status_code == 200:
            users_data = response.json()
            print("✅ Users list retrieved successfully")
            print(f"   Total users: {users_data.get('total_users', 0)}")
            users = users_data.get('users', [])
            if users:
                print(f"   First 5 users: {users}")
                
                # Test recommendations for first user
                first_user = users[0]
                print(f"\n4. Testing Recommendations for User: {first_user}")
                rec_response = requests.get(f"{API_BASE_URL}/recommendations/{first_user}?limit=3")
                if rec_response.status_code == 200:
                    recommendations = rec_response.json()
                    print("✅ User recommendations retrieved successfully")
                    print(f"   User: {recommendations.get('user_id')}")
                    print(f"   Recommendations: {recommendations.get('recommendations', [])}")
                else:
                    print(f"❌ Failed to get recommendations: {rec_response.status_code}")
                    print(f"   Response: {rec_response.text}")
        else:
            print("❌ Failed to get users list")
    except Exception as e:
        print(f"❌ Error getting users: {e}")
    
    # Test multiple users recommendations
    print("\n5. Testing Multiple Users Recommendations...")
    try:
        response = requests.get(f"{API_BASE_URL}/users?per_page=3")
        if response.status_code == 200:
            users_data = response.json()
            users = users_data.get('users', [])[:3]  # Get first 3 users
            
            if users:
                payload = {
                    "user_ids": users,
                    "limit": 2
                }
                
                multi_response = requests.post(
                    f"{API_BASE_URL}/recommendations",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
                
                if multi_response.status_code == 200:
                    multi_recs = multi_response.json()
                    print("✅ Multiple user recommendations retrieved successfully")
                    print(f"   Users requested: {multi_recs.get('total_users_requested', 0)}")
                    print(f"   Users with recommendations: {multi_recs.get('users_with_recommendations', 0)}")
                    
                    results = multi_recs.get('results', {})
                    for user_id, recs in results.items():
                        print(f"   User {user_id}: {len(recs)} recommendations")
                else:
                    print(f"❌ Failed to get multiple recommendations: {multi_response.status_code}")
        
    except Exception as e:
        print(f"❌ Error testing multiple recommendations: {e}")
    
    # Test similar users
    print("\n6. Testing Similar Users...")
    try:
        response = requests.get(f"{API_BASE_URL}/users?per_page=1")
        if response.status_code == 200:
            users_data = response.json()
            users = users_data.get('users', [])
            
            if users:
                first_user = users[0]
                similar_response = requests.get(f"{API_BASE_URL}/users/{first_user}/similar?limit=3")
                
                if similar_response.status_code == 200:
                    similar_data = similar_response.json()
                    print("✅ Similar users retrieved successfully")
                    print(f"   User: {similar_data.get('user_id')}")
                    print(f"   Similar users found: {similar_data.get('total_similar_users', 0)}")
                    
                    similar_users = similar_data.get('similar_users', [])
                    for similar_user in similar_users[:2]:
                        print(f"   Similar user: {similar_user.get('user_id')} (similarity: {similar_user.get('similarity_score', 0):.3f})")
                else:
                    print(f"❌ Failed to get similar users: {similar_response.status_code}")
    except Exception as e:
        print(f"❌ Error testing similar users: {e}")
    
    print("\n🎉 API Testing Complete!")
    print("\n📚 Available Endpoints:")
    print("   GET  /health                          - Health check")
    print("   GET  /stats                           - Overall statistics")
    print("   GET  /users                           - List users with pagination")
    print("   GET  /recommendations/<user_id>       - Get recommendations for a user")
    print("   POST /recommendations                 - Get recommendations for multiple users")
    print("   GET  /users/<user_id>/similar         - Find similar users")
    print("   GET  /products/<product_id>/users     - Get users who have a product recommended")
    print("   POST /reload                          - Reload recommendation data")

if __name__ == "__main__":
    test_api()
