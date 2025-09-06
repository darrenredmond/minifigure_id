#!/usr/bin/env python3
"""
Validate test setup and dependencies for the LEGO Valuation System.
This script checks if tests can run properly.
"""

import sys
import os
import importlib

def check_dependency(module_name, description):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {e}")
        return False

def check_project_structure():
    """Check if project structure is correct"""
    required_paths = [
        'src/api/main.py',
        'src/models/schemas.py', 
        'src/database/database.py',
        'tests/test_api_endpoints.py',
        'tests/api_test_utils.py'
    ]
    
    # Check for static directory (required by FastAPI app)
    static_paths = [
        'src/web/static'
    ]
    
    print("\n📁 Project Structure:")
    all_good = True
    for path in required_paths:
        if os.path.exists(path):
            print(f"✅ {path}")
        else:
            print(f"❌ {path} - Missing")
            all_good = False
    
    # Check static directory (create if missing)
    print("\n📂 Static Files Directory:")
    for path in static_paths:
        if os.path.exists(path):
            print(f"✅ {path}")
        else:
            print(f"⚠️  {path} - Missing (will be auto-created)")
            try:
                os.makedirs(path, exist_ok=True)
                with open(f"{path}/.gitkeep", "w") as f:
                    f.write("# Static files directory\n")
                print(f"✅ Created {path}")
            except Exception as e:
                print(f"❌ Failed to create {path}: {e}")
                all_good = False
    
    return all_good

def main():
    print("🧱 LEGO Valuation System - Test Validation")
    print("=" * 50)
    
    print("\n🔍 Checking Dependencies:")
    deps_ok = True
    
    # Core Python modules
    deps_ok &= check_dependency('pytest', 'pytest (testing framework)')
    deps_ok &= check_dependency('fastapi', 'FastAPI (web framework)')
    deps_ok &= check_dependency('sqlalchemy', 'SQLAlchemy (database ORM)')
    deps_ok &= check_dependency('PIL', 'Pillow (image processing)')
    
    # Optional but recommended
    check_dependency('pytest_cov', 'pytest-cov (coverage reporting)')
    check_dependency('httpx', 'httpx (HTTP client for testing)')
    
    # Check project structure
    structure_ok = check_project_structure()
    
    # Try importing project modules
    print("\n🏗️  Project Module Imports:")
    project_ok = True
    try:
        from src.api.main import app
        print("✅ FastAPI app import")
    except Exception as e:
        print(f"❌ FastAPI app import: {e}")
        project_ok = False
    
    try:
        from src.models.schemas import LegoItem
        print("✅ Project schemas import")
    except Exception as e:
        print(f"❌ Project schemas import: {e}")
        project_ok = False
    
    # Try importing test modules  
    print("\n🧪 Test Module Imports:")
    test_imports_ok = True
    try:
        from tests.api_test_utils import TestDataFactory
        print("✅ Test utilities import")
    except Exception as e:
        print(f"❌ Test utilities import: {e}")
        test_imports_ok = False
    
    # Overall status
    print("\n📊 Summary:")
    print("=" * 30)
    
    if deps_ok and structure_ok and project_ok and test_imports_ok:
        print("🎉 All checks passed! Tests should run successfully.")
        print("\nTo run tests:")
        print("  ./run_tests.sh api")
        print("  pytest tests/test_api_endpoints.py -v")
        return 0
    else:
        print("⚠️  Some issues detected:")
        
        if not deps_ok:
            print("  • Install missing dependencies: pip install -r requirements.txt")
        
        if not structure_ok:
            print("  • Check project file structure")
        
        if not project_ok:
            print("  • Fix project module imports")
            
        if not test_imports_ok:
            print("  • Check test file imports")
        
        print("\nAfter fixing issues, tests should work with:")
        print("  python validate_tests.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())