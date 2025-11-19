"""Intelligent space optimization engine.

This module analyzes disk usage and provides recommendations for
freeing up space through:
- Duplicate file removal
- Archiving old/unused files to cloud
- Compressing large folders
- Identifying large files

Example:
    >>> optimizer = SpaceOptimizer()
    >>> report = optimizer.analyze_storage()
    >>> print(f"Potential savings: {optimizer.format_size(report['total_savings'])}")
    >>> optimizer.archive_old_files(min_age_days=180)
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import shutil

logger = logging.getLogger(__name__)


class SpaceOptimizer:
    """Intelligent storage space optimizer.

    Features:
    - Duplicate file detection across drives
    - Old file identification
    - Large file finder
    - Cloud archiving recommendations
    - Compression opportunities
    - Storage usage visualization
    """

    def __init__(
        self,
        min_file_size: int = 1024,  # Minimum 1KB
        hash_algorithm: str = "md5"
    ):
        """Initialize space optimizer.

        Args:
            min_file_size: Minimum file size to consider (bytes)
            hash_algorithm: Hash algorithm (md5, sha1, sha256)
        """
        self.min_file_size = min_file_size
        self.hash_algorithm = hash_algorithm

    def analyze_storage(self, paths: List[Path]) -> Dict[str, Any]:
        """Analyze storage and generate comprehensive report.

        Args:
            paths: List of directories to analyze

        Returns:
            Dict: Complete storage analysis report
        """
        logger.info("Starting storage analysis...")

        report = {
            "duplicates": self.find_all_duplicates(paths),
            "large_files": self.find_large_files(paths, min_size_gb=0.1),
            "old_files": self.find_old_files(paths, days=180),
            "compressible": self.find_compressible_folders(paths),
            "total_size": 0,
            "total_savings": 0,
            "recommendations": []
        }

        # Calculate total size
        for path in paths:
            if path.exists():
                report["total_size"] += self._get_directory_size(path)

        # Calculate potential savings
        dup_savings = sum(
            sum(file["size"] for file in group["files"][1:])  # All except one
            for group in report["duplicates"]
        )

        old_savings = sum(f["size"] for f in report["old_files"])
        compress_savings = sum(f["potential_savings"] for f in report["compressible"])

        report["total_savings"] = dup_savings + old_savings + compress_savings

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        logger.info(f"Storage analysis complete. Potential savings: {self.format_size(report['total_savings'])}")

        return report

    def find_all_duplicates(self, paths: List[Path]) -> List[Dict[str, Any]]:
        """Find duplicate files across multiple paths.

        Args:
            paths: List of directories to scan

        Returns:
            List[Dict]: List of duplicate file groups
        """
        logger.info("Scanning for duplicates...")

        hash_map = defaultdict(list)

        for path in paths:
            if not path.exists():
                continue

            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                if file_path.stat().st_size < self.min_file_size:
                    continue

                try:
                    file_hash = self._calculate_file_hash(file_path)
                    file_info = {
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime)
                    }
                    hash_map[file_hash].append(file_info)

                except (PermissionError, OSError) as e:
                    logger.debug(f"Skipping file {file_path}: {e}")
                    continue

        # Filter to only groups with duplicates
        duplicate_groups = [
            {
                "hash": file_hash,
                "files": files,
                "count": len(files),
                "total_size": sum(f["size"] for f in files),
                "wasted_space": sum(f["size"] for f in files[1:])  # All except first
            }
            for file_hash, files in hash_map.items()
            if len(files) > 1
        ]

        # Sort by wasted space (descending)
        duplicate_groups.sort(key=lambda x: x["wasted_space"], reverse=True)

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups

    def find_large_files(
        self,
        paths: List[Path],
        min_size_gb: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Find large files.

        Args:
            paths: Directories to scan
            min_size_gb: Minimum file size in GB

        Returns:
            List[Dict]: List of large files
        """
        logger.info(f"Scanning for files larger than {min_size_gb} GB...")

        min_size_bytes = int(min_size_gb * 1024 * 1024 * 1024)
        large_files = []

        for path in paths:
            if not path.exists():
                continue

            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    size = file_path.stat().st_size
                    if size >= min_size_bytes:
                        large_files.append({
                            "path": str(file_path),
                            "size": size,
                            "size_gb": size / (1024**3),
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime),
                            "accessed": datetime.fromtimestamp(file_path.stat().st_atime)
                        })

                except (PermissionError, OSError):
                    continue

        # Sort by size (descending)
        large_files.sort(key=lambda x: x["size"], reverse=True)

        logger.info(f"Found {len(large_files)} large files")
        return large_files

    def find_old_files(
        self,
        paths: List[Path],
        days: int = 180
    ) -> List[Dict[str, Any]]:
        """Find files that haven't been accessed recently.

        Args:
            paths: Directories to scan
            days: Files not accessed in this many days

        Returns:
            List[Dict]: List of old files suitable for archiving
        """
        logger.info(f"Scanning for files not accessed in {days} days...")

        cutoff_date = datetime.now() - timedelta(days=days)
        old_files = []

        for path in paths:
            if not path.exists():
                continue

            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                try:
                    accessed = datetime.fromtimestamp(file_path.stat().st_atime)
                    modified = datetime.fromtimestamp(file_path.stat().st_mtime)

                    # Use most recent of access or modification
                    last_used = max(accessed, modified)

                    if last_used < cutoff_date:
                        old_files.append({
                            "path": str(file_path),
                            "size": file_path.stat().st_size,
                            "last_accessed": accessed,
                            "last_modified": modified,
                            "days_since_use": (datetime.now() - last_used).days
                        })

                except (PermissionError, OSError):
                    continue

        # Sort by days since use (descending)
        old_files.sort(key=lambda x: x["days_since_use"], reverse=True)

        logger.info(f"Found {len(old_files)} old files")
        return old_files

    def find_compressible_folders(
        self,
        paths: List[Path],
        min_size_mb: int = 100
    ) -> List[Dict[str, Any]]:
        """Find folders that could benefit from compression.

        Args:
            paths: Directories to scan
            min_size_mb: Minimum folder size in MB

        Returns:
            List[Dict]: List of compressible folders
        """
        logger.info("Scanning for compressible folders...")

        min_size_bytes = min_size_mb * 1024 * 1024
        compressible = []

        for path in paths:
            if not path.exists():
                continue

            for folder_path in path.rglob("*"):
                if not folder_path.is_dir():
                    continue

                try:
                    folder_size = self._get_directory_size(folder_path)

                    if folder_size >= min_size_bytes:
                        # Estimate compression ratio (conservative 30%)
                        estimated_savings = int(folder_size * 0.3)

                        compressible.append({
                            "path": str(folder_path),
                            "size": folder_size,
                            "potential_savings": estimated_savings,
                            "compression_ratio": 0.7
                        })

                except (PermissionError, OSError):
                    continue

        # Sort by potential savings (descending)
        compressible.sort(key=lambda x: x["potential_savings"], reverse=True)

        logger.info(f"Found {len(compressible)} compressible folders")
        return compressible

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash."""
        if self.hash_algorithm == "md5":
            hasher = hashlib.md5()
        elif self.hash_algorithm == "sha1":
            hasher = hashlib.sha1()
        elif self.hash_algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory."""
        total = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    try:
                        total += file_path.stat().st_size
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError):
            pass

        return total

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Duplicates
        if report["duplicates"]:
            dup_savings = sum(g["wasted_space"] for g in report["duplicates"])
            recommendations.append(
                f"Remove {len(report['duplicates'])} duplicate file groups to save {self.format_size(dup_savings)}"
            )

        # Old files
        if report["old_files"]:
            old_savings = sum(f["size"] for f in report["old_files"])
            recommendations.append(
                f"Archive {len(report['old_files'])} old files to cloud to save {self.format_size(old_savings)}"
            )

        # Large files
        if report["large_files"]:
            recommendations.append(
                f"Review {len(report['large_files'])} large files - consider archiving to cloud"
            )

        # Compressible
        if report["compressible"]:
            compress_savings = sum(f["potential_savings"] for f in report["compressible"])
            recommendations.append(
                f"Compress {len(report['compressible'])} folders to save ~{self.format_size(compress_savings)}"
            )

        return recommendations

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
