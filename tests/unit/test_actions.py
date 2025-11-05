"""
Unit tests for ActionManager.

Tests file organization actions including move, rename, copy operations
and Safety Guardian integration.
"""

import pytest  # type: ignore[import-untyped]
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

# Import the action manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.actions import ActionManager
from config import Config


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock(spec=Config)
    config.get_folder_policy.return_value = {'allow_move': True}
    config.path_blacklist = []
    config.base_destination = "/tmp/test_base"  # This will be overridden in tests that need it
    config.time_estimates = {
        'move': 0.5,
        'rename': 0.3,
        'copy': 0.4
    }
    config.dry_run = False
    return config


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db = MagicMock()
    db.log_action = Mock()
    return db


@pytest.fixture
def mock_safety_guardian():
    """Create a mock Safety Guardian."""
    guardian = MagicMock()
    guardian.evaluate_operation.return_value = {
        'approved': True,
        'reasoning': 'Operation is safe',
        'warnings': [],
        'risk_level': 'low'
    }
    return guardian


@pytest.fixture
def action_manager(mock_config, mock_db_manager, mock_safety_guardian):
    """Create an ActionManager instance with mocked dependencies."""
    with patch('core.actions.SafetyGuardian', return_value=mock_safety_guardian):
        manager = ActionManager(
            config=mock_config,
            db_manager=mock_db_manager,
            dry_run=False
        )
        manager.safety_guardian = mock_safety_guardian
        return manager


class TestActionManagerInit:
    """Test ActionManager initialization."""
    
    def test_init_normal_mode(self, mock_config, mock_db_manager):
        """Test initialization in normal mode."""
        with patch('core.actions.SafetyGuardian'):
            manager = ActionManager(mock_config, mock_db_manager, dry_run=False)
            assert manager.config == mock_config
            assert manager.db_manager == mock_db_manager
            assert manager.dry_run is False
    
    def test_init_dry_run_mode(self, mock_config, mock_db_manager):
        """Test initialization in dry-run mode."""
        with patch('core.actions.SafetyGuardian'):
            manager = ActionManager(mock_config, mock_db_manager, dry_run=True)
            assert manager.dry_run is True


class TestMoveOperation:
    """Test file move operations."""
    
    def test_move_file_success(self, action_manager, temp_dir, mock_config):
        """Test successful file move operation."""
        # Set base_destination to temp_dir for this test
        mock_config.base_destination = str(temp_dir)
        
        # Create test file
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        classification = {
            'category': 'Documents',
            'suggested_path': 'Documents',  # Relative path
            'rename': None,
            'confidence': 'high'
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        assert result['success'] is True
        assert result['action'] == 'move'
        assert 'new_path' in result
        assert 'time_saved' in result
    
    def test_move_blocked_by_folder_policy(self, action_manager, temp_dir, mock_config):
        """Test move blocked by folder policy."""
        mock_config.get_folder_policy.return_value = {'allow_move': False}
        
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        classification = {
            'category': 'Documents',
            'suggested_path': str(temp_dir / "Documents"),
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=False
        )
        
        assert result['success'] is False
        assert result['action'] == 'blocked'
        assert 'folder policy' in result['message'].lower()
    
    def test_move_blocked_by_blacklist(self, action_manager, temp_dir, mock_config):
        """Test move blocked by path blacklist."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        # Add source to blacklist
        mock_config.path_blacklist = [str(temp_dir)]
        
        classification = {
            'category': 'Documents',
            'suggested_path': str(temp_dir / "Documents"),
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        assert result['success'] is False
        assert result['action'] == 'blocked'
        assert 'blacklisted' in result['message'].lower()


class TestRenameOperation:
    """Test file rename operations."""
    
    def test_rename_file_success(self, action_manager, temp_dir):
        """Test successful file rename."""
        source_file = temp_dir / "old_name.txt"
        source_file.write_text("test content")
        
        classification = {
            'category': 'Documents',
            'suggested_path': None,
            'rename': 'new_name.txt',
            'confidence': 'high'
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        assert result['success'] is True
        assert result['action'] == 'rename'
        assert 'new_name.txt' in result.get('new_path', '')


class TestSafetyGuardianIntegration:
    """Test Safety Guardian integration."""
    
    def test_safety_guardian_approves(self, action_manager, temp_dir, mock_safety_guardian, mock_config):
        """Test operation proceeds when Safety Guardian approves."""
        # Set base_destination to temp_dir for this test
        mock_config.base_destination = str(temp_dir)
        
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        mock_safety_guardian.evaluate_operation.return_value = {
            'approved': True,
            'reasoning': 'Operation is safe',
            'warnings': [],
            'risk_level': 'low'
        }
        
        classification = {
            'category': 'Documents',
            'suggested_path': 'Documents',  # Relative path
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        # Safety Guardian should be called
        mock_safety_guardian.evaluate_operation.assert_called_once()
        assert result['action'] != 'blocked_by_guardian'
    
    def test_safety_guardian_blocks(self, action_manager, temp_dir, mock_safety_guardian, mock_config):
        """Test operation blocked when Safety Guardian rejects."""
        # Set base_destination to temp_dir for this test
        mock_config.base_destination = str(temp_dir)
        
        source_file = temp_dir / "system_file.dll"
        source_file.write_text("system content")
        
        mock_safety_guardian.evaluate_operation.return_value = {
            'approved': False,
            'reasoning': 'System file protection',
            'warnings': [],
            'risk_level': 'high',
            'threats': ['system_file'],
            'requires_confirmation': True
        }
        
        classification = {
            'category': 'System',
            'suggested_path': 'System',  # Relative path
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=False
        )
        
        assert result['success'] is False
        assert result['action'] == 'blocked_by_guardian'
        assert 'Safety Guardian blocked' in result['message']
        assert 'safety_result' in result
    
    def test_safety_guardian_with_warnings(self, action_manager, temp_dir, mock_safety_guardian, mock_config):
        """Test operation proceeds with warnings."""
        # Set base_destination to temp_dir for this test
        mock_config.base_destination = str(temp_dir)
        
        source_file = temp_dir / "important.txt"
        source_file.write_text("important data")
        
        mock_safety_guardian.evaluate_operation.return_value = {
            'approved': True,
            'reasoning': 'Approved with caution',
            'warnings': ['File may be important'],
            'risk_level': 'medium'
        }
        
        classification = {
            'category': 'Documents',
            'suggested_path': 'Documents',  # Relative path
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        # Should proceed but log warnings
        assert result['action'] != 'blocked_by_guardian'


class TestPathTraversalSecurity:
    """Test path traversal security."""
    
    def test_path_traversal_blocked(self, action_manager, temp_dir):
        """Test that path traversal attempts are blocked."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        # Attempt path traversal
        classification = {
            'category': 'Documents',
            'suggested_path': '../../etc/passwd',
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        assert result['success'] is False
        assert result['action'] == 'blocked'
        assert 'security' in result['message'].lower() or 'path' in result['message'].lower()


class TestDryRunMode:
    """Test dry-run mode."""
    
    def test_dry_run_no_actual_move(self, mock_config, mock_db_manager, temp_dir):
        """Test that dry-run doesn't actually move files."""
        # Set base_destination to temp_dir for this test
        mock_config.base_destination = str(temp_dir)
        
        with patch('core.actions.SafetyGuardian') as mock_guardian_class:
            mock_guardian = MagicMock()
            mock_guardian.evaluate_operation.return_value = {
                'approved': True,
                'reasoning': 'Operation is safe',
                'warnings': [],
                'risk_level': 'low'
            }
            mock_guardian_class.return_value = mock_guardian
            
            manager = ActionManager(mock_config, mock_db_manager, dry_run=True)
            
            source_file = temp_dir / "test.txt"
            source_file.write_text("test content")
            
            classification = {
                'category': 'Documents',
                'suggested_path': 'Documents',  # Relative path
                'rename': None
            }
            
            result = manager.execute(
                file_path=str(source_file),
                classification=classification,
                user_approved=True
            )
            
            # Should indicate dry-run
            assert 'dry' in result['action'].lower() or 'dry' in result.get('message', '').lower()
            
            # Original file should still exist
            assert source_file.exists()


class TestErrorHandling:
    """Test error handling."""
    
    def test_nonexistent_file(self, action_manager):
        """Test handling of non-existent file."""
        result = action_manager.execute(
            file_path="/path/to/nonexistent/file.txt",
            classification={'suggested_path': '/some/path'},
            user_approved=True
        )
        
        assert result['success'] is False
        assert 'not found' in result['message'].lower()
    
    def test_no_action_suggested(self, action_manager, temp_dir):
        """Test handling when no action is suggested."""
        source_file = temp_dir / "test.txt"
        source_file.write_text("test content")
        
        classification = {
            'category': 'Documents',
            'suggested_path': None,
            'rename': None
        }
        
        result = action_manager.execute(
            file_path=str(source_file),
            classification=classification,
            user_approved=True
        )
        
        assert result['action'] == 'none'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
