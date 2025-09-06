#!/usr/bin/env python3
"""
Verify that the API test fixes are working correctly.
"""

import sys

def test_schema_compatibility():
    """Test that schemas work with the expected field names"""
    print("🔍 Testing Schema Compatibility...")
    
    try:
        from src.models.schemas import ValuationResult, RecommendationCategory, PlatformType
        
        # Test that ValuationResult accepts the correct field names
        result = ValuationResult(
            estimated_value=75.50,  # This should work now
            confidence_score=0.8,
            recommendation=RecommendationCategory.RESALE,
            reasoning="Test reasoning",
            suggested_platforms=[PlatformType.BRICKLINK]
        )
        
        print("✅ ValuationResult schema accepts correct fields")
        print(f"   estimated_value: {result.estimated_value}")
        print(f"   recommendation: {result.recommendation}")
        return True
        
    except Exception as e:
        print(f"❌ Schema compatibility failed: {e}")
        return False

def test_repository_methods():
    """Test that repository methods exist"""
    print("\n🗄️  Testing Repository Methods...")
    
    try:
        from src.database.repository import ValuationRepository, InventoryRepository
        
        # Check ValuationRepository methods
        val_repo_methods = dir(ValuationRepository)
        required_val_methods = [
            'list_valuation_records',
            'get_valuation_record', 
            'create_valuation_record'
        ]
        
        for method in required_val_methods:
            if method in val_repo_methods:
                print(f"✅ ValuationRepository.{method}")
            else:
                print(f"❌ ValuationRepository.{method} missing")
                return False
        
        # Check InventoryRepository methods
        inv_repo_methods = dir(InventoryRepository)
        required_inv_methods = [
            'list_inventory',
            'get_inventory_summary',
            'create_from_valuation'
        ]
        
        for method in required_inv_methods:
            if method in inv_repo_methods:
                print(f"✅ InventoryRepository.{method}")
            else:
                print(f"❌ InventoryRepository.{method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Repository method check failed: {e}")
        return False

def test_repository_initialization():
    """Test that repositories can be initialized with Session objects"""
    print("\n🔧 Testing Repository Initialization...")
    
    try:
        from src.database.repository import ValuationRepository, InventoryRepository
        from unittest.mock import Mock
        
        # Mock a SQLAlchemy session
        mock_session = Mock()
        mock_session.query = Mock()  # This is how we detect it's a Session
        
        # Test ValuationRepository
        val_repo = ValuationRepository(mock_session)
        print("✅ ValuationRepository initialized with Session")
        
        # Test InventoryRepository  
        inv_repo = InventoryRepository(mock_session)
        print("✅ InventoryRepository initialized with Session")
        
        return True
        
    except Exception as e:
        print(f"❌ Repository initialization failed: {e}")
        return False

def test_api_imports():
    """Test that API can be imported"""
    print("\n🌐 Testing API Imports...")
    
    try:
        from src.api.main import app
        print("✅ FastAPI app imported successfully")
        
        # Check if static directory exists
        import os
        if os.path.exists("src/web/static"):
            print("✅ Static directory exists")
        else:
            print("⚠️  Static directory missing (will be auto-created)")
        
        return True
        
    except Exception as e:
        print(f"❌ API import failed: {e}")
        return False

def test_simple_endpoint():
    """Test a simple endpoint without complex setup"""
    print("\n🧪 Testing Simple Endpoint...")
    
    try:
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        response = client.get("/health")
        
        print(f"✅ Health endpoint responded: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            return True
        else:
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Simple endpoint test failed: {e}")
        return False

def main():
    print("🛠️  API Test Fix Verification")
    print("=" * 50)
    
    tests = [
        test_schema_compatibility,
        test_repository_methods,
        test_repository_initialization,
        test_api_imports,
        test_simple_endpoint
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n📊 Summary:")
    print("=" * 20)
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test.__name__}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All fixes verified! API tests should now work much better.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")  
        print("2. Run API tests: ./run_tests.sh api")
        print("3. Or run simple tests: pytest tests/test_api_simple.py -v")
        return 0
    else:
        print(f"\n⚠️  {total - passed} issues remain. Check the failures above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())