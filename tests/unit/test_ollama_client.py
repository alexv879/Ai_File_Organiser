"""
Unit tests for OllamaClient.

Tests Ollama AI integration for file classification.
"""

import pytest  # type: ignore[import-untyped]
import json
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Import the Ollama client
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ai.ollama_client import OllamaClient


@pytest.fixture
def ollama_client():
    """Create an OllamaClient instance."""
    return OllamaClient(
        base_url="http://localhost:11434",
        model="qwen2.5:7b-instruct",
        timeout=30
    )


@pytest.fixture
def mock_requests():
    """Create a mock requests module."""
    with patch('ai.ollama_client.requests') as mock_req:
        yield mock_req


class TestOllamaClientInit:
    """Test OllamaClient initialization."""
    
    def test_init_default_values(self):
        """Test initialization with default values."""
        client = OllamaClient()
        assert client.base_url == "http://localhost:11434"
        assert client.model == "qwen2.5:7b-instruct"
        assert client.timeout == 30
    
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        client = OllamaClient(
            base_url="http://custom:8080",
            model="custom-model",
            timeout=60
        )
        assert client.base_url == "http://custom:8080"
        assert client.model == "custom-model"
        assert client.timeout == 60
    
    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        client = OllamaClient(base_url="http://localhost:11434/")
        assert client.base_url == "http://localhost:11434"


class TestServiceAvailability:
    """Test Ollama service availability checking."""
    
    def test_is_available_success(self, ollama_client, mock_requests):
        """Test successful availability check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        assert ollama_client.is_available() is True
        mock_requests.get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5
        )
    
    def test_is_available_failure(self, ollama_client, mock_requests):
        """Test availability check when service is down."""
        mock_requests.get.side_effect = Exception("Connection refused")
        
        assert ollama_client.is_available() is False
    
    def test_is_available_wrong_status(self, ollama_client, mock_requests):
        """Test availability check with non-200 status."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response
        
        assert ollama_client.is_available() is False


class TestModelListing:
    """Test model listing functionality."""
    
    def test_list_models_success(self, ollama_client, mock_requests):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama3'},
                {'name': 'mistral'},
                {'name': 'codellama'}
            ]
        }
        mock_requests.get.return_value = mock_response
        
        models = ollama_client.list_models()
        
        assert len(models) == 3
        assert 'llama3' in models
        assert 'mistral' in models
        assert 'codellama' in models
    
    def test_list_models_failure(self, ollama_client, mock_requests):
        """Test model listing when request fails."""
        mock_requests.get.side_effect = Exception("Connection error")
        
        models = ollama_client.list_models()
        
        assert models == []
    
    def test_list_models_empty(self, ollama_client, mock_requests):
        """Test model listing with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'models': []}
        mock_requests.get.return_value = mock_response
        
        models = ollama_client.list_models()
        
        assert models == []


class TestFileClassification:
    """Test file classification functionality."""
    
    def test_classify_file_success(self, ollama_client, mock_requests):
        """Test successful file classification."""
        # Mock availability check
        mock_avail_response = Mock()
        mock_avail_response.status_code = 200
        
        # Mock classification response
        mock_classify_response = Mock()
        mock_classify_response.status_code = 200
        mock_classify_response.json.return_value = {
            'response': json.dumps({
                'category': 'Documents',
                'suggested_path': 'Documents/Reports',
                'rename': None,
                'reason': 'Financial report document'
            })
        }
        
        mock_requests.get.return_value = mock_avail_response
        mock_requests.post.return_value = mock_classify_response
        
        result = ollama_client.classify_file(
            filename="Q4_Report.pdf",
            extension=".pdf",
            text_snippet="Quarterly financial report...",
            file_size=204800
        )
        
        assert result['success'] is True
        assert result['category'] == 'Documents'
        assert result['suggested_path'] == 'Documents/Reports'
        assert 'reason' in result
    
    def test_classify_file_service_unavailable(self, ollama_client, mock_requests):
        """Test classification when service is unavailable."""
        mock_requests.get.side_effect = Exception("Connection refused")
        
        result = ollama_client.classify_file(
            filename="test.txt",
            extension=".txt"
        )
        
        assert result['success'] is False
        assert result['category'] == 'Unsorted'
        assert 'error' in result
    
    def test_classify_file_json_in_code_block(self, ollama_client, mock_requests):
        """Test classification with JSON in markdown code block."""
        mock_avail_response = Mock()
        mock_avail_response.status_code = 200
        
        mock_classify_response = Mock()
        mock_classify_response.status_code = 200
        mock_classify_response.json.return_value = {
            'response': '```json\n{"category": "Images", "suggested_path": "Images/Photos", "rename": null, "reason": "Photo file"}\n```'
        }
        
        mock_requests.get.return_value = mock_avail_response
        mock_requests.post.return_value = mock_classify_response
        
        result = ollama_client.classify_file(
            filename="photo.jpg",
            extension=".jpg"
        )
        
        assert result['success'] is True
        assert result['category'] == 'Images'
    
    def test_classify_file_invalid_json(self, ollama_client, mock_requests):
        """Test classification with invalid JSON response."""
        mock_avail_response = Mock()
        mock_avail_response.status_code = 200
        
        mock_classify_response = Mock()
        mock_classify_response.status_code = 200
        mock_classify_response.json.return_value = {
            'response': 'This is not valid JSON'
        }
        
        mock_requests.get.return_value = mock_avail_response
        mock_requests.post.return_value = mock_classify_response
        
        result = ollama_client.classify_file(
            filename="test.txt",
            extension=".txt"
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert 'raw_response' in result
    
    def test_classify_file_timeout(self, ollama_client, mock_requests):
        """Test classification with timeout."""
        mock_avail_response = Mock()
        mock_avail_response.status_code = 200
        mock_requests.get.return_value = mock_avail_response
        
        from requests.exceptions import Timeout
        mock_requests.post.side_effect = Timeout("Request timed out")
        
        result = ollama_client.classify_file(
            filename="large_file.pdf",
            extension=".pdf"
        )
        
        assert result['success'] is False
        assert 'timed out' in result['error'].lower()


class TestPromptConstruction:
    """Test classification prompt construction."""
    
    def test_prompt_with_all_parameters(self, ollama_client):
        """Test prompt construction with all parameters."""
        prompt = ollama_client._construct_classification_prompt(
            filename="report.pdf",
            extension=".pdf",
            text_snippet="This is a test document",
            file_size=1024
        )
        
        assert "report.pdf" in prompt
        assert ".pdf" in prompt
        assert "This is a test document" in prompt
        assert "1024" in prompt
        assert "JSON" in prompt
    
    def test_prompt_minimal_parameters(self, ollama_client):
        """Test prompt construction with minimal parameters."""
        prompt = ollama_client._construct_classification_prompt(
            filename="test.txt",
            extension=".txt"
        )
        
        assert "test.txt" in prompt
        assert ".txt" in prompt
        assert "JSON" in prompt


class TestChatInterface:
    """Test general chat interface."""
    
    def test_chat_success(self, ollama_client, mock_requests):
        """Test successful chat interaction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'This is the AI response'
        }
        mock_requests.post.return_value = mock_response
        
        response = ollama_client.chat("Hello, how are you?")
        
        assert response == 'This is the AI response'
    
    def test_chat_with_context(self, ollama_client, mock_requests):
        """Test chat with conversation context."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Contextual response'
        }
        mock_requests.post.return_value = mock_response
        
        context = ['previous message 1', 'previous message 2']
        response = ollama_client.chat("Follow-up question", context=context)
        
        assert response == 'Contextual response'
        # Verify context was sent
        call_args = mock_requests.post.call_args
        assert 'context' in call_args[1]['json']
    
    def test_chat_error(self, ollama_client, mock_requests):
        """Test chat with connection error."""
        mock_requests.post.side_effect = Exception("Connection error")
        
        response = ollama_client.chat("Test message")
        
        assert "Error" in response


class TestModelPull:
    """Test model download functionality."""
    
    def test_pull_model_success(self, ollama_client, mock_requests):
        """Test successful model pull."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        result = ollama_client.pull_model("mistral")
        
        assert result is True
        mock_requests.post.assert_called_once()
    
    def test_pull_model_failure(self, ollama_client, mock_requests):
        """Test failed model pull."""
        mock_requests.post.side_effect = Exception("Network error")
        
        result = ollama_client.pull_model("mistral")
        
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
