#!/usr/bin/env python3
"""
Debug script to identify specific test failures and their causes.
"""

import sys
import traceback
from pathlib import Path

def test_basic_imports():
    """Test basic imports that tests depend on"""
    print("🔍 Testing Basic Imports:")
    
    try:
        import pytest
        print(f"✅ pytest {pytest.__version__}")
    except ImportError as e:
        print(f"❌ pytest: {e}")
        return False
    
    try:
        from fastapi.testclient import TestClient
        print("✅ FastAPI TestClient")
    except ImportError as e:
        print(f"❌ FastAPI TestClient: {e}")
        return False
    
    try:
        from sqlalchemy import create_engine
        print("✅ SQLAlchemy")
    except ImportError as e:
        print(f"❌ SQLAlchemy: {e}")
        return False
    
    return True

def test_app_import():
    """Test importing the FastAPI app"""
    print("\n🏗️  Testing App Import:")
    
    try:
        from src.api.main import app
        print("✅ FastAPI app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ FastAPI app import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ FastAPI app initialization failed: {e}")
        print(f"   Full error: {traceback.format_exc()}")
        return False

def test_client_creation():
    """Test creating a test client"""
    print("\n🧪 Testing Client Creation:")
    
    try:
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        print("✅ TestClient created successfully")
        return True, client
    except Exception as e:
        print(f"❌ TestClient creation failed: {e}")
        print(f"   Full error: {traceback.format_exc()}")
        return False, None

def test_basic_endpoints(client):
    """Test basic endpoints that should always work"""
    print("\n🌐 Testing Basic Endpoints:")
    
    if not client:
        print("❌ No client available for testing")
        return False
    
    # Test health endpoint
    try:
        response = client.get("/health")
        print(f"✅ Health endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    # Test root endpoint
    try:
        response = client.get("/")
        print(f"✅ Root endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    # Test OpenAPI schema
    try:
        response = client.get("/openapi.json")
        print(f"✅ OpenAPI schema: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenAPI schema failed: {e}")
    
    return True

def test_database_operations(client):
    """Test database-dependent operations"""
    print("\n🗄️  Testing Database Operations:")
    
    if not client:
        print("❌ No client available for testing")
        return False
    
    # Test valuations endpoint
    try:
        response = client.get("/valuations")
        print(f"✅ Valuations endpoint: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error response: {response.text}")
    except Exception as e:
        print(f"❌ Valuations endpoint failed: {e}")
    
    # Test inventory endpoint
    try:
        response = client.get("/inventory")
        print(f"✅ Inventory endpoint: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error response: {response.text}")
    except Exception as e:
        print(f"❌ Inventory endpoint failed: {e}")
    
    return True

def test_file_upload():
    """Test file upload functionality"""
    print("\n📁 Testing File Upload:")
    
    try:
        from src.api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test upload with no file (should fail validation)
        response = client.post("/upload")
        print(f"✅ Upload no file: {response.status_code} (expected 422)")
        
        # Test upload with fake file
        test_content = b"fake image data"
        response = client.post(
            "/upload",
            files={"file": ("test.jpg", test_content, "image/jpeg")}
        )
        print(f"✅ Upload with file: {response.status_code}")
        if response.status_code not in [200, 400, 500]:
            print(f"   Unexpected status. Response: {response.text}")
        
    except Exception as e:
        print(f"❌ File upload test failed: {e}")
        print(f"   Full error: {traceback.format_exc()}")

def run_actual_test():
    """Try running an actual test to see the exact error"""
    print("\n🧪 Running Actual Test:")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_api_simple.py::TestBasicEndpoints::test_health_endpoint", 
            "-v"
        ], capture_output=True, text=True, timeout=30)
        
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except FileNotFoundError:
        print("❌ pytest not found in PATH")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

def main():
    print("🧱 LEGO API Test Debug Tool")
    print("=" * 50)
    
    # Check basic setup
    if not test_basic_imports():
        print("\n💡 Fix: Install missing dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    
    # Check app import
    if not test_app_import():
        print("\n💡 Fix: Check project structure and dependencies")
        return 1
    
    # Check client creation
    success, client = test_client_creation()
    if not success:
        print("\n💡 Fix: Check app initialization and static directory")
        print("   mkdir -p src/web/static")
        return 1
    
    # Test basic endpoints
    test_basic_endpoints(client)
    
    # Test database operations
    test_database_operations(client)
    
    # Test file upload
    test_file_upload()
    
    # Try running actual test
    run_actual_test()
    
    print("\n✅ Debug complete!")
    print("\nNext steps:")
    print("1. Fix any issues identified above")
    print("2. Run: pytest tests/test_api_simple.py -v")
    print("3. If simple tests pass, try: pytest tests/test_api_endpoints.py -v")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())