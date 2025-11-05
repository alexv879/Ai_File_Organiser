import os
from pathlib import Path

from src.config import get_config
from src.core.safety_guardian import SafetyGuardian
from src.core.duplicates import DuplicateFinder
from src.core.db_manager import DatabaseManager


def test_is_application_folder_detects_exe_and_dll(tmp_path: Path):
    # Arrange: create folder with exe and dll
    app_dir = tmp_path / "TestGame"
    app_dir.mkdir()
    (app_dir / "game.exe").write_bytes(b"\x00")
    (app_dir / "engine.dll").write_bytes(b"\x00")

    guardian = SafetyGuardian(get_config())

    # Act
    is_app = guardian.is_application_folder(app_dir)
    safe, reason = guardian.is_file_safe_to_modify(app_dir / "game.exe")

    # Assert
    assert is_app is True
    assert safe is False
    assert "application" in reason.lower() or "protected" in reason.lower()


def test_duplicate_filter_skips_protected_group(tmp_path: Path):
    # Arrange: make two identical files, one inside a folder with exe+dll
    user_dir = tmp_path / "UserFolder"
    app_dir = tmp_path / "GameFolder"
    user_dir.mkdir()
    app_dir.mkdir()

    # app indicators
    (app_dir / "run.exe").write_bytes(b"\x00")
    (app_dir / "lib.dll").write_bytes(b"\x00")

    f1 = user_dir / "photo.jpg"
    f2 = app_dir / "photo.jpg"
    content = b"same-content"
    f1.write_bytes(content)
    f2.write_bytes(content)

    cfg = get_config()
    db = DatabaseManager()
    finder = DuplicateFinder(cfg, db, hash_algorithm='sha1', min_file_size=1)

    # Build a duplicate group manually in expected shape
    duplicates = [{
        'hash': 'dummy',
        'paths': [str(f1), str(f2)],
        'size': len(content),
        'total_wasted_space': len(content),
        'count': 2
    }]

    # Act
    safe, protected_groups, protected_files = finder.filter_protected_duplicates(duplicates)

    # Assert: the group should be skipped entirely
    assert protected_groups == 1
    assert len(safe) == 0


def test_is_protected_path_by_known_patterns(tmp_path: Path):
    # Simulate a path that contains a known app folder name
    suspicious_dir = tmp_path / "SteamLibrary" / "SomeGame"
    suspicious_dir.mkdir(parents=True)
    (suspicious_dir / "file.pak").write_bytes(b"\x00")
    guardian = SafetyGuardian(get_config())

    assert guardian.is_protected_path(suspicious_dir) is True
