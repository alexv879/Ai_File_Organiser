"""
Performance Optimizer - Intelligent Quantization & Speed Enhancement

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module implements intelligent quantization and performance optimization
to balance detail extraction with processing speed. Key principle: extract
only what's NECESSARY for good organization, not everything possible.

QUANTIZATION STRATEGIES:
- Minimal: Fastest, basic info only
- Balanced: Good speed/detail tradeoff (RECOMMENDED)
- Detailed: More metadata, slower
- Maximum: Everything available, slowest

PERFORMANCE OPTIMIZATIONS:
- Metadata caching (avoid re-extraction)
- Batch processing (group operations)
- Parallel processing (multi-threading)
- Lazy loading (extract only when needed)
- Smart sampling (check subset, not all files)
- Progressive processing (quick scan first, details later)

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)


class QuantizationLevel(Enum):
    """
    Quantization levels - how much detail to extract.
    
    Higher levels = more accuracy but slower
    Lower levels = less detail but much faster
    """
    MINIMAL = "minimal"        # File system info only (fastest)
    BALANCED = "balanced"      # Key metadata only (recommended)
    DETAILED = "detailed"      # Most metadata (slower)
    MAXIMUM = "maximum"        # Everything available (slowest)


class ProcessingStrategy(Enum):
    """Processing strategy for file operations"""
    SEQUENTIAL = "sequential"      # One at a time (reliable)
    BATCH = "batch"               # Process in batches (efficient)
    PARALLEL = "parallel"         # Multi-threaded (fastest)
    PROGRESSIVE = "progressive"   # Quick scan + lazy details (smart)


class PerformanceOptimizer:
    """
    Optimizes file organization performance through intelligent quantization
    and caching strategies.
    
    Key Features:
    - Metadata caching (avoid re-extraction)
    - Batch processing (reduce overhead)
    - Parallel processing (utilize cores)
    - Smart quantization (extract only what's needed)
    - Progressive loading (fast preview, lazy details)
    """
    
    def __init__(self, config=None):
        """
        Initialize performance optimizer.
        
        Args:
            config: Configuration object with performance settings
        """
        self.config = config
        
        # Quantization settings
        self.quantization_level = getattr(
            config, 'quantization_level', QuantizationLevel.BALANCED.value
        )
        
        # Processing settings
        self.processing_strategy = getattr(
            config, 'processing_strategy', ProcessingStrategy.BATCH.value
        )
        self.batch_size = getattr(config, 'batch_size', 100)
        self.max_workers = getattr(config, 'max_workers', 4)
        
        # Caching settings
        self.enable_cache = getattr(config, 'enable_metadata_cache', True)
        self.cache_ttl_hours = getattr(config, 'cache_ttl_hours', 24)
        self.cache_dir = getattr(config, 'cache_dir', '.cache/metadata')
        
        # Performance limits
        self.max_file_size_mb = getattr(config, 'max_file_size_mb', 100)
        self.timeout_seconds = getattr(config, 'timeout_seconds', 5)
        
        # Initialize cache
        self.metadata_cache = {}
        if self.enable_cache:
            self._load_cache()
        
        logger.info(f"Performance Optimizer initialized: "
                   f"quantization={self.quantization_level}, "
                   f"strategy={self.processing_strategy}")
    
    def get_quantization_profile(self, level: str) -> Dict[str, Any]:
        """
        Get extraction profile for quantization level.
        
        Returns what metadata to extract for each level.
        """
        profiles = {
            QuantizationLevel.MINIMAL.value: {
                'file_system': True,      # Name, size, dates
                'extension': True,        # File type
                'exif_date': False,       # Skip EXIF date
                'exif_gps': False,        # Skip GPS
                'exif_camera': False,     # Skip camera info
                'pdf_metadata': False,    # Skip PDF metadata
                'pdf_content': False,     # Skip content analysis
                'audio_tags': False,      # Skip ID3 tags
                'video_info': False,      # Skip video metadata
                'document_props': False,  # Skip document properties
                'processing_time_ms': 10, # Target: 10ms per file
                'description': 'Fastest - file system info only'
            },
            
            QuantizationLevel.BALANCED.value: {
                'file_system': True,      # Name, size, dates
                'extension': True,        # File type
                'exif_date': True,        # ✓ EXIF date (important!)
                'exif_gps': True,         # ✓ GPS (useful for photos)
                'exif_camera': False,     # Skip camera (not critical)
                'pdf_metadata': True,     # ✓ PDF title/author
                'pdf_content': True,      # ✓ Content detection (invoice, etc.)
                'audio_tags': True,       # ✓ Artist/album (music library)
                'video_info': True,       # ✓ Resolution/duration
                'document_props': True,   # ✓ Author/keywords
                'processing_time_ms': 50, # Target: 50ms per file
                'description': 'Recommended - key metadata only'
            },
            
            QuantizationLevel.DETAILED.value: {
                'file_system': True,
                'extension': True,
                'exif_date': True,
                'exif_gps': True,
                'exif_camera': True,      # ✓ Include camera info
                'pdf_metadata': True,
                'pdf_content': True,
                'pdf_full_text': True,    # ✓ Extract more text
                'audio_tags': True,
                'audio_bitrate': True,    # ✓ Audio quality details
                'video_info': True,
                'video_codec': True,      # ✓ Codec information
                'document_props': True,
                'document_preview': True, # ✓ Content preview
                'processing_time_ms': 200, # Target: 200ms per file
                'description': 'More detail - most metadata'
            },
            
            QuantizationLevel.MAXIMUM.value: {
                'file_system': True,
                'extension': True,
                'exif_all': True,         # All EXIF data
                'exif_thumbnails': True,  # Extract thumbnails
                'pdf_all': True,          # All PDF metadata
                'pdf_full_text': True,    # Complete text extraction
                'audio_all': True,        # All audio metadata
                'audio_waveform': True,   # Generate waveform
                'video_all': True,        # All video metadata
                'video_thumbnails': True, # Extract video thumbnails
                'document_all': True,     # All document properties
                'document_full_text': True, # Complete text extraction
                'processing_time_ms': 1000, # Target: 1s per file
                'description': 'Maximum - everything available'
            }
        }
        
        return profiles.get(level, profiles[QuantizationLevel.BALANCED.value])
    
    def should_extract_metadata(self, file_path: str, 
                               metadata_type: str) -> bool:
        """
        Determine if metadata should be extracted based on quantization level.
        
        Args:
            file_path: Path to file
            metadata_type: Type of metadata (exif_date, pdf_metadata, etc.)
            
        Returns:
            True if should extract, False to skip
        """
        profile = self.get_quantization_profile(self.quantization_level)
        
        # Check if file size exceeds limit
        try:
            size_mb = os.path.getsize(file_path) / (1024**2)
            if size_mb > self.max_file_size_mb:
                logger.warning(f"File {file_path} exceeds size limit "
                             f"({size_mb:.1f}MB > {self.max_file_size_mb}MB), "
                             f"skipping metadata extraction")
                return False
        except:
            pass
        
        return profile.get(metadata_type, False)
    
    def get_from_cache(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata from cache if available and not expired.
        
        Args:
            file_path: Path to file
            
        Returns:
            Cached metadata dict or None
        """
        if not self.enable_cache:
            return None
        
        cache_key = self._get_cache_key(file_path)
        
        if cache_key in self.metadata_cache:
            cached = self.metadata_cache[cache_key]
            
            # Check if cache is expired
            cache_time = cached.get('cache_time')
            if cache_time:
                cache_age = datetime.now() - datetime.fromisoformat(cache_time)
                if cache_age < timedelta(hours=self.cache_ttl_hours):
                    # Check if file was modified since caching
                    try:
                        file_mtime = datetime.fromtimestamp(
                            os.path.getmtime(file_path)
                        )
                        cache_mtime = datetime.fromisoformat(
                            cached.get('file_modified', cache_time)
                        )
                        
                        if file_mtime <= cache_mtime:
                            logger.debug(f"Cache hit: {file_path}")
                            return cached.get('metadata')
                    except:
                        pass
        
        logger.debug(f"Cache miss: {file_path}")
        return None
    
    def save_to_cache(self, file_path: str, metadata: Dict[str, Any]):
        """
        Save metadata to cache.
        
        Args:
            file_path: Path to file
            metadata: Metadata dict to cache
        """
        if not self.enable_cache:
            return
        
        cache_key = self._get_cache_key(file_path)
        
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        except:
            file_mtime = datetime.now()
        
        self.metadata_cache[cache_key] = {
            'cache_time': datetime.now().isoformat(),
            'file_modified': file_mtime.isoformat(),
            'metadata': metadata,
            'quantization_level': self.quantization_level
        }
        
        # Periodically save cache to disk
        if len(self.metadata_cache) % 100 == 0:
            self._save_cache()
    
    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key for file"""
        # Use file path + modification time as key
        try:
            mtime = os.path.getmtime(file_path)
            key_str = f"{file_path}:{mtime}"
        except:
            key_str = file_path
        
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _load_cache(self):
        """Load metadata cache from disk"""
        cache_file = Path(self.cache_dir) / 'metadata_cache.json'
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self.metadata_cache = json.load(f)
                logger.info(f"Loaded {len(self.metadata_cache)} cached entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.metadata_cache = {}
    
    def _save_cache(self):
        """Save metadata cache to disk"""
        cache_file = Path(self.cache_dir) / 'metadata_cache.json'
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Remove expired entries before saving
            self._cleanup_cache()
            
            with open(cache_file, 'w') as f:
                json.dump(self.metadata_cache, f, indent=2)
            logger.debug(f"Saved {len(self.metadata_cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _cleanup_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = []
        
        for key, value in self.metadata_cache.items():
            cache_time = value.get('cache_time')
            if cache_time:
                cache_age = now - datetime.fromisoformat(cache_time)
                if cache_age > timedelta(hours=self.cache_ttl_hours):
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.metadata_cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def process_files_batch(self, file_paths: List[str],
                           extractor_func) -> List[Dict[str, Any]]:
        """
        Process files in batches for efficiency.
        
        Args:
            file_paths: List of file paths to process
            extractor_func: Function to extract metadata (callable)
            
        Returns:
            List of metadata dicts
        """
        if self.processing_strategy == ProcessingStrategy.PARALLEL.value:
            return self._process_parallel(file_paths, extractor_func)
        
        elif self.processing_strategy == ProcessingStrategy.BATCH.value:
            return self._process_batch(file_paths, extractor_func)
        
        else:  # SEQUENTIAL
            return self._process_sequential(file_paths, extractor_func)
    
    def _process_sequential(self, file_paths: List[str],
                           extractor_func) -> List[Dict[str, Any]]:
        """Process files one by one"""
        results = []
        
        for file_path in file_paths:
            # Check cache first
            metadata = self.get_from_cache(file_path)
            
            if metadata is None:
                # Extract metadata
                metadata = extractor_func(file_path)
                self.save_to_cache(file_path, metadata)
            
            results.append(metadata)
        
        return results
    
    def _process_batch(self, file_paths: List[str],
                      extractor_func) -> List[Dict[str, Any]]:
        """Process files in batches"""
        results = []
        
        for i in range(0, len(file_paths), self.batch_size):
            batch = file_paths[i:i + self.batch_size]
            
            logger.info(f"Processing batch {i//self.batch_size + 1} "
                       f"({len(batch)} files)")
            
            for file_path in batch:
                metadata = self.get_from_cache(file_path)
                
                if metadata is None:
                    metadata = extractor_func(file_path)
                    self.save_to_cache(file_path, metadata)
                
                results.append(metadata)
        
        return results
    
    def _process_parallel(self, file_paths: List[str],
                         extractor_func) -> List[Dict[str, Any]]:
        """Process files in parallel using thread pool"""
        results = []
        
        def process_single(file_path):
            metadata = self.get_from_cache(file_path)
            
            if metadata is None:
                metadata = extractor_func(file_path)
                self.save_to_cache(file_path, metadata)
            
            return metadata
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_single, fp): fp 
                for fp in file_paths
            }
            
            for future in as_completed(futures):
                try:
                    metadata = future.result(timeout=self.timeout_seconds)
                    results.append(metadata)
                except Exception as e:
                    file_path = futures[future]
                    logger.error(f"Error processing {file_path}: {e}")
                    results.append({'error': str(e), 'path': file_path})
        
        return results
    
    def estimate_processing_time(self, num_files: int) -> Dict[str, Any]:
        """
        Estimate processing time based on quantization level and strategy.
        
        Args:
            num_files: Number of files to process
            
        Returns:
            Dict with time estimates
        """
        profile = self.get_quantization_profile(self.quantization_level)
        time_per_file_ms = profile['processing_time_ms']
        
        # Calculate base time
        total_ms = num_files * time_per_file_ms
        
        # Apply strategy multiplier
        if self.processing_strategy == ProcessingStrategy.PARALLEL.value:
            # Parallel processing reduces time (assuming 4 cores)
            total_ms = total_ms / self.max_workers
        elif self.processing_strategy == ProcessingStrategy.BATCH.value:
            # Batch has ~10% overhead reduction
            total_ms = total_ms * 0.9
        
        # Apply cache hit rate (assume 30% cache hit rate)
        cache_hit_rate = 0.3 if self.enable_cache else 0
        total_ms = total_ms * (1 - cache_hit_rate)
        
        total_seconds = total_ms / 1000
        
        return {
            'num_files': num_files,
            'quantization_level': self.quantization_level,
            'processing_strategy': self.processing_strategy,
            'time_per_file_ms': time_per_file_ms,
            'estimated_total_seconds': total_seconds,
            'estimated_total_minutes': total_seconds / 60,
            'estimated_total_formatted': self._format_duration(total_seconds),
            'cache_enabled': self.enable_cache,
            'parallel_workers': self.max_workers if self.processing_strategy == ProcessingStrategy.PARALLEL.value else 1
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"
    
    def get_performance_recommendations(self, 
                                       num_files: int,
                                       current_time_seconds: Optional[float] = None
                                       ) -> List[str]:
        """
        Get recommendations to improve performance.
        
        Args:
            num_files: Number of files being processed
            current_time_seconds: Current processing time (optional)
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Check if processing is too slow
        if current_time_seconds:
            time_per_file = current_time_seconds / num_files if num_files > 0 else 0
            profile = self.get_quantization_profile(self.quantization_level)
            target_time = profile['processing_time_ms'] / 1000
            
            if time_per_file > target_time * 2:
                recommendations.append(
                    f"Processing is slow ({time_per_file:.2f}s per file). "
                    f"Consider lowering quantization level to '{QuantizationLevel.MINIMAL.value}' "
                    f"for faster processing."
                )
        
        # Recommend quantization level based on file count
        if num_files > 10000:
            if self.quantization_level != QuantizationLevel.MINIMAL.value:
                recommendations.append(
                    f"Large file count ({num_files:,} files). "
                    f"Consider '{QuantizationLevel.MINIMAL.value}' quantization "
                    f"for 10x faster processing."
                )
        
        # Recommend parallel processing
        if num_files > 100 and self.processing_strategy != ProcessingStrategy.PARALLEL.value:
            recommendations.append(
                f"With {num_files:,} files, '{ProcessingStrategy.PARALLEL.value}' "
                f"strategy could be {self.max_workers}x faster."
            )
        
        # Recommend caching
        if not self.enable_cache:
            recommendations.append(
                "Enable metadata caching for 30-50% speed improvement on subsequent runs."
            )
        
        # Recommend batch size adjustment
        if self.processing_strategy == ProcessingStrategy.BATCH.value:
            if self.batch_size < 100:
                recommendations.append(
                    f"Batch size ({self.batch_size}) is small. "
                    f"Increase to 100-500 for better efficiency."
                )
        
        return recommendations


def create_performance_optimizer(config=None) -> PerformanceOptimizer:
    """Create a performance optimizer instance"""
    return PerformanceOptimizer(config)


if __name__ == "__main__":
    # Test performance optimizer
    print("Testing Performance Optimizer...\n")
    
    class MockConfig:
        quantization_level = "balanced"
        processing_strategy = "parallel"
        batch_size = 100
        max_workers = 4
        enable_metadata_cache = True
        cache_ttl_hours = 24
        cache_dir = ".cache/metadata"
        max_file_size_mb = 100
        timeout_seconds = 5
    
    optimizer = PerformanceOptimizer(MockConfig())
    
    # Test 1: Get quantization profiles
    print("="*70)
    print("QUANTIZATION PROFILES")
    print("="*70)
    for level in QuantizationLevel:
        profile = optimizer.get_quantization_profile(level.value)
        print(f"\n{level.value.upper()}:")
        print(f"  Description: {profile['description']}")
        print(f"  Target time: {profile['processing_time_ms']}ms per file")
        print(f"  EXIF date: {profile.get('exif_date', False)}")
        print(f"  PDF metadata: {profile.get('pdf_metadata', False)}")
        print(f"  Audio tags: {profile.get('audio_tags', False)}")
    
    # Test 2: Time estimation
    print("\n" + "="*70)
    print("TIME ESTIMATION (1000 files)")
    print("="*70)
    estimate = optimizer.estimate_processing_time(1000)
    print(f"Quantization: {estimate['quantization_level']}")
    print(f"Strategy: {estimate['processing_strategy']}")
    print(f"Time per file: {estimate['time_per_file_ms']}ms")
    print(f"Estimated total: {estimate['estimated_total_formatted']}")
    print(f"Cache enabled: {estimate['cache_enabled']}")
    
    # Test 3: Recommendations
    print("\n" + "="*70)
    print("PERFORMANCE RECOMMENDATIONS")
    print("="*70)
    recommendations = optimizer.get_performance_recommendations(5000, 300.0)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
