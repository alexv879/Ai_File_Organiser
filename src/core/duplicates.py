"""
Duplicate File Finder Module

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module identifies duplicate files using content-based hashing.
It can detect exact duplicates and provide cleanup recommendations.

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict
import os
from datetime import datetime, timezone
from .safety_guardian import SafetyGuardian
from src.utils.logger import get_logger
import json
import string
import fnmatch
from src.progress import get_progress_reporter, get_parallel_processor


class DuplicateFinder:
    """
    Finds duplicate files based on content hashing.

    Attributes:
        config: Configuration object
        db_manager: Database manager for storing duplicate information
        hash_algorithm (str): Hash algorithm to use ('sha1', 'md5', 'sha256')
        min_file_size (int): Minimum file size to consider (bytes)
        file_hashes (Dict): Cache of file hash calculations
    """

    def __init__(self, config, db_manager, hash_algorithm: Optional[str] = None, min_file_size: int = 1024):
        """
        Initialize duplicate finder.

        Args:
            config: Configuration object
            db_manager: Database manager instance
            hash_algorithm (str, optional): Hash algorithm ('sha1', 'md5', 'sha256')
            min_file_size (int): Minimum file size to check in bytes (default 1KB)
        """
        self.config = config
        self.db_manager = db_manager
        self.hash_algorithm = hash_algorithm or config.hash_algorithm or 'sha1'
        self.min_file_size = min_file_size
        self.file_hashes: Dict[str, str] = {}  # path -> hash cache
        self._guardian = SafetyGuardian(config)
        self._logger = get_logger()
        self._progress = get_progress_reporter()
        self._parallel = get_parallel_processor()

    def calculate_hash(self, file_path: str, chunk_size: int = 8192) -> Optional[str]:
        """
        Calculate hash of file content.

        Args:
            file_path (str): Path to file
            chunk_size (int): Size of chunks to read (bytes)

        Returns:
            str or None: Hex digest of file hash, or None if error
        """
        # Check cache first
        if file_path in self.file_hashes:
            return self.file_hashes[file_path]

        try:
            path = Path(file_path)

            # Check file size
            file_size = path.stat().st_size
            if file_size < self.min_file_size:
                return None

            # Choose hash algorithm
            if self.hash_algorithm == 'md5':
                hasher = hashlib.md5()
            elif self.hash_algorithm == 'sha256':
                hasher = hashlib.sha256()
            else:  # default to sha1
                hasher = hashlib.sha1()

            # Read file in chunks and update hash
            with open(path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)

            file_hash = hasher.hexdigest()

            # Cache result
            self.file_hashes[file_path] = file_hash

            return file_hash

        except Exception as e:
            print(f"Error hashing {file_path}: {e}")
            return None

    def find_duplicates_in_directory(self, directory: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Find all duplicate files in a directory.

        Args:
            directory (str): Directory path to scan
            recursive (bool): If True, scan subdirectories

        Returns:
            List[Dict]: List of duplicate groups, each containing:
                - hash (str): File content hash
                - paths (List[str]): List of duplicate file paths
                - size (int): File size in bytes
                - total_wasted_space (int): Space that could be freed
        """
        dir_path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            print(f"Directory not found: {directory}")
            return []

        # Build hash -> paths mapping
        hash_map: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        # Scan directory
        if recursive:
            files = dir_path.rglob('*')
        else:
            files = dir_path.glob('*')

        print(f"Scanning for duplicates in: {directory}")
        scanned_count = 0

        for file_path in files:
            if not file_path.is_file():
                continue

            # Calculate hash
            file_hash = self.calculate_hash(str(file_path))

            if file_hash:
                file_size = file_path.stat().st_size
                hash_map[file_hash].append((str(file_path), file_size))
                scanned_count += 1

                if scanned_count % 100 == 0:
                    print(f"Scanned {scanned_count} files...")

        print(f"Scan complete: {scanned_count} files processed")

        # Filter to only duplicates (hash appears more than once)
        duplicates = []

        for file_hash, file_list in hash_map.items():
            if len(file_list) > 1:
                paths = [path for path, size in file_list]
                size = file_list[0][1]  # All duplicates have same size
                wasted_space = size * (len(file_list) - 1)  # Space occupied by duplicates

                duplicate_group = {
                    'hash': file_hash,
                    'paths': paths,
                    'size': size,
                    'total_wasted_space': wasted_space,
                    'count': len(paths)
                }

                duplicates.append(duplicate_group)

                # Store in database
                for path in paths:
                    self.db_manager.add_duplicate(file_hash, path, size)

        # Sort by wasted space (descending)
        duplicates.sort(key=lambda x: x['total_wasted_space'], reverse=True)

        return duplicates

    def find_duplicates_parallel(self, directory: str, recursive: bool = True,
                               max_workers: int = 4) -> List[Dict[str, Any]]:
        """
        Find duplicates using parallel processing with progress reporting.

        Args:
            directory (str): Directory path to scan
            recursive (bool): If True, scan subdirectories
            max_workers (int): Maximum number of parallel workers

        Returns:
            List[Dict]: List of duplicate groups
        """
        dir_path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            print(f"Directory not found: {directory}")
            return []

        # Create progress task
        task_name = f"Scanning {directory}"
        task = self._progress.create_task("duplicate_scan", task_name)

        # Collect all files first
        print(f"Collecting files in: {directory}")
        if recursive:
            all_files = list(dir_path.rglob('*'))
        else:
            all_files = list(dir_path.glob('*'))

        # Filter to files only
        file_paths = [f for f in all_files if f.is_file()]
        task.total = len(file_paths)

        print(f"Found {len(file_paths)} files, calculating hashes...")

        # Calculate hashes in parallel
        def calculate_hash_with_progress(file_path):
            result = self.calculate_hash(str(file_path))
            self._progress.update_task("duplicate_scan", 1)
            return (str(file_path), result)

        # Process files in parallel
        hash_results = self._parallel.map_with_progress(
            lambda fp: (fp, self.calculate_hash(fp)),
            [str(fp) for fp in file_paths],
            "Hashing files"
        )

        # Build hash map
        hash_map: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for file_path_str, file_hash in hash_results:
            if file_hash:
                try:
                    file_size = Path(file_path_str).stat().st_size
                    hash_map[file_hash].append((file_path_str, file_size))
                except OSError:
                    continue

        self._progress.complete_task("duplicate_scan")

        # Filter to duplicates
        duplicates = []
        for file_hash, file_list in hash_map.items():
            if len(file_list) > 1:
                paths = [path for path, size in file_list]
                size = file_list[0][1]
                wasted_space = size * (len(file_list) - 1)

                duplicate_group = {
                    'hash': file_hash,
                    'paths': paths,
                    'size': size,
                    'total_wasted_space': wasted_space,
                    'count': len(paths)
                }

                duplicates.append(duplicate_group)
                for path in paths:
                    self.db_manager.add_duplicate(file_hash, path, size)

        # Sort by wasted space
        duplicates.sort(key=lambda x: x['total_wasted_space'], reverse=True)

        return duplicates

    def find_duplicates_in_multiple_directories(self, directories: List[str]) -> List[Dict[str, Any]]:
        """
        Find duplicates across multiple directories.

        Args:
            directories (List[str]): List of directory paths

        Returns:
            List[Dict]: Duplicate groups
        """
        all_duplicates = []

        for directory in directories:
            duplicates = self.find_duplicates_in_directory(directory)
            all_duplicates.extend(duplicates)

        return all_duplicates

    def get_duplicate_summary(self, duplicates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for duplicates.

        Args:
            duplicates (List[Dict]): List of duplicate groups

        Returns:
            Dict: Summary statistics
        """
        total_files = sum(group['count'] for group in duplicates)
        total_duplicate_files = sum(group['count'] - 1 for group in duplicates)
        total_wasted_space = sum(group['total_wasted_space'] for group in duplicates)

        return {
            'total_duplicate_groups': len(duplicates),
            'total_duplicate_files': total_duplicate_files,
            'total_files_including_originals': total_files,
            'total_wasted_space_bytes': total_wasted_space,
            'total_wasted_space_mb': round(total_wasted_space / (1024 * 1024), 2),
            'total_wasted_space_gb': round(total_wasted_space / (1024 * 1024 * 1024), 2)
        }

    def suggest_duplicates_to_keep(self, duplicate_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest which file to keep and which to delete from duplicate group.

        Strategy:
        1. Keep file with shortest path (likely more organized)
        2. Keep file with most descriptive name
        3. Keep oldest file (likely the original)

        Args:
            duplicate_group (Dict): Single duplicate group

        Returns:
            Dict: Suggestions with keys:
                - keep (str): Path to keep
                - delete (List[str]): Paths to delete
                - reason (str): Explanation
        """
        paths = duplicate_group['paths']

        if len(paths) < 2:
            return {
                'keep': paths[0] if paths else None,
                'delete': [],
                'reason': 'No duplicates to remove'
            }

        # Strategy 1: Prefer shorter paths (better organized)
        sorted_by_length = sorted(paths, key=lambda p: len(p))

        # Strategy 2: Prefer paths with meaningful names (not temp/download folders)
        temp_keywords = ['temp', 'tmp', 'download', 'cache', 'trash']

        def is_temp_location(path: str) -> bool:
            path_lower = path.lower()
            return any(keyword in path_lower for keyword in temp_keywords)

        non_temp_paths = [p for p in paths if not is_temp_location(p)]

        if non_temp_paths:
            # Keep the first non-temp path with shortest length
            keep_path = sorted(non_temp_paths, key=lambda p: len(p))[0]
            reason = "Keeping file in more permanent location"
        else:
            # All are in temp locations, just keep shortest path
            keep_path = sorted_by_length[0]
            reason = "Keeping file with shortest path"

        delete_paths = [p for p in paths if p != keep_path]

        return {
            'keep': keep_path,
            'delete': delete_paths,
            'reason': reason
        }

    def find_temp_and_junk_files(self, directory: str) -> List[str]:
        """
        Find temporary and junk files that can be safely deleted.

        Args:
            directory (str): Directory to scan

        Returns:
            List[str]: List of temp/junk file paths
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            return []

        junk_patterns = [
            '*.tmp', '*.temp', '*.cache',
            '*.crdownload', '*.part', '*.partial',
            '*.download', '.DS_Store', 'Thumbs.db',
            'desktop.ini', '*.bak', '*~'
        ]

        junk_files = []

        for pattern in junk_patterns:
            junk_files.extend([str(p) for p in dir_path.rglob(pattern)])

        return junk_files

    def cleanup_duplicates(self, duplicate_group: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up duplicate files (delete all but one).

        Args:
            duplicate_group (Dict): Duplicate group to clean
            dry_run (bool): If True, don't actually delete files

        Returns:
            Dict: Cleanup result
        """
        suggestion = self.suggest_duplicates_to_keep(duplicate_group)

        deleted_count = 0
        errors = []

        for file_path in suggestion['delete']:
            try:
                # Safety check: do not delete application/game files
                is_safe, reason = self._guardian.is_file_safe_to_modify(Path(file_path))
                if not is_safe:
                    self._logger.safety_block(file_path, f"Duplicate cleanup skip: {reason}", check_type='application_protection')
                    continue

                if dry_run:
                    # Log dry run deletion intent
                    try:
                        self._logger.log_operation('DELETE', file_path, file_path, 'DELETED', 'DRY_RUN')
                    except Exception:
                        pass
                else:
                    # Perform deletion to Recycle Bin in future (send2trash); unlink for now
                    Path(file_path).unlink()
                    self.db_manager.remove_duplicate_entry(file_path)
                    try:
                        self._logger.log_operation('DELETE', file_path, file_path, 'DELETED', 'SUCCESS')
                    except Exception:
                        pass

                deleted_count += 1
            except Exception as e:
                errors.append(f"Error deleting {file_path}: {e}")

        return {
            'success': len(errors) == 0,
            'kept': suggestion['keep'],
            'deleted_count': deleted_count,
            'errors': errors,
            'dry_run': dry_run,
            'space_freed': duplicate_group['size'] * deleted_count
        }

    def cleanup_duplicates_parallel(self, duplicates: List[Dict[str, Any]],
                                  dry_run: bool = True, strategy: str = "newest") -> Dict[str, Any]:
        """
        Clean up duplicates in parallel with progress reporting.

        Args:
            duplicates: List of duplicate groups
            dry_run: If True, don't actually delete files
            strategy: Cleanup strategy ('newest', 'oldest', 'largest', 'smallest')

        Returns:
            Dict with cleanup results
        """
        if not duplicates:
            return {'total_groups': 0, 'files_deleted': 0, 'space_freed': 0}

        # Create progress task
        task_name = f"Cleaning {len(duplicates)} duplicate groups"
        task = self._progress.create_task("cleanup_duplicates", task_name, len(duplicates))

        def cleanup_group(group):
            try:
                if strategy == "newest":
                    suggestion = self.compare_by_date(group)
                elif strategy == "oldest":
                    suggestion = self.compare_by_date(group)
                    # For oldest, we want to keep the oldest file instead
                    paths = group['paths']
                    file_times = {}
                    for path in paths:
                        try:
                            mtime = Path(path).stat().st_mtime
                            file_times[path] = datetime.fromtimestamp(mtime)
                        except Exception:
                            file_times[path] = datetime.min

                    oldest_path = min(file_times.keys(), key=lambda p: file_times[p])
                    suggestion = {
                        'keep': oldest_path,
                        'delete': [p for p in paths if p != oldest_path],
                        'reason': f'Keeping oldest file: {oldest_path}'
                    }
                else:
                    suggestion = self.suggest_duplicates_to_keep(group)

                deleted_count = 0
                space_freed = 0

                for file_path in suggestion['delete']:
                    is_safe, reason = self._guardian.is_file_safe_to_modify(Path(file_path))
                    if not is_safe:
                        self._logger.safety_block(file_path, f"Duplicate cleanup skip: {reason}", check_type='application_protection')
                        continue

                    if dry_run:
                        self._logger.log_operation('DELETE', file_path, file_path, 'DELETED', 'DRY_RUN')
                    else:
                        Path(file_path).unlink()
                        self.db_manager.remove_duplicate_entry(file_path)
                        self._logger.log_operation('DELETE', file_path, file_path, 'DELETED', 'SUCCESS')

                    deleted_count += 1
                    space_freed += group['size']

                return {
                    'kept': suggestion['keep'],
                    'deleted_count': deleted_count,
                    'space_freed': space_freed,
                    'errors': []
                }
            except Exception as e:
                return {
                    'kept': None,
                    'deleted_count': 0,
                    'space_freed': 0,
                    'errors': [str(e)]
                }

        # Process groups in parallel
        results = self._parallel.map_with_progress(
            cleanup_group,
            duplicates,
            "Cleaning duplicate groups"
        )

        # Aggregate results
        total_deleted = 0
        total_space_freed = 0
        all_errors = []

        for result in results:
            total_deleted += result['deleted_count']
            total_space_freed += result['space_freed']
            all_errors.extend(result['errors'])
            self._progress.update_task("cleanup_duplicates", 1)

        self._progress.complete_task("cleanup_duplicates")

        return {
            'total_groups': len(duplicates),
            'files_deleted': total_deleted,
            'space_freed': total_space_freed,
            'errors': all_errors,
            'dry_run': dry_run,
            'strategy': strategy
        }

    def filter_protected_duplicates(self, duplicates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Filter out duplicate groups that contain protected application/game files.

        Returns:
            (safe_duplicates, protected_groups_count, protected_files_count)
        """
        safe_groups: List[Dict[str, Any]] = []
        protected_groups = 0
        protected_files = 0

        for group in duplicates:
            paths: List[str] = group.get('paths', [])
            group_protected = False

            for p in paths:
                is_safe, reason = self._guardian.is_file_safe_to_modify(Path(p))
                if not is_safe:
                    group_protected = True
                    protected_files += 1
                    # No need to check all once one is protected per group policy
                    break

            if group_protected:
                protected_groups += 1
                # Skip entire group to avoid presenting for deletion
                continue
            safe_groups.append(group)

        return safe_groups, protected_groups, protected_files

    def compare_by_date(self, duplicate_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced comparison that keeps the NEWEST file by modification date.

        Args:
            duplicate_group: Dict with 'paths' list of duplicate file paths

        Returns:
            Dict with 'keep' (newest file) and 'delete' (older files)
        """
        paths = duplicate_group['paths']

        if len(paths) < 2:
            return {
                'keep': paths[0] if paths else None,
                'delete': [],
                'reason': 'No duplicates'
            }

        # Get modification times for each file
        file_times = {}
        for path in paths:
            try:
                mtime = Path(path).stat().st_mtime
                file_times[path] = datetime.fromtimestamp(mtime)
            except Exception as e:
                print(f"Error getting time for {path}: {e}")
                file_times[path] = datetime.min

        # Find newest file
        newest_path = max(file_times.keys(), key=lambda p: file_times[p])
        oldest_path = min(file_times.keys(), key=lambda p: file_times[p])

        newer_time = file_times[newest_path].strftime("%Y-%m-%d %H:%M:%S")
        older_time = file_times[oldest_path].strftime("%Y-%m-%d %H:%M:%S")

        delete_paths = [p for p in paths if p != newest_path]

        return {
            'keep': newest_path,
            'keep_date': newer_time,
            'delete': delete_paths,
            'oldest_date': older_time,
            'reason': f'Keeping newest version (modified {newer_time}), deleting older ({older_time})'
        }

    def get_drive_letter(self, path: str) -> str:
        """Get drive letter from path (e.g., 'C' from 'C:\\...')"""
        try:
            return Path(path).drive.split(':')[0]
        except:
            return '?'

    @staticmethod
    def enumerate_available_drives() -> List[str]:
        """
        Return a list of available drive roots like ['C:\\', 'D:\\'] by checking A-Z.
        """
        drives = []
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            if os.path.exists(root):
                drives.append(root)
        return drives

    @staticmethod
    def is_path_excluded(path: str, exclude_patterns: List[str]) -> bool:
        p = path.replace('\\', '/').lower()
        for pat in exclude_patterns:
            pat_norm = pat.replace('\\', '/').lower()
            # simple startswith or glob match
            if p.startswith(pat_norm) or fnmatch.fnmatch(p, pat_norm):
                return True
        return False

    def detect_candidate_directories(self, drives: List[str], sample_depth: int = 1, min_files: int = 20, top_n: int = 30, exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """
        Heuristically discover candidate directories to scan for duplicates.

        Strategy:
        - For each drive, look at immediate children (depth=1) and a few well-known locations.
        - For each candidate, compute a shallow sample: count files and sum sizes (limited traversal).
        - Exclude system/protected paths via exclude_patterns.
        - Return top_n directories ranked by file count and total size.
        """
        if exclude_patterns is None:
            exclude_patterns = [
                'c:/windows', 'c:/program files', 'c:/program files (x86)', 'c:/programdata',
                '*/system volume information/*', '*/$recycle.bin/*', '*/windowsapps/*'
            ]

        candidates = {}

        for drive in drives:
            drive = drive if drive.endswith('\\') else drive + '\\'
            # always consider drive root
            roots = [drive]

            # Add common child folders under drive root
            try:
                with os.scandir(drive) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            roots.append(os.path.join(drive, entry.name))
            except Exception:
                # permission errors or other issues; skip scanning drive root
                pass

            # Add some well-known user folders if present
            username = os.getenv('USERNAME') or os.getenv('USER') or ''
            if username:
                user_common = [
                    os.path.join(drive, 'Users', username, 'Desktop'),
                    os.path.join(drive, 'Users', username, 'Downloads'),
                    os.path.join(drive, 'Users', username, 'Documents'),
                    os.path.join(drive, 'Users', username, 'Pictures'),
                ]
                roots.extend(user_common)

            # Evaluate each root candidate with a shallow scan
            for root in roots:
                if not root:
                    continue
                try:
                    root_norm = os.path.normpath(root)
                except Exception:
                    continue

                if self.is_path_excluded(root_norm, exclude_patterns):
                    # skip excluded
                    continue

                # perform shallow walk limited by sample_depth and early-stop on file count
                file_count = 0
                total_size = 0
                try:
                    for dirpath, dirnames, filenames in os.walk(root_norm):
                        # compute relative depth
                        rel = os.path.relpath(dirpath, root_norm)
                        depth = 0 if rel == '.' else rel.count(os.sep) + 1
                        if depth > sample_depth:
                            # don't descend further
                            dirnames[:] = []
                            continue

                        for fname in filenames:
                            fpath = os.path.join(dirpath, fname)
                            try:
                                st = os.stat(fpath)
                                file_count += 1
                                total_size += st.st_size
                            except Exception:
                                continue

                        # early stop if sample gets large
                        if file_count >= 2000:
                            break
                except Exception:
                    # permissions, non-dir, etc.
                    continue

                # only keep candidates with some files
                if file_count >= 1:
                    candidates[root_norm] = (file_count, total_size)

        # rank candidates by file_count then total_size
        ranked = sorted(candidates.items(), key=lambda kv: (kv[1][0], kv[1][1]), reverse=True)
        selected = [k for k, v in ranked[:top_n]]
        return selected

    def generate_structure_report(self, directories: List[str], out_path: str = 'cross_drive_structure.json', sample_limit: int = 200) -> Dict[str, Any]:
        """
        Walk candidate directories shallowly and write a structure report (json) with counts and sizes.
        Returns the report dict.
        """
        report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'directories': []}

        for d in directories:
            entry = {'path': d, 'file_count': 0, 'total_size': 0, 'sample_files': []}
            try:
                for dirpath, dirnames, filenames in os.walk(d):
                    for fname in filenames:
                        fpath = os.path.join(dirpath, fname)
                        try:
                            st = os.stat(fpath)
                            entry['file_count'] += 1
                            entry['total_size'] += st.st_size
                            if len(entry['sample_files']) < sample_limit:
                                entry['sample_files'].append({'path': fpath, 'size': st.st_size, 'mtime': st.st_mtime})
                        except Exception:
                            continue
                    # limit depth to keep report generation quick
                    # only scan first level under candidate for the report
                    break
            except Exception:
                entry['error'] = 'permission or io error'

            report['directories'].append(entry)

        # write JSON
        try:
            with open(out_path, 'w', encoding='utf-8') as fh:
                json.dump(report, fh, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to write structure report: {e}")

        return report

    @staticmethod
    def human_size(bytes_size: float) -> str:
        """Format bytes into human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"

    def find_duplicates_cross_drive(self, drives: Optional[List[str]] = None, top_n: int = 40, dry_run: bool = True) -> Dict[str, Any]:
        """
        Find duplicates across multiple drives with intelligent candidate selection.

        Args:
            drives: List of drives to scan (auto-detects if None)
            top_n: Number of top candidate directories to scan
            dry_run: If True, preview only

        Returns:
            Dict with results and summary
        """
        if drives is None:
            drives = self.enumerate_available_drives()

        print(f"Detected drives: {drives}")

        # Detect candidate directories
        print('Detecting candidate directories (shallow sampling)...')
        exclude_patterns = [
            'C:/Windows', 'C:/Program Files', 'C:/Program Files (x86)', 'C:/ProgramData',
            '*/System Volume Information/*', '*/$Recycle.Bin/*', '*/WindowsApps/*'
        ]
        directories = self.detect_candidate_directories(drives, sample_depth=1, top_n=top_n, exclude_patterns=exclude_patterns)

        print(f"Will scan {len(directories)} directories (top candidates)")

        # Generate structure report
        struct_report = self.generate_structure_report(directories, out_path='cross_drive_structure.json')
        total_files = sum(d.get('file_count', 0) for d in struct_report.get('directories', []))
        total_bytes = sum(d.get('total_size', 0) for d in struct_report.get('directories', []))
        print(f"Structure report written to cross_drive_structure.json")
        print(f"Candidate directories: {len(struct_report.get('directories', []))}")
        print(f"Total files (sampled): {total_files}, Total size (sampled): {self.human_size(total_bytes)}")

        # Find duplicates across all candidate directories
        duplicates = self.find_duplicates_in_multiple_directories(directories)

        if not duplicates:
            return {'duplicates': [], 'summary': {'message': 'No duplicates found'}}

        # Apply date-based cleanup strategy
        results = []
        total_waste = 0
        total_deletable = 0

        for dup_group in duplicates:
            suggestion = self.compare_by_date(dup_group)
            space_mb = dup_group['size'] * (len(suggestion['delete'])) / (1024 * 1024)
            total_deletable += len(suggestion['delete'])
            total_waste += dup_group['size'] * len(suggestion['delete']) / (1024 * 1024)

            results.append({
                'keep': suggestion['keep'],
                'delete': suggestion['delete'],
                'space_freed_mb': space_mb,
                'reason': suggestion['reason']
            })

        summary = {
            'total_duplicate_groups': len(duplicates),
            'files_that_can_be_deleted': total_deletable,
            'total_space_to_free_mb': total_waste,
            'total_space_to_free_gb': total_waste / 1024,
            'dry_run': dry_run,
            'drives_scanned': drives,
            'directories_scanned': len(directories)
        }

        return {
            'duplicates': duplicates,
            'results': results,
            'summary': summary
        }


def find_duplicates(directory: str, config, db_manager) -> List[Dict[str, Any]]:
    """
    Convenience function to find duplicates in a directory.

    Args:
        directory (str): Directory to scan
        config: Configuration object
        db_manager: Database manager

    Returns:
        List[Dict]: Duplicate groups
    """
    finder = DuplicateFinder(config, db_manager)
    return finder.find_duplicates_in_directory(directory)


if __name__ == "__main__":
    # Test duplicate finder
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from src.config import get_config
    from core.db_manager import DatabaseManager

    config = get_config()
    db = DatabaseManager()

    finder = DuplicateFinder(config, db)

    # Test with current directory
    test_dir = Path.home() / "Downloads"

    if test_dir.exists():
        print(f"Scanning for duplicates in: {test_dir}")
        duplicates = finder.find_duplicates_in_directory(str(test_dir), recursive=False)

        if duplicates:
            print(f"\nFound {len(duplicates)} duplicate groups:")

            summary = finder.get_duplicate_summary(duplicates)
            print(f"\nSummary:")
            print(f"  Total duplicate files: {summary['total_duplicate_files']}")
            print(f"  Wasted space: {summary['total_wasted_space_mb']} MB")

            # Show first few duplicates
            for i, group in enumerate(duplicates[:3]):
                print(f"\nGroup {i+1}:")
                print(f"  Size: {group['size']} bytes")
                print(f"  Count: {group['count']} files")
                for path in group['paths']:
                    print(f"    - {path}")
        else:
            print("No duplicates found!")
    else:
        print(f"Test directory not found: {test_dir}")
