import pytest
import json
import time
from unittest.mock import Mock, patch
import requests

from src.external.bricklink_client import BrickLinkClient
from src.models.schemas import MarketData


class TestBrickLinkClient:
    @pytest.fixture
    def client(self):
        """Create BrickLinkClient with test credentials"""
        with patch('src.external.bricklink_client.settings') as mock_settings:
            mock_settings.bricklink_consumer_key = "test_consumer_key"
            mock_settings.bricklink_consumer_secret = "test_consumer_secret" 
            mock_settings.bricklink_token_value = "test_token_value"
            mock_settings.bricklink_token_secret = "test_token_secret"
            return BrickLinkClient()
    
    @pytest.fixture
    def client_no_keys(self):
        """Create BrickLinkClient with no credentials"""
        with patch('src.external.bricklink_client.settings') as mock_settings:
            mock_settings.bricklink_consumer_key = None
            mock_settings.bricklink_consumer_secret = None
            mock_settings.bricklink_token_value = None
            mock_settings.bricklink_token_secret = None
            return BrickLinkClient()

    def test_init_with_credentials(self, client):
        """Test client initialization with credentials"""
        assert client.consumer_key == "test_consumer_key"
        assert client.consumer_secret == "test_consumer_secret"
        assert client.token_value == "test_token_value"
        assert client.token_secret == "test_token_secret"
        assert client.BASE_URL == "https://api.bricklink.com/api/store/v1"

    def test_generate_oauth_signature(self, client):
        """Test OAuth signature generation"""
        method = "GET"
        url = "https://api.bricklink.com/api/store/v1/items/MINIFIG"
        params = {
            "oauth_consumer_key": "test_consumer_key",
            "oauth_token": "test_token_value",
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": "1234567890",
            "oauth_nonce": "987654321",
            "oauth_version": "1.0",
        }
        
        signature = client._generate_oauth_signature(method, url, params)
        
        # Should return a URL-encoded base64 string
        assert isinstance(signature, str)
        assert len(signature) > 0
        # Should be URL-encoded (no + or / characters from base64)
        assert '+' not in signature.replace('%2B', '')  # Allow URL-encoded +
        assert '/' not in signature.replace('%2F', '')  # Allow URL-encoded /

    def test_get_oauth_headers(self, client):
        """Test OAuth header generation"""
        with patch('time.time', return_value=1234567890.0):
            headers = client._get_oauth_headers("GET", "https://api.bricklink.com/api/store/v1/items/MINIFIG")
        
        assert "Authorization" in headers
        auth_header = headers["Authorization"]
        assert auth_header.startswith("OAuth ")
        
        # Check that all required OAuth parameters are present
        assert "oauth_consumer_key" in auth_header
        assert "oauth_token" in auth_header
        assert "oauth_signature_method" in auth_header
        assert "oauth_timestamp" in auth_header
        assert "oauth_nonce" in auth_header
        assert "oauth_version" in auth_header
        assert "oauth_signature" in auth_header

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_success(self, mock_get, client):
        """Test successful item search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"no": "sw0001a", "name": "Luke Skywalker"},
                {"no": "sw0002", "name": "Princess Leia"}
            ]
        }
        mock_get.return_value = mock_response
        
        results = client.search_items("MINIFIG", "Luke Skywalker")
        
        assert len(results) == 2
        assert results[0]["no"] == "sw0001a"
        assert results[1]["name"] == "Princess Leia"
        mock_get.assert_called_once()

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_no_credentials(self, mock_get, client_no_keys):
        """Test search with no credentials"""
        results = client_no_keys.search_items("MINIFIG", "Luke Skywalker")
        
        assert results == []
        mock_get.assert_not_called()

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_ip_mismatch(self, mock_get, client):
        """Test search with IP mismatch error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "meta": {
                "description": "TOKEN_IP_MISMATCHED: consumer: ABC123 IP: 1.2.3.4",
                "message": "BAD_OAUTH_REQUEST",
                "code": 401
            }
        }
        mock_get.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            results = client.search_items("MINIFIG", "Luke Skywalker")
        
        assert results == []
        mock_print.assert_called_with("BrickLink API: IP address not whitelisted for these credentials")

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_auth_error(self, mock_get, client):
        """Test search with other auth error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "meta": {
                "description": "Invalid token",
                "message": "INVALID_TOKEN",
                "code": 401
            }
        }
        mock_get.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            results = client.search_items("MINIFIG", "Luke Skywalker")
        
        assert results == []
        mock_print.assert_called_with("BrickLink API authentication failed: INVALID_TOKEN")

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_server_error(self, mock_get, client):
        """Test search with server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            results = client.search_items("MINIFIG", "Luke Skywalker")
        
        assert results == []
        mock_print.assert_called_with("BrickLink API error: 500 - Internal Server Error")

    @patch('src.external.bricklink_client.requests.get')
    def test_search_items_exception(self, mock_get, client):
        """Test search with network exception"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        with patch('builtins.print') as mock_print:
            results = client.search_items("MINIFIG", "Luke Skywalker")
        
        assert results == []
        mock_print.assert_called_with("Error calling BrickLink API: Network error")

    @patch('src.external.bricklink_client.requests.get')
    def test_get_price_guide_success(self, mock_get, client):
        """Test successful price guide retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "avg_price": 25.50,
                "times_sold": 15
            }
        }
        mock_get.return_value = mock_response
        
        result = client.get_price_guide("MINIFIG", "sw0001a", "U")
        
        assert isinstance(result, MarketData)
        assert result.current_price == 25.50
        assert result.avg_price_6m == 25.50
        assert result.times_sold == 15
        assert result.availability == "uncommon"  # 15 sales = uncommon
        mock_get.assert_called_once()

    @patch('src.external.bricklink_client.requests.get')
    def test_get_price_guide_no_data(self, mock_get, client):
        """Test price guide with empty data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {}}
        mock_get.return_value = mock_response
        
        result = client.get_price_guide("MINIFIG", "sw0001a", "U")
        
        assert isinstance(result, MarketData)
        assert result.current_price is None
        assert result.times_sold is None
        assert result.availability == "very_rare"  # 0 sales = very_rare

    @patch('src.external.bricklink_client.requests.get')
    def test_get_price_guide_no_credentials(self, mock_get, client_no_keys):
        """Test price guide with no credentials"""
        result = client_no_keys.get_price_guide("MINIFIG", "sw0001a", "U")
        
        assert result is None
        mock_get.assert_not_called()

    @patch('src.external.bricklink_client.requests.get')
    def test_get_price_guide_ip_mismatch(self, mock_get, client):
        """Test price guide with IP mismatch error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "meta": {
                "description": "TOKEN_IP_MISMATCHED: consumer: ABC123 IP: 1.2.3.4",
                "message": "BAD_OAUTH_REQUEST"
            }
        }
        mock_get.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            result = client.get_price_guide("MINIFIG", "sw0001a", "U")
        
        assert result is None
        mock_print.assert_called_with("BrickLink API: IP address not whitelisted for these credentials")

    def test_determine_availability(self, client):
        """Test availability determination logic"""
        assert client._determine_availability(0) == "very_rare"
        assert client._determine_availability(5) == "rare"
        assert client._determine_availability(25) == "uncommon"
        assert client._determine_availability(100) == "common"

    @patch('src.external.bricklink_client.requests.get')
    def test_get_item_details_success(self, mock_get, client):
        """Test successful item details retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "no": "sw0001a",
                "name": "Luke Skywalker",
                "type": "MINIFIG",
                "category_id": 65
            }
        }
        mock_get.return_value = mock_response
        
        result = client.get_item_details("MINIFIG", "sw0001a")
        
        assert result["no"] == "sw0001a"
        assert result["name"] == "Luke Skywalker"
        assert result["type"] == "MINIFIG"

    @patch('src.external.bricklink_client.requests.get')
    def test_get_item_details_no_credentials(self, mock_get, client_no_keys):
        """Test item details with no credentials"""
        result = client_no_keys.get_item_details("MINIFIG", "sw0001a")
        
        assert result is None
        mock_get.assert_not_called()

    def test_get_similar_items(self, client):
        """Test similar items search"""
        with patch.object(client, 'search_items') as mock_search:
            mock_search.side_effect = [
                [{"no": "sw0001a", "name": "Luke Skywalker", "category_name": "Star Wars"}],
                [{"no": "7140", "name": "X-wing Fighter", "category_name": "Star Wars"}]
            ]
            
            results = client.get_similar_items("Luke", "Star Wars")
            
            assert len(results) == 2
            assert results[0]["no"] == "sw0001a"
            assert results[1]["no"] == "7140"
            # Should call search_items twice (MINIFIG and SET)
            assert mock_search.call_count == 2

    def test_get_similar_items_theme_filter(self, client):
        """Test similar items with theme filtering"""
        with patch.object(client, 'search_items') as mock_search:
            mock_search.side_effect = [
                [
                    {"no": "sw0001a", "name": "Luke Skywalker", "category_name": "Star Wars"},
                    {"no": "cas123", "name": "Knight", "category_name": "Castle"}
                ],
                []
            ]
            
            results = client.get_similar_items("Luke", "Star Wars")
            
            # Should filter out the Castle item
            assert len(results) == 1
            assert results[0]["no"] == "sw0001a"

    @patch('src.external.bricklink_client.requests.get')
    def test_api_call_parameters(self, mock_get, client):
        """Test that API calls use correct parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response
        
        client.search_items("MINIFIG", "Luke Skywalker")
        
        # Verify the call was made with correct URL and parameters
        call_args = mock_get.call_args
        url = call_args[1]['params']
        assert url['name'] == "Luke Skywalker"
        
        # Verify headers contain OAuth authorization
        headers = call_args[1]['headers']
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith('OAuth ')


class TestBrickLinkClientEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def client(self):
        """Create BrickLinkClient with test credentials"""
        with patch('src.external.bricklink_client.settings') as mock_settings:
            mock_settings.bricklink_consumer_key = "test_key"
            mock_settings.bricklink_consumer_secret = "test_secret"
            mock_settings.bricklink_token_value = "test_token"
            mock_settings.bricklink_token_secret = "test_token_secret"
            return BrickLinkClient()

    def test_oauth_signature_special_characters(self, client):
        """Test OAuth signature with special characters"""
        method = "GET"
        url = "https://api.bricklink.com/api/store/v1/items/MINIFIG"
        params = {
            "oauth_consumer_key": "test&key=special",
            "oauth_token": "token+with/chars",
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": "1234567890",
            "oauth_nonce": "987654321",
            "oauth_version": "1.0",
            "name": "Luke & Leia"  # Special characters in search
        }
        
        # Should not raise an exception
        signature = client._generate_oauth_signature(method, url, params)
        assert isinstance(signature, str)
        assert len(signature) > 0

    @patch('src.external.bricklink_client.requests.get')
    def test_malformed_json_response(self, mock_get, client):
        """Test handling of malformed JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response
        
        with patch('builtins.print') as mock_print:
            results = client.search_items("MINIFIG", "Luke")
        
        assert results == []

    def test_empty_search_term(self, client):
        """Test search with empty search term"""
        with patch.object(client, '_get_oauth_headers') as mock_headers:
            mock_headers.return_value = {"Authorization": "OAuth test"}
            
            with patch('src.external.bricklink_client.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": []}
                mock_get.return_value = mock_response
                
                results = client.search_items("MINIFIG", "")
                
                # Should still make the call
                assert results == []
                mock_get.assert_called_once()

    def test_price_guide_different_conditions(self, client):
        """Test price guide with different condition parameters"""
        with patch('src.external.bricklink_client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"avg_price": 10.0}}
            mock_get.return_value = mock_response
            
            # Test with 'N' (new) condition
            result = client.get_price_guide("MINIFIG", "sw0001a", "N")
            assert result is not None
            
            # Verify the condition was passed correctly
            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['new_or_used'] == 'N'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])