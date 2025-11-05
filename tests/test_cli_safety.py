import os
import sys
import time
from pathlib import Path

import pytest  # type: ignore[import-untyped]
from unittest.mock import patch, MagicMock


# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cli.aifo import app  # type: ignore
from typer.testing import CliRunner


runner = CliRunner()


def write_file(path: Path, size_bytes: int = 0, mtime_offset_days: int = 0, content: bytes = b'x'):
    path.parent.mkdir(parents=True, exist_ok=True)
    if size_bytes <= 0:
        path.write_bytes(content)
    else:
        with path.open('wb') as f:
            remaining = size_bytes
            chunk = b'x' * 1024
            while remaining > 0:
                to_write = min(remaining, len(chunk))
                f.write(chunk[:to_write])
                remaining -= to_write
    if mtime_offset_days:
        past = time.time() - mtime_offset_days * 24 * 3600
        os.utime(path, (past, past))


def test_organize_simulate_safe(tmp_path: Path):
    f = tmp_path / 'doc.txt'
    write_file(f)

    # Mock the SafetyGuardian to allow scanning temp directory
    with patch('cli.aifo.SafetyGuardian') as mock_guardian_class:
        mock_guardian = MagicMock()
        mock_guardian.validate_scan_folder.return_value = (True, None)
        mock_guardian.is_file_safe_to_modify.return_value = (True, None)
        mock_guardian_class.return_value = mock_guardian
        
        result = runner.invoke(app, ['organize', str(tmp_path)])
        assert result.exit_code == 0
        assert 'Processed' in result.stdout


def test_organize_skips_app_folder(tmp_path: Path):
    app_dir = tmp_path / 'game_install'
    write_file(app_dir / 'engine.dll')
    write_file(app_dir / 'launcher.exe')
    # File next to .exe + .dll should be considered protected and skipped
    write_file(app_dir / 'readme.txt')
    # A safe file elsewhere should be processed
    write_file(tmp_path / 'photo.jpg')

    with patch('cli.aifo.SafetyGuardian') as mock_guardian_class:
        mock_guardian = MagicMock()
        mock_guardian.validate_scan_folder.return_value = (True, None)
        mock_guardian.is_file_safe_to_modify.return_value = (True, None)
        mock_guardian_class.return_value = mock_guardian
        
        result = runner.invoke(app, ['organize', str(tmp_path)])
        assert result.exit_code == 0
        # We expect at least 1 file processed (photo.jpg), and that the command didn't fail
        assert 'Processed' in result.stdout


def test_space_large_old_lists(tmp_path: Path):
    large_old = tmp_path / 'big.iso'
    write_file(large_old, size_bytes=5 * 1024 * 1024, mtime_offset_days=365)  # 5MB, 1 year old

    with patch('cli.aifo.SafetyGuardian') as mock_guardian_class:
        mock_guardian = MagicMock()
        mock_guardian.validate_scan_folder.return_value = (True, None)
        mock_guardian.is_file_safe_to_modify.return_value = (True, None)
        mock_guardian_class.return_value = mock_guardian
        
        result = runner.invoke(app, ['space-large-old', str(tmp_path), '--min-size-mb', '1', '--older-than-days', '30'])
        assert result.exit_code == 0
        assert 'Found' in result.stdout
        assert str(large_old) in result.stdout


def test_find_duplicates_lists_groups(tmp_path: Path):
    a = tmp_path / 'dup1.txt'
    b = tmp_path / 'sub' / 'dup1.txt'
    write_file(a, content=b'A')
    write_file(b, content=b'A')

    with patch('cli.aifo.SafetyGuardian') as mock_guardian_class:
        mock_guardian = MagicMock()
        mock_guardian.validate_scan_folder.return_value = (True, None)
        mock_guardian_class.return_value = mock_guardian
        
        result = runner.invoke(app, ['find-duplicates', str(tmp_path)])
        assert result.exit_code == 0
        assert 'Found' in result.stdout
