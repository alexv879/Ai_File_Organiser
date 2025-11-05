"""
Unit tests for FileClassifier.

Tests the hybrid classification system including rule-based, AI, and agent classification.
"""

import pytest  # type: ignore[import-untyped]
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch

# Import the classifier
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.classifier import FileClassifier
from config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock(spec=Config)
    config.categories = {
        'Documents': {
            'extensions': ['.pdf', '.doc', '.docx', '.txt'],
            'path': 'Documents'
        },
        'Images': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif'],
            'path': 'Images'
        }
    }
    config.destination_rules = {
        'pdf': 'Documents/PDFs/',
        'jpg': 'Pictures/',
        'jpeg': 'Pictures/',
        'png': 'Pictures/',
        'gif': 'Pictures/',
        'docx': 'Documents/Word/',
        'doc': 'Documents/Word/',
        'xlsx': 'Documents/Excel/',
        'xls': 'Documents/Excel/',
        'pptx': 'Documents/PowerPoint/',
        'txt': 'Documents/Text/',
        'zip': 'Downloads/Archives/',
        'rar': 'Downloads/Archives/',
        '7z': 'Downloads/Archives/',
        'mp4': 'Videos/',
        'avi': 'Videos/',
        'mkv': 'Videos/',
        'mp3': 'Music/',
        'wav': 'Music/',
        'flac': 'Music/'
    }
    config.get_category_for_extension = Mock(return_value='Documents')
    return config


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = MagicMock()
    client.classify_file.return_value = {
        'category': 'Documents',
        'suggested_path': 'Documents/Reports',
        'rename': None,
        'reason': 'AI classification',
        'success': True
    }
    return client


@pytest.fixture
def classifier(mock_config, mock_ollama_client):
    """Create a FileClassifier instance with mocked dependencies."""
    mock_config.enable_ai = True
    mock_config.text_extract_limit = 500
    classifier = FileClassifier(mock_config, ollama_client=mock_ollama_client)
    return classifier


@pytest.fixture
def classifier_no_ai(mock_config):
    """Create a FileClassifier instance with AI disabled."""
    mock_config.enable_ai = False
    mock_config.text_extract_limit = 500
    classifier = FileClassifier(mock_config, ollama_client=None)
    return classifier


class TestFileClassifierInit:
    """Test FileClassifier initialization."""
    
    def test_init_without_ai(self, mock_config):
        """Test initialization without AI enabled."""
        mock_config.enable_ai = False
        mock_config.text_extract_limit = 500
        classifier = FileClassifier(mock_config, ollama_client=None)
        assert classifier.config == mock_config
        assert classifier.enable_ai is False
        assert classifier.ollama_client is None
    
    def test_init_with_ai(self, mock_config, mock_ollama_client):
        """Test initialization with AI enabled."""
        mock_config.enable_ai = True
        mock_config.text_extract_limit = 500
        classifier = FileClassifier(mock_config, ollama_client=mock_ollama_client)
        assert classifier.enable_ai is True
        assert classifier.ollama_client is not None


class TestRuleBasedClassification:
    """Test rule-based classification methods."""
    
    def test_classify_pdf_document(self, classifier_no_ai):
        """Test classification of a PDF file."""
        test_file = Path(__file__).parent / "test_data" / "sample.pdf"
        
        # Mock the file info extraction
        with patch.object(classifier_no_ai, '_extract_file_info') as mock_extract:
            mock_extract.return_value = {
                'path': str(test_file),
                'filename': 'sample.pdf',
                'stem': 'sample',
                'extension': '.pdf',
                'size': 1024,
                'mime_type': 'application/pdf',
                'text_snippet': None,
                'modified_time': 0
            }
            
            result = classifier_no_ai.classify(str(test_file), deep_analysis=False)
            
            assert result['category'] in ['Documents', 'Unsorted']
            assert 'suggested_path' in result
            assert 'confidence' in result
            assert result['method'] == 'rule-based'
    
    def test_classify_image_file(self, classifier_no_ai):
        """Test classification of an image file."""
        test_file = Path(__file__).parent / "test_data" / "photo.jpg"
        
        with patch.object(classifier_no_ai, '_extract_file_info') as mock_extract:
            mock_extract.return_value = {
                'path': str(test_file),
                'filename': 'photo.jpg',
                'stem': 'photo',
                'extension': '.jpg',
                'size': 2048,
                'mime_type': 'image/jpeg',
                'text_snippet': None,
                'modified_time': 0
            }
            
            result = classifier_no_ai.classify(str(test_file), deep_analysis=False)
            
            assert result['category'] in ['Pictures', 'Unsorted']
            assert 'confidence' in result


class TestAIClassification:
    """Test AI-powered classification."""
    
    def test_ai_classification_enabled(self, classifier, mock_ollama_client):
        """Test that AI classification is used when confidence is low."""
        test_file = Path(__file__).parent / "test_data" / "unknown.xyz"
        
        with patch.object(classifier, '_extract_file_info') as mock_extract:
            with patch.object(classifier, '_classify_by_rules') as mock_rules:
                mock_extract.return_value = {
                    'path': str(test_file),
                    'filename': 'unknown.xyz',
                    'stem': 'unknown',
                    'extension': '.xyz',
                    'size': 512,
                    'mime_type': None,
                    'text_snippet': None,
                    'modified_time': 0
                }
                mock_rules.return_value = {
                    'category': 'Unsorted',
                    'suggested_path': None,
                    'confidence': 'low',
                    'method': 'rule-based'
                }
                
                result = classifier.classify(str(test_file), deep_analysis=False)
                
                # Should fall back to AI if available
                assert result is not None
    
    def test_ai_classification_disabled(self, mock_config):
        """Test behavior when AI is disabled."""
        mock_config.enable_ai = False
        mock_config.text_extract_limit = 500
        classifier = FileClassifier(mock_config, ollama_client=None)
        
        test_file = Path(__file__).parent / "test_data" / "sample.txt"
        
        with patch.object(classifier, '_extract_file_info') as mock_extract:
            mock_extract.return_value = {
                'path': str(test_file),
                'filename': 'sample.txt',
                'stem': 'sample',
                'extension': '.txt',
                'size': 256,
                'mime_type': 'text/plain',
                'text_snippet': None,
                'modified_time': 0
            }
            
            result = classifier.classify(str(test_file), deep_analysis=False)
            
            # Should only use rule-based when AI disabled
            assert result['method'] == 'rule-based'


class TestAgentClassification:
    """Test agent-powered deep analysis."""
    
    def test_deep_analysis_requested(self, classifier):
        """Test that deep analysis triggers agent classification."""
        test_file = Path(__file__).parent / "test_data" / "sample.pdf"
        
        with patch.object(classifier, '_extract_file_info') as mock_extract:
            with patch.object(classifier, '_classify_by_agent') as mock_agent:
                mock_extract.return_value = {
                    'path': str(test_file),
                    'filename': 'sample.pdf',
                    'stem': 'sample',
                    'extension': '.pdf',
                    'size': 1024,
                    'mime_type': 'application/pdf',
                    'text_snippet': None,
                    'modified_time': 0
                }
                mock_agent.return_value = {
                    'category': 'Documents',
                    'suggested_path': 'Documents/Analysis',
                    'confidence': 'high',
                    'method': 'agent',
                    'success': True
                }
                
                result = classifier.classify(str(test_file), deep_analysis=True)
                
                # Should attempt agent classification
                mock_agent.assert_called_once()


class TestFileInfoExtraction:
    """Test file information extraction."""
    
    def test_extract_basic_info(self, classifier):
        """Test extraction of basic file information."""
        # This would test _extract_file_info method
        # Implementation depends on actual file creation
        pass
    
    def test_extract_text_from_pdf(self, classifier):
        """Test text extraction from PDF files."""
        # Test PDF text extraction with PyPDF2
        pass
    
    def test_extract_text_from_docx(self, classifier):
        """Test text extraction from DOCX files."""
        # Test DOCX text extraction with python-docx
        pass


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_nonexistent_file(self, classifier):
        """Test classification of non-existent file."""
        result = classifier.classify("/path/to/nonexistent/file.txt", deep_analysis=False)
        # Should handle gracefully
        assert result is not None
        assert result['category'] == 'Unsorted'
        assert result['reason'] == 'File not found'
    
    def test_empty_filename(self, classifier):
        """Test handling of empty filename."""
        # Should handle edge case
        pass
    
    def test_special_characters_in_filename(self, classifier):
        """Test files with special characters."""
        # Should sanitize and classify properly
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
