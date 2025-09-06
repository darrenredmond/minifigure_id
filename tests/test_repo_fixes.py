#!/usr/bin/env python3
"""
Test that the repository recursion fixes work correctly.
"""

import sys
from unittest.mock import Mock

def test_repository_recursion_fix():
    """Test that repositories don't have recursion errors"""
    print("🔧 Testing Repository Recursion Fix...")
    
    try:
        from src.database.repository import ValuationRepository, InventoryRepository
        
        # Test with mock db_manager (non-Session object)
        mock_db_manager = Mock()
        mock_context = Mock()
        mock_session = Mock()
        
        # Set up the mock context manager
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session_context = Mock(return_value=mock_context)
        
        # Test ValuationRepository with db_manager
        val_repo = ValuationRepository(mock_db_manager)
        print("✅ ValuationRepository created with db_manager")
        
        # Test InventoryRepository with db_manager  
        inv_repo = InventoryRepository(mock_db_manager)
        print("✅ InventoryRepository created with db_manager")
        
        # Test with mock Session object
        mock_session = Mock()
        mock_session.query = Mock()  # This is the marker for Session objects
        
        # Test ValuationRepository with Session
        val_repo_session = ValuationRepository(mock_session)
        print("✅ ValuationRepository created with Session")
        
        # Test InventoryRepository with Session
        inv_repo_session = InventoryRepository(mock_session)
        print("✅ InventoryRepository created with Session")
        
        # Test that context managers work without recursion
        with val_repo._get_session_context() as session:
            print("✅ ValuationRepository context manager works")
        
        with inv_repo._get_session_context() as session:
            print("✅ InventoryRepository context manager works")
            
        with val_repo_session._get_session_context() as session:
            print("✅ ValuationRepository Session context works")
        
        with inv_repo_session._get_session_context() as session:
            print("✅ InventoryRepository Session context works")
        
        return True
        
    except RecursionError:
        print("❌ Recursion error still present")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

def test_repository_methods_exist():
    """Test that the API compatibility methods exist"""
    print("\n🔍 Testing Repository API Compatibility Methods...")
    
    try:
        from src.database.repository import ValuationRepository, InventoryRepository
        
        # Create mock instances
        mock_db_manager = Mock()
        mock_db_manager.get_session_context = Mock()
        
        val_repo = ValuationRepository(mock_db_manager)
        inv_repo = InventoryRepository(mock_db_manager)
        
        # Check ValuationRepository methods
        val_methods = [
            'list_valuation_records',
            'get_valuation_record', 
            'create_valuation_record'
        ]
        
        for method in val_methods:
            if hasattr(val_repo, method):
                print(f"✅ ValuationRepository.{method} exists")
            else:
                print(f"❌ ValuationRepository.{method} missing")
                return False
        
        # Check InventoryRepository methods
        inv_methods = [
            'list_inventory',
            'get_inventory_summary',
            'create_from_valuation'
        ]
        
        for method in inv_methods:
            if hasattr(inv_repo, method):
                print(f"✅ InventoryRepository.{method} exists")
            else:
                print(f"❌ InventoryRepository.{method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Method check failed: {e}")
        return False

def main():
    print("🛠️  Database Repository Fix Test")
    print("=" * 40)
    
    results = [
        test_repository_recursion_fix(),
        test_repository_methods_exist()
    ]
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All repository fixes verified!")
        print("The recursion errors should now be resolved.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} issues remain.")
        return 1

if __name__ == "__main__":
    sys.exit(main())