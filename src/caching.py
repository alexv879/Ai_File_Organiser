"""
Persistent caching using diskcache for improved performance.
Provides caching for file operations, metadata, and computation results.
"""

import hashlib
import json
import os
    # removed unused import 'pickle'
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import diskcache as dc
from functools import wraps


class FileCache:
    """File-based caching using diskcache."""

    def __init__(self, cache_dir: str = "./cache/files", size_limit: int = int(1e9)):
        """Initialize file cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache = dc.Cache(
            directory=str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy='least-recently-used'
        )

    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file for cache key."""
        try:
            stat = os.stat(file_path)
            # Use file path, size, and modification time for hash
            hash_input = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()
        except (OSError, FileNotFoundError):
            return hashlib.md5(file_path.encode()).hexdigest()

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get cached file content."""
        cache_key = f"content:{self._get_file_hash(file_path)}"
        result = self.cache.get(cache_key)
        return str(result) if result is not None else None

    def set_file_content(self, file_path: str, content: str, expire: Optional[int] = None) -> None:
        """Cache file content."""
        cache_key = f"content:{self._get_file_hash(file_path)}"
        self.cache.set(cache_key, content, expire=expire)

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata."""
        cache_key = f"metadata:{self._get_file_hash(file_path)}"
        result = self.cache.get(cache_key)
        return result if isinstance(result, dict) else None

    def set_file_metadata(self, file_path: str, metadata: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache file metadata."""
        cache_key = f"metadata:{self._get_file_hash(file_path)}"
        self.cache.set(cache_key, metadata, expire=expire)

    def invalidate_file(self, file_path: str) -> None:
        """Invalidate all cached data for a file."""
        file_hash = self._get_file_hash(file_path)
        keys_to_delete = [
            f"content:{file_hash}",
            f"metadata:{file_hash}",
            f"analysis:{file_hash}",
            f"duplicates:{file_hash}"
        ]

        for key in keys_to_delete:
            self.cache.delete(key)

    def get_file_analysis(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file analysis results."""
        cache_key = f"analysis:{self._get_file_hash(file_path)}"
        result = self.cache.get(cache_key)
        return result if isinstance(result, dict) else None

    def set_file_analysis(self, file_path: str, analysis: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache file analysis results."""
        cache_key = f"analysis:{self._get_file_hash(file_path)}"
        self.cache.set(cache_key, analysis, expire=expire)

    def get_duplicate_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached duplicate information."""
        cache_key = f"duplicates:{self._get_file_hash(file_path)}"
        result = self.cache.get(cache_key)
        return result if isinstance(result, dict) else None

    def set_duplicate_info(self, file_path: str, duplicate_info: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache duplicate information."""
        cache_key = f"duplicates:{self._get_file_hash(file_path)}"
        self.cache.set(cache_key, duplicate_info, expire=expire)

      # removed duplicate ComputationCache class

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        return self.cache.expire()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # diskcache doesn't provide hit/miss statistics directly
            return {
                'size': self.cache.volume(),  # Use volume() instead of len()
                'directory': str(self.cache_dir),
            }
        except Exception:
            return {
                'size': 0,
                'directory': str(self.cache_dir),
            }

    def close(self) -> None:
        """Close the cache."""
        self.cache.close()


class ComputationCache:
    """Cache for computation results."""

    def __init__(self, cache_dir: str = "./cache/computation", size_limit: int = int(500e6)):
        """Initialize computation cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache = dc.Cache(
            directory=str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy='least-recently-used'
        )

    def _make_cache_key(self, func_name: str, args: Tuple, kwargs: Dict) -> str:
        """Create a cache key from function name and arguments."""
        # Convert args and kwargs to a stable representation
        args_str = json.dumps(args, sort_keys=True, default=str)
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_input = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(key_input.encode()).hexdigest()

    def get(self, func_name: str, args: Tuple = (), kwargs: Optional[Dict] = None) -> Any:
        """Get cached computation result."""
        if kwargs is None:
            kwargs = {}
        cache_key = self._make_cache_key(func_name, args, kwargs)
        return self.cache.get(cache_key)

    def set(self, func_name: str, args: Tuple = (), kwargs: Optional[Dict] = None, value: Any = None, expire: Optional[int] = None) -> None:
        """Cache computation result."""
        if kwargs is None:
            kwargs = {}
        cache_key = self._make_cache_key(func_name, args, kwargs)
        self.cache.set(cache_key, value, expire=expire)

    def memoize(self, expire: Optional[int] = None):
        """Decorator for caching function results."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Try to get from cache first
                result = self.get(func.__name__, args, kwargs)
                if result is not None:
                    return result

                # Compute and cache
                result = func(*args, **kwargs)
                self.set(func.__name__, args, kwargs, result, expire=expire)
                return result

            return wrapper
        return decorator

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        return self.cache.expire()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # diskcache doesn't provide hit/miss statistics directly
            return {
                'size': self.cache.volume(),  # Use volume() instead of len()
                'directory': str(self.cache_dir),
            }
        except Exception:
            return {
                'size': 0,
                'directory': str(self.cache_dir),
            }

    def close(self) -> None:
        """Close the cache."""
        self.cache.close()


class DirectoryCache:
    """Cache for directory operations."""

    def __init__(self, cache_dir: str = "./cache/directories", size_limit: int = int(200e6)):
        """Initialize directory cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache = dc.Cache(
            directory=str(self.cache_dir),
            size_limit=size_limit,
            eviction_policy='least-recently-used'
        )

    def get_directory_listing(self, dir_path: str) -> Optional[List[str]]:
        """Get cached directory listing."""
        try:
            stat = os.stat(dir_path)
            cache_key = f"listing:{dir_path}:{stat.st_mtime}"
            result = self.cache.get(cache_key)
            return result if isinstance(result, list) else None
        except (OSError, FileNotFoundError):
            return None

    def set_directory_listing(self, dir_path: str, listing: List[str], expire: Optional[int] = None) -> None:
        """Cache directory listing."""
        try:
            stat = os.stat(dir_path)
            cache_key = f"listing:{dir_path}:{stat.st_mtime}"
            self.cache.set(cache_key, listing, expire=expire)
        except (OSError, FileNotFoundError):
            pass

    def get_directory_tree(self, dir_path: str, max_depth: int = 3) -> Optional[Dict[str, Any]]:
        """Get cached directory tree."""
        try:
            stat = os.stat(dir_path)
            cache_key = f"tree:{dir_path}:{stat.st_mtime}:{max_depth}"
            result = self.cache.get(cache_key)
            return result if isinstance(result, dict) else None
        except (OSError, FileNotFoundError):
            return None

    def set_directory_tree(self, dir_path: str, tree: Dict[str, Any], max_depth: int = 3, expire: Optional[int] = None) -> None:
        """Cache directory tree."""
        try:
            stat = os.stat(dir_path)
            cache_key = f"tree:{dir_path}:{stat.st_mtime}:{max_depth}"
            self.cache.set(cache_key, tree, expire=expire)
        except (OSError, FileNotFoundError):
            pass

    def invalidate_directory(self, dir_path: str) -> None:
        """Invalidate all cached data for a directory."""
        # Delete all keys that start with the directory path
        keys_to_delete = []
        for key in self.cache:
            if isinstance(key, str) and (key.startswith(f"listing:{dir_path}") or key.startswith(f"tree:{dir_path}")):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            self.cache.delete(key)

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        return self.cache.expire()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # diskcache doesn't provide hit/miss statistics directly
            return {
                'size': self.cache.volume(),  # Use volume() instead of len()
                'directory': str(self.cache_dir),
            }
        except Exception:
            return {
                'size': 0,
                'directory': str(self.cache_dir),
            }

    def close(self) -> None:
        """Close the cache."""
        self.cache.close()


class CacheManager:
    """Unified cache manager for all caching needs."""

    def __init__(self, base_cache_dir: str = "./cache"):
        """Initialize cache manager."""
        self.base_cache_dir = Path(base_cache_dir)
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize different cache types
        self.file_cache = FileCache(str(self.base_cache_dir / "files"))
        self.computation_cache = ComputationCache(str(self.base_cache_dir / "computation"))
        self.directory_cache = DirectoryCache(str(self.base_cache_dir / "directories"))

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get cached file content."""
        return self.file_cache.get_file_content(file_path)

    def set_file_content(self, file_path: str, content: str, expire: Optional[int] = None) -> None:
        """Cache file content."""
        self.file_cache.set_file_content(file_path, content, expire=expire)

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata."""
        return self.file_cache.get_file_metadata(file_path)

    def set_file_metadata(self, file_path: str, metadata: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache file metadata."""
        self.file_cache.set_file_metadata(file_path, metadata, expire=expire)

    def get_file_analysis(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached file analysis."""
        return self.file_cache.get_file_analysis(file_path)

    def set_file_analysis(self, file_path: str, analysis: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache file analysis."""
        self.file_cache.set_file_analysis(file_path, analysis, expire=expire)

    def get_duplicate_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get cached duplicate info."""
        return self.file_cache.get_duplicate_info(file_path)

    def set_duplicate_info(self, file_path: str, duplicate_info: Dict[str, Any], expire: Optional[int] = None) -> None:
        """Cache duplicate info."""
        self.file_cache.set_duplicate_info(file_path, duplicate_info, expire=expire)

    def get_directory_listing(self, dir_path: str) -> Optional[List[str]]:
        """Get cached directory listing."""
        return self.directory_cache.get_directory_listing(dir_path)

    def set_directory_listing(self, dir_path: str, listing: List[str], expire: Optional[int] = None) -> None:
        """Cache directory listing."""
        self.directory_cache.set_directory_listing(dir_path, listing, expire=expire)

    def get_directory_tree(self, dir_path: str, max_depth: int = 3) -> Optional[Dict[str, Any]]:
        """Get cached directory tree."""
        return self.directory_cache.get_directory_tree(dir_path, max_depth)

    def set_directory_tree(self, dir_path: str, tree: Dict[str, Any], max_depth: int = 3, expire: Optional[int] = None) -> None:
        """Cache directory tree."""
        self.directory_cache.set_directory_tree(dir_path, tree, max_depth, expire=expire)

    def memoize_computation(self, expire: Optional[int] = None):
        """Decorator for caching computation results."""
        return self.computation_cache.memoize(expire=expire)

    def invalidate_file(self, file_path: str) -> None:
        """Invalidate all cached data for a file."""
        self.file_cache.invalidate_file(file_path)

    def invalidate_directory(self, dir_path: str) -> None:
        """Invalidate all cached data for a directory."""
        self.directory_cache.invalidate_directory(dir_path)

    def clear_all_expired(self) -> Dict[str, int]:
        """Clear expired entries from all caches."""
        return {
            'file_cache': self.file_cache.clear_expired(),
            'computation_cache': self.computation_cache.clear_expired(),
            'directory_cache': self.directory_cache.clear_expired(),
        }

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {
            'file_cache': self.file_cache.get_stats(),
            'computation_cache': self.computation_cache.get_stats(),
            'directory_cache': self.directory_cache.get_stats(),
        }

    def close_all(self) -> None:
        """Close all caches."""
        self.file_cache.close()
        self.computation_cache.close()
        self.directory_cache.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close_all()


# Global cache manager instance
cache_manager = CacheManager()