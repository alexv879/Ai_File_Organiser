"""
Optimized Metadata Extractor - Fast & Intelligent

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.

This module wraps the existing metadata_extractor with performance
optimization and intelligent quantization.

KEY FEATURES:
- Respects quantization levels (extract only what's needed)
- Uses caching (avoid re-extraction)
- Batch processing (efficiency)
- Timeout protection (don't hang on slow files)
- Smart extraction (detect when full metadata needed)

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import time

from .performance_optimizer import PerformanceOptimizer, QuantizationLevel
from .metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)


class OptimizedMetadataExtractor:
    """
    Wrapper around MetadataExtractor that adds performance optimization.
    
    This class intelligently decides what metadata to extract based on:
    - Quantization level (minimal/balanced/detailed/maximum)
    - File type and size
    - Caching availability
    - Processing strategy
    """
    
    def __init__(self, config=None, performance_optimizer=None):
        """
        Initialize optimized metadata extractor.
        
        Args:
            config: Configuration object
            performance_optimizer: PerformanceOptimizer instance (optional)
        """
        self.config = config
        
        # Initialize base metadata extractor
        self.base_extractor = MetadataExtractor()
        
        # Initialize or use provided performance optimizer
        if performance_optimizer:
            self.optimizer = performance_optimizer
        else:
            from .performance_optimizer import create_performance_optimizer
            self.optimizer = create_performance_optimizer(config)
        
        logger.info("Optimized Metadata Extractor initialized with "
                   f"quantization level: {self.optimizer.quantization_level}")
    
    def extract_metadata(self, file_path: str, 
                        force_full: bool = False) -> Dict[str, Any]:
        """
        Extract metadata with intelligent quantization.
        
        Args:
            file_path: Path to file
            force_full: Force full extraction (ignore quantization)
            
        Returns:
            Dict with metadata
        """
        start_time = time.time()
        
        # Check cache first
        if not force_full:
            cached = self.optimizer.get_from_cache(file_path)
            if cached:
                logger.debug(f"Using cached metadata for {file_path}")
                return cached
        
        # Get quantization profile
        profile = self.optimizer.get_quantization_profile(
            self.optimizer.quantization_level
        )
        
        # Extract metadata based on profile
        metadata = self._extract_quantized(file_path, profile, force_full)
        
        # Add performance metrics
        extraction_time = time.time() - start_time
        metadata['extraction_time_ms'] = int(extraction_time * 1000)
        metadata['quantization_level'] = self.optimizer.quantization_level
        metadata['from_cache'] = False
        
        # Save to cache
        if not force_full:
            self.optimizer.save_to_cache(file_path, metadata)
        
        logger.debug(f"Extracted metadata for {file_path} in "
                    f"{extraction_time*1000:.1f}ms")
        
        return metadata
    
    def _extract_quantized(self, file_path: str, 
                          profile: Dict[str, Any],
                          force_full: bool) -> Dict[str, Any]:
        """
        Extract metadata according to quantization profile.
        
        Args:
            file_path: Path to file
            profile: Quantization profile dict
            force_full: Force full extraction
            
        Returns:
            Metadata dict
        """
        metadata = {}
        
        # Always include file system info (fast)
        if profile.get('file_system', True):
            metadata.update(self._extract_file_system_info(file_path))
        
        # Extension (fast)
        if profile.get('extension', True):
            metadata['extension'] = Path(file_path).suffix.lower()
        
        # Early return for minimal quantization
        if not force_full and self.optimizer.quantization_level == QuantizationLevel.MINIMAL.value:
            return metadata
        
        # Get file type
        file_ext = Path(file_path).suffix.lower()
        
        # IMAGE METADATA
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
            metadata.update(self._extract_image_metadata(file_path, profile, force_full))
        
        # PDF METADATA
        elif file_ext == '.pdf':
            metadata.update(self._extract_pdf_metadata(file_path, profile, force_full))
        
        # AUDIO METADATA
        elif file_ext in ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma']:
            metadata.update(self._extract_audio_metadata(file_path, profile, force_full))
        
        # VIDEO METADATA
        elif file_ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']:
            metadata.update(self._extract_video_metadata(file_path, profile, force_full))
        
        # DOCUMENT METADATA
        elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
            metadata.update(self._extract_document_metadata(file_path, profile, force_full))
        
        return metadata
    
    def _extract_file_system_info(self, file_path: str) -> Dict[str, Any]:
        """Extract basic file system information (always fast)"""
        try:
            stat = os.stat(file_path)
            return {
                'file_name': Path(file_path).name,
                'file_size': stat.st_size,
                'modified_date': stat.st_mtime,
                'created_date': stat.st_ctime,
            }
        except Exception as e:
            logger.warning(f"Error getting file system info for {file_path}: {e}")
            return {}
    
    def _extract_image_metadata(self, file_path: str, 
                               profile: Dict[str, Any],
                               force_full: bool) -> Dict[str, Any]:
        """Extract image metadata based on quantization level"""
        metadata = {'file_type': 'image'}
        
        # Quick check: should we extract EXIF at all?
        if not force_full:
            if not profile.get('exif_date') and not profile.get('exif_gps') and not profile.get('exif_camera'):
                return metadata
        
        try:
            # Use base extractor but filter results
            full_metadata = self.base_extractor.extract_image_metadata(file_path)
            
            # Include EXIF date if requested
            if force_full or profile.get('exif_date'):
                if 'date_taken' in full_metadata:
                    metadata['date_taken'] = full_metadata['date_taken']
            
            # Include GPS if requested
            if force_full or profile.get('exif_gps'):
                if 'gps_latitude' in full_metadata:
                    metadata['gps_latitude'] = full_metadata['gps_latitude']
                    metadata['gps_longitude'] = full_metadata['gps_longitude']
                if 'location_name' in full_metadata:
                    metadata['location_name'] = full_metadata['location_name']
            
            # Include camera info if requested
            if force_full or profile.get('exif_camera'):
                for key in ['camera_make', 'camera_model', 'lens', 'focal_length', 
                           'aperture', 'shutter_speed', 'iso']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
        except Exception as e:
            logger.warning(f"Error extracting image metadata: {e}")
        
        return metadata
    
    def _extract_pdf_metadata(self, file_path: str,
                             profile: Dict[str, Any],
                             force_full: bool) -> Dict[str, Any]:
        """Extract PDF metadata based on quantization level"""
        metadata = {'file_type': 'pdf'}
        
        # Quick check: should we extract PDF metadata?
        if not force_full:
            if not profile.get('pdf_metadata') and not profile.get('pdf_content'):
                return metadata
        
        try:
            full_metadata = self.base_extractor.extract_pdf_metadata(file_path)
            
            # Include basic metadata if requested
            if force_full or profile.get('pdf_metadata'):
                for key in ['title', 'author', 'subject', 'num_pages']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
            # Include content analysis if requested
            if force_full or profile.get('pdf_content'):
                for key in ['is_invoice', 'is_receipt', 'contains_table', 
                           'language', 'content_preview']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
        except Exception as e:
            logger.warning(f"Error extracting PDF metadata: {e}")
        
        return metadata
    
    def _extract_audio_metadata(self, file_path: str,
                               profile: Dict[str, Any],
                               force_full: bool) -> Dict[str, Any]:
        """Extract audio metadata based on quantization level"""
        metadata = {'file_type': 'audio'}
        
        # Quick check: should we extract audio tags?
        if not force_full and not profile.get('audio_tags'):
            return metadata
        
        try:
            full_metadata = self.base_extractor.extract_audio_metadata(file_path)
            
            # Include basic tags if requested
            if force_full or profile.get('audio_tags'):
                for key in ['title', 'artist', 'album', 'genre', 'year', 'duration']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
            # Include quality info if requested (detailed level)
            if force_full or profile.get('audio_bitrate'):
                for key in ['bitrate', 'sample_rate', 'channels']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
        except Exception as e:
            logger.warning(f"Error extracting audio metadata: {e}")
        
        return metadata
    
    def _extract_video_metadata(self, file_path: str,
                               profile: Dict[str, Any],
                               force_full: bool) -> Dict[str, Any]:
        """Extract video metadata based on quantization level"""
        metadata = {'file_type': 'video'}
        
        # Quick check: should we extract video info?
        if not force_full and not profile.get('video_info'):
            return metadata
        
        try:
            full_metadata = self.base_extractor.extract_video_metadata(file_path)
            
            # Include basic info if requested
            if force_full or profile.get('video_info'):
                for key in ['duration', 'width', 'height', 'resolution_category']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
            # Include codec info if requested (detailed level)
            if force_full or profile.get('video_codec'):
                for key in ['codec', 'fps', 'bitrate']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
        except Exception as e:
            logger.warning(f"Error extracting video metadata: {e}")
        
        return metadata
    
    def _extract_document_metadata(self, file_path: str,
                                  profile: Dict[str, Any],
                                  force_full: bool) -> Dict[str, Any]:
        """Extract document metadata based on quantization level"""
        metadata = {'file_type': 'document'}
        
        # Quick check: should we extract document properties?
        if not force_full and not profile.get('document_props'):
            return metadata
        
        try:
            full_metadata = self.base_extractor.extract_document_metadata(file_path)
            
            # Include basic properties if requested
            if force_full or profile.get('document_props'):
                for key in ['author', 'title', 'subject', 'keywords', 'category']:
                    if key in full_metadata:
                        metadata[key] = full_metadata[key]
            
        except Exception as e:
            logger.warning(f"Error extracting document metadata: {e}")
        
        return metadata
    
    def extract_batch(self, file_paths: list) -> list:
        """
        Extract metadata for multiple files efficiently.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            List of metadata dicts
        """
        return self.optimizer.process_files_batch(
            file_paths, 
            self.extract_metadata
        )


def create_optimized_extractor(config=None, performance_optimizer=None):
    """Create an optimized metadata extractor"""
    return OptimizedMetadataExtractor(config, performance_optimizer)


if __name__ == "__main__":
    # Test optimized extractor
    print("Testing Optimized Metadata Extractor...\n")
    
    class MockConfig:
        quantization_level = "balanced"
        processing_strategy = "batch"
        batch_size = 100
        max_workers = 4
        enable_metadata_cache = True
        cache_ttl_hours = 24
        cache_dir = ".cache/metadata"
        max_file_size_mb = 100
        timeout_seconds = 5
    
    extractor = OptimizedMetadataExtractor(MockConfig())
    
    print("Optimized Metadata Extractor initialized!")
    print(f"Quantization level: {extractor.optimizer.quantization_level}")
    print(f"Processing strategy: {extractor.optimizer.processing_strategy}")
    print(f"Cache enabled: {extractor.optimizer.enable_cache}")
    
    # Test quantization profiles
    print("\n" + "="*70)
    print("QUANTIZATION BEHAVIOR")
    print("="*70)
    
    for level in ["minimal", "balanced", "detailed", "maximum"]:
        print(f"\n{level.upper()}:")
        profile = extractor.optimizer.get_quantization_profile(level)
        print(f"  Image EXIF: date={profile.get('exif_date')}, "
              f"GPS={profile.get('exif_gps')}, camera={profile.get('exif_camera')}")
        print(f"  PDF: metadata={profile.get('pdf_metadata')}, "
              f"content={profile.get('pdf_content')}")
        print(f"  Audio: tags={profile.get('audio_tags')}, "
              f"bitrate={profile.get('audio_bitrate')}")
        print(f"  Target time: {profile['processing_time_ms']}ms/file")
