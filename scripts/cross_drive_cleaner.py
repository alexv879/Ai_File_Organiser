#!/usr/bin/env python3
"""
Cross-Drive Duplicate Manager - Smart Cleanup Tool

This tool finds duplicates across different drives (C:, D:, etc.)
and intelligently removes old versions, keeping the newest.
"""

import sys
sys.path.insert(0, r'd:\AIFILEORGANISER\src')

from pathlib import Path
from datetime import datetime, timezone
from ai.ollama_client import OllamaClient
from core.duplicates import DuplicateFinder
from core.db_manager import DatabaseManager
from config import get_config
from typing import Dict, List, Optional
import json
import argparse
import os
import string
import fnmatch
from collections import defaultdict

class CrossDriveDuplicateManager:
    """
    Manages duplicate files across multiple drives intelligently.
    Keeps newest version, deletes older versions.
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = DatabaseManager()
        self.duplicate_finder = DuplicateFinder(self.config, self.db)
    
    def compare_by_date(self, duplicate_group: Dict) -> Dict:
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
    
    def clean_cross_drive_duplicates(self, directories: List[str], dry_run: bool = True):
        """
        Find and clean duplicates across multiple drives.
        
        Args:
            directories: List of directories to scan (e.g., ['C:\\Users\\...', 'D:\\...'])
            dry_run: If True, preview only. If False, actually delete.
        """
        print("\n" + "="*70)
        print("CROSS-DRIVE DUPLICATE CLEANER")
        print("="*70)
        print(f"Scanning directories: {directories}")
        print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'ACTUAL CLEANUP'}")
        print("="*70 + "\n")
        
        # Find all duplicates
        duplicates = self.duplicate_finder.find_duplicates_in_multiple_directories(directories)
        
        if not duplicates:
            print("[OK] No duplicates found!")
            return
        
        total_waste = 0
        total_deletable = 0
        results = []
        
        print(f"Found {len(duplicates)} duplicate groups\n")
        print("-" * 70)
        
        for i, dup_group in enumerate(duplicates, 1):
            # Use date-based comparison
            suggestion = self.compare_by_date(dup_group)
            
            # Get drive letters
            keep_drive = self.get_drive_letter(suggestion['keep'])
            
            # Calculate space to free
            space_mb = dup_group['size'] * (len(suggestion['delete'])) / (1024 * 1024)
            
            print(f"\n#{i} Duplicate Group (Size: {dup_group['size'] / (1024*1024):.1f} MB)")
            print(f"   KEEP: {suggestion['keep']}")
            print(f"   Date: {suggestion['keep_date']}")
            print(f"   Drive: {keep_drive}:\\")
            print(f"   \n   DELETE ({len(suggestion['delete'])} older versions):")
            
            for delete_path in suggestion['delete']:
                delete_drive = self.get_drive_letter(delete_path)
                print(f"      - {delete_path}")
                print(f"        Drive: {delete_drive}:\\")
            
            print(f"   \n   WOULD FREE: {space_mb:.1f} MB")
            print(f"   REASON: {suggestion['reason']}")
            
            total_deletable += len(suggestion['delete'])
            total_waste += dup_group['size'] * len(suggestion['delete']) / (1024 * 1024)
            
            results.append({
                'keep': suggestion['keep'],
                'delete': suggestion['delete'],
                'space_freed_mb': space_mb
            })
        
        print("\n" + "="*70)
        print(f"SUMMARY")
        print("="*70)
        print(f"Total duplicate groups: {len(duplicates)}")
        print(f"Files that can be deleted: {total_deletable}")
        print(f"Total space to free: {total_waste:.1f} MB ({total_waste/1024:.2f} GB)")
        print(f"Mode: {'DRY RUN (no files deleted)' if dry_run else 'ACTUAL CLEANUP'}")
        print("="*70)
        
        if not dry_run and results:
            print("\n[WARNING] Proceeding with actual deletion...")
            for result in results:
                for delete_path in result['delete']:
                    try:
                        Path(delete_path).unlink()
                        print(f"[OK] Deleted: {delete_path}")
                    except Exception as e:
                        print(f"[ERROR] Failed to delete {delete_path}: {e}")


def get_common_user_directories() -> List[str]:
    """
    Get all common user directories across drives.
    Automatically checks which directories exist.
    """
    import os
    
    common_paths = []
    username = os.getenv('USERNAME', 'user')
    
    # Scan C: drive locations
    c_drive_locations = [
        f'C:\\Users\\{username}\\Desktop',
        f'C:\\Users\\{username}\\Downloads',
        f'C:\\Users\\{username}\\Documents',
        f'C:\\Users\\{username}\\Pictures',
        f'C:\\Users\\{username}\\Videos',
        f'C:\\Users\\{username}\\Music',
        f'C:\\Users\\{username}\\AppData\\Local\\Downloads',
    ]
    
    # Scan D: drive locations (if D: exists)
    d_drive_locations = [
        'D:\\',
        'D:\\Downloads',
        'D:\\Documents',
        'D:\\Backup',
        'D:\\Pictures',
        'D:\\Videos',
    ]
    
    # Scan E: drive locations (if E: exists)
    e_drive_locations = [
        'E:\\',
        'E:\\Downloads',
        'E:\\Documents',
        'E:\\Backup',
    ]
    
    # Check all locations and add existing ones
    all_locations = c_drive_locations + d_drive_locations + e_drive_locations
    
    for path in all_locations:
        if os.path.exists(path):
            common_paths.append(path)
            print(f"[FOUND] {path}")
        else:
            print(f"[SKIP]  {path} (not found)")
    
    if not common_paths:
        print("\n[ERROR] No directories found!")
        return c_drive_locations  # Return defaults
    
    return common_paths


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


def is_path_excluded(path: str, exclude_patterns: List[str]) -> bool:
    p = path.replace('\\', '/').lower()
    for pat in exclude_patterns:
        pat_norm = pat.replace('\\', '/').lower()
        # simple startswith or glob match
        if p.startswith(pat_norm) or fnmatch.fnmatch(p, pat_norm):
            return True
    return False


def detect_candidate_directories(drives: List[str], sample_depth: int = 1, min_files: int = 20, top_n: int = 30, exclude_patterns: Optional[List[str]] = None) -> List[str]:
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

            if is_path_excluded(root_norm, exclude_patterns):
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


def generate_structure_report(directories: List[str], out_path: str = 'cross_drive_structure.json', sample_limit: int = 200) -> Dict:
    """
    Walk candidate directories shallowly and write a structure report (json) with counts and sizes.
    Returns the report dict.
    """
    report = {'generated_at': datetime.now(timezone.utc).isoformat() + 'Z', 'directories': []}

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


def human_size(bytes_size: float) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


if __name__ == '__main__':
    manager = CrossDriveDuplicateManager()
    
    print("\n" + "="*70)
    print("SCANNING FOR AVAILABLE DIRECTORIES...")
    print("="*70 + "\n")
    
    # Automatically enumerate drives and detect candidate directories
    drives = enumerate_available_drives()
    print(f"Detected drives: {drives}")

    # Use heuristic detector to pick top candidate folders to scan
    print('\nDetecting candidate directories (shallow sampling)...')
    exclude_patterns = [
        'C:/Windows', 'C:/Program Files', 'C:/Program Files (x86)', 'C:/ProgramData',
        '*/System Volume Information/*', '*/$Recycle.Bin/*', '*/WindowsApps/*'
    ]
    directories = detect_candidate_directories(drives, sample_depth=1, top_n=40, exclude_patterns=exclude_patterns)

    print("\n" + "="*70)
    print(f"WILL SCAN {len(directories)} DIRECTORIES (top candidates)")
    print("="*70 + "\n")

    # Generate a shallow structure report and save it
    struct_report = generate_structure_report(directories, out_path='cross_drive_structure.json')
    total_files = sum(d.get('file_count', 0) for d in struct_report.get('directories', []))
    total_bytes = sum(d.get('total_size', 0) for d in struct_report.get('directories', []))
    print(f"Structure report written to cross_drive_structure.json")
    print(f"Candidate directories: {len(struct_report.get('directories', []))}")
    print(f"Total files (sampled): {total_files}, Total size (sampled): {human_size(total_bytes)}")

    # Allow user to optionally exclude paths before running analysis
    try:
        resp = input("Would you like to exclude any paths from scanning? (comma-separated, enter to skip): ")
    except Exception:
        resp = ''
    if resp:
        user_excludes = [p.strip() for p in resp.split(',') if p.strip()]
        if user_excludes:
            # filter directories
            filtered = []
            for d in directories:
                if any(d.lower().startswith(ex.lower()) or fnmatch.fnmatch(d.lower(), ex.lower()) for ex in user_excludes):
                    print(f"[USER EXCLUDE] Skipping {d}")
                else:
                    filtered.append(d)
            directories = filtered

    # Confirm to proceed to duplicate analysis
    try:
        proceed = input("Proceed to duplicate analysis (DRY RUN)? (y/N): ").strip().lower() or 'n'
    except Exception:
        proceed = 'n'

    if proceed != 'y':
        print("Aborting. No changes made. You can inspect cross_drive_structure.json and rerun the script when ready.")
        sys.exit(0)

    # Run duplicate analysis in DRY RUN to produce a summary
    manager.clean_cross_drive_duplicates(directories, dry_run=True)

    # Ask user for final approval to delete
    try:
        final = input("Do you want to perform the actual cleanup and delete the older duplicates? (y/N): ").strip().lower() or 'n'
    except Exception:
        final = 'n'

    if final == 'y':
        # Optionally ask for quarantine directory or perform permanent deletion
        try:
            quarantine = input("Enter a quarantine directory to MOVE deleted files into (leave blank to permanently delete): ").strip()
        except Exception:
            quarantine = ''

        if quarantine:
            print(f"Quarantine not implemented in this quick-run. Proceeding with permanent deletion instead.")

        manager.clean_cross_drive_duplicates(directories, dry_run=False)
        print("Cleanup finished.")
    else:
        print("No changes performed. Review the dry-run results and run again when ready.")

