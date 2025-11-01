"""
Hierarchical Folder Structure Manager

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module implements intelligent hierarchical folder organization based on
research-backed best practices. It creates purposeful, well-structured folder
hierarchies that optimize findability while minimizing cognitive load.

RESEARCH-BASED PRINCIPLES:
- Optimal depth: 3-4 levels maximum (backed by UX research)
- Cognitive load: Shallow hierarchies easier to navigate
- Discoverability: Each level should have clear purpose
- Consistency: Similar items organized similarly

HIERARCHY LEVELS:
Level 1: Primary Category (Documents, Work, Personal, Finance, etc.)
Level 2: Subcategory (Invoices, Projects, Photos, etc.)  
Level 3: Temporal/Contextual (2025, Q1, Client-Name, etc.)
Level 4: Specific Context (January, Project-Alpha, etc.) [Optional]

NOTICE: This software is proprietary and confidential.
See LICENSE.txt for full terms and conditions.

Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HierarchyLevel(Enum):
    """Hierarchy level definitions"""
    PRIMARY = 1      # Main category (Documents, Work, Media, etc.)
    SECONDARY = 2    # Subcategory (Invoices, Projects, Photos, etc.)
    TERTIARY = 3     # Temporal/Contextual (2025, ClientName, etc.)
    QUATERNARY = 4   # Specific context (Month, ProjectPhase, etc.)


class FolderPurpose(Enum):
    """Purpose types for folder organization"""
    CATEGORY = "category"          # Type-based (Documents, Images, etc.)
    TEMPORAL = "temporal"          # Time-based (2025, Q1, January, etc.)
    CONTEXTUAL = "contextual"      # Context-based (Client, Project, etc.)
    THEMATIC = "thematic"          # Theme-based (Personal, Work, etc.)


class HierarchicalOrganizer:
    """
    Intelligent folder hierarchy generator based on research best practices.
    
    Creates purposeful folder structures with optimal depth (3-4 levels)
    for maximum discoverability and minimal cognitive load.
    
    Research Sources:
    - Microsoft SharePoint IA Guidelines: Max 1-2 nested levels recommended
    - Azure Management Hierarchy: 3 levels optimal
    - UX Research: Shallow > Deep for navigation efficiency
    """
    
    # Primary categories (Level 1)
    PRIMARY_CATEGORIES = {
        # Work-related
        'work': {
            'keywords': ['work', 'job', 'office', 'business', 'corporate', 'professional'],
            'subcategories': ['projects', 'meetings', 'reports', 'presentations', 'contracts']
        },
        'documents': {
            'keywords': ['doc', 'document', 'text', 'file', 'paper'],
            'subcategories': ['legal', 'personal', 'reference', 'templates', 'forms']
        },
        'finance': {
            'keywords': ['finance', 'money', 'bank', 'tax', 'invoice', 'receipt', 'bill', 'payment'],
            'subcategories': ['invoices', 'receipts', 'taxes', 'statements', 'budgets']
        },
        'personal': {
            'keywords': ['personal', 'private', 'family', 'home'],
            'subcategories': ['health', 'education', 'travel', 'hobbies', 'family']
        },
        
        # Creative & Media
        'photos': {
            'keywords': ['photo', 'picture', 'image', 'jpg', 'jpeg', 'png'],
            'subcategories': ['events', 'travel', 'family', 'work', 'screenshots']
        },
        'videos': {
            'keywords': ['video', 'movie', 'film', 'mp4', 'avi', 'recording'],
            'subcategories': ['personal', 'tutorials', 'meetings', 'events', 'projects']
        },
        'music': {
            'keywords': ['music', 'audio', 'sound', 'mp3', 'song'],
            'subcategories': ['playlists', 'albums', 'podcasts', 'recordings']
        },
        'creative': {
            'keywords': ['design', 'art', 'creative', 'graphics', 'illustration'],
            'subcategories': ['designs', 'artwork', 'templates', 'resources', 'drafts']
        },
        
        # Technical
        'projects': {
            'keywords': ['project', 'code', 'development', 'programming'],
            'subcategories': ['active', 'archived', 'client-work', 'personal']
        },
        'downloads': {
            'keywords': ['download', 'temp', 'temporary'],
            'subcategories': ['installers', 'archives', 'temporary', 'to-sort']
        },
        'archives': {
            'keywords': ['archive', 'old', 'backup', 'historical'],
            'subcategories': ['2024', '2023', '2022', 'old-projects']
        }
    }
    
    # Temporal organization patterns (Level 3)
    TEMPORAL_PATTERNS = {
        'yearly': '{year}',              # 2025
        'quarterly': '{year}/Q{quarter}', # 2025/Q1
        'monthly': '{year}/{month}',      # 2025/January or 2025/01
        'weekly': '{year}/Week-{week}'    # 2025/Week-42
    }
    
    def __init__(self, config=None):
        """
        Initialize hierarchical organizer.
        
        Args:
            config: Configuration object with hierarchy preferences
        """
        self.config = config
        self.max_depth = getattr(config, 'max_hierarchy_depth', 4)
        self.preferred_depth = getattr(config, 'preferred_hierarchy_depth', 3)
        self.use_temporal = getattr(config, 'use_temporal_organization', True)
        self.temporal_pattern = getattr(config, 'temporal_pattern', 'yearly')
    
    def generate_hierarchy(self, 
                          filename: str,
                          extension: str,
                          file_metadata: Dict[str, Any],
                          classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate optimal folder hierarchy for a file.
        
        Args:
            filename: Name of the file
            extension: File extension
            file_metadata: File metadata (size, date, content preview, etc.)
            classification: AI classification result
            
        Returns:
            Dict with hierarchy structure:
                - full_path: Complete path string
                - levels: List of folder names by level
                - purposes: Purpose of each level
                - depth: Total depth
                - reasoning: Explanation of structure
        """
        hierarchy_levels = []
        purposes = []
        reasoning_parts = []
        
        # LEVEL 1: Primary Category
        primary, primary_reasoning = self._determine_primary_category(
            filename, extension, file_metadata, classification
        )
        hierarchy_levels.append(primary)
        purposes.append(FolderPurpose.CATEGORY)
        reasoning_parts.append(primary_reasoning)
        
        # LEVEL 2: Secondary Category/Subcategory
        secondary, secondary_reasoning = self._determine_secondary_category(
            primary, filename, extension, file_metadata, classification
        )
        if secondary:
            hierarchy_levels.append(secondary)
            purposes.append(FolderPurpose.CONTEXTUAL)
            reasoning_parts.append(secondary_reasoning)
        
        # LEVEL 3: Temporal or Contextual Organization
        if self.use_temporal and len(hierarchy_levels) < self.max_depth:
            tertiary, tertiary_reasoning = self._determine_tertiary_level(
                primary, secondary, filename, file_metadata, classification
            )
            if tertiary:
                hierarchy_levels.append(tertiary)
                purposes.append(FolderPurpose.TEMPORAL)
                reasoning_parts.append(tertiary_reasoning)
        
        # LEVEL 4: Specific Context (only if needed and beneficial)
        if len(hierarchy_levels) < self.preferred_depth:
            quaternary, quaternary_reasoning = self._determine_quaternary_level(
                primary, secondary, filename, file_metadata, classification
            )
            if quaternary:
                hierarchy_levels.append(quaternary)
                purposes.append(FolderPurpose.CONTEXTUAL)
                reasoning_parts.append(quaternary_reasoning)
        
        # Build final path
        full_path = str(Path(*hierarchy_levels))
        
        return {
            'full_path': full_path,
            'levels': hierarchy_levels,
            'purposes': [p.value for p in purposes],
            'depth': len(hierarchy_levels),
            'reasoning': ' → '.join(reasoning_parts),
            'primary_category': primary,
            'has_temporal': FolderPurpose.TEMPORAL in purposes,
            'is_optimal_depth': len(hierarchy_levels) in [3, 4]
        }
    
    def _determine_primary_category(self, filename: str, extension: str,
                                    _metadata: Dict, classification: Dict) -> Tuple[str, str]:
        """Determine Level 1: Primary category"""
        
        # Try AI classification first
        if classification.get('category'):
            ai_category = classification['category'].lower()
            
            # Map AI category to primary categories
            for primary, data in self.PRIMARY_CATEGORIES.items():
                if primary in ai_category or ai_category in primary:
                    return primary.title(), f"Primary: {primary.title()} (from AI)"
                
                # Check keywords
                for keyword in data['keywords']:
                    if keyword in ai_category or keyword in filename.lower():
                        return primary.title(), f"Primary: {primary.title()} (matched '{keyword}')"
        
        # Fallback to extension-based
        extension = extension.lower().lstrip('.')
        
        # Extension mappings
        ext_mappings = {
            ('pdf', 'doc', 'docx', 'txt', 'md', 'rtf', 'odt'): ('Documents', 'document files'),
            ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'): ('Photos', 'image files'),
            ('mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'): ('Videos', 'video files'),
            ('mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'): ('Music', 'audio files'),
            ('zip', 'rar', '7z', 'tar', 'gz'): ('Downloads', 'archive files'),
            ('py', 'js', 'java', 'cpp', 'html', 'css', 'php'): ('Projects', 'code files'),
            ('psd', 'ai', 'sketch', 'fig', 'xcf'): ('Creative', 'design files'),
            ('xlsx', 'xls', 'csv', 'ods'): ('Finance', 'spreadsheet files'),
            ('pptx', 'ppt', 'key', 'odp'): ('Work', 'presentation files'),
        }
        
        for exts, (category, reason) in ext_mappings.items():
            if extension in exts:
                return category, f"Primary: {category} (by {reason} .{extension})"
        
        return 'Documents', f"Primary: Documents (default for .{extension})"
    
    def _determine_secondary_category(self, primary: str, filename: str,
                                     _extension: str, _metadata: Dict,
                                     _classification: Dict) -> Tuple[Optional[str], str]:
        """Determine Level 2: Secondary category/subcategory"""
        
        primary_lower = primary.lower()
        filename_lower = filename.lower()
        
        # Get subcategories for this primary category
        if primary_lower in self.PRIMARY_CATEGORIES:
            subcats = self.PRIMARY_CATEGORIES[primary_lower].get('subcategories', [])
            
            # Check filename for subcategory keywords
            for subcat in subcats:
                if subcat in filename_lower or subcat.rstrip('s') in filename_lower:
                    return subcat.title(), f"Sub: {subcat.title()} (detected in filename)"
        
        # Pattern-based detection
        patterns = {
            r'invoice|bill|receipt': ('Invoices', 'financial documents'),
            r'report|analysis|summary': ('Reports', 'analytical documents'),
            r'presentation|slides|deck': ('Presentations', 'presentation files'),
            r'contract|agreement|nda': ('Contracts', 'legal documents'),
            r'screenshot|screen.shot|capture': ('Screenshots', 'screen captures'),
            r'meeting|minutes|notes': ('Meetings', 'meeting-related'),
            r'project|prj': ('Projects', 'project files'),
            r'template|boilerplate': ('Templates', 'template files'),
            r'draft|wip|work.in.progress': ('Drafts', 'draft documents'),
            r'travel|trip|vacation': ('Travel', 'travel-related'),
            r'tax|taxes|irs': ('Taxes', 'tax documents'),
            r'statement|bank|account': ('Statements', 'financial statements'),
        }
        
        for pattern, (subcat, reason) in patterns.items():
            if re.search(pattern, filename_lower):
                return subcat, f"Sub: {subcat} ({reason} detected)"
        
        # AI suggested subcategory
        ai_suggested = classification.get('suggested_path', '')
        if ai_suggested and '/' in ai_suggested:
            parts = ai_suggested.split('/')
            if len(parts) >= 2:
                return parts[1], f"Sub: {parts[1]} (from AI suggestion)"
        
        # Default subcategories by primary
        defaults = {
            'documents': 'General',
            'finance': 'Transactions',
            'work': 'General',
            'photos': 'Unsorted',
            'videos': 'Personal',
            'music': 'Library',
            'projects': 'Active',
            'downloads': 'Recent',
            'personal': 'General',
            'creative': 'Designs',
            'archives': 'Old-Files'
        }
        
        default = defaults.get(primary_lower, 'General')
        return default, f"Sub: {default} (default for {primary})"
    
    def _determine_tertiary_level(self, _primary: str, _secondary: Optional[str],
                                  filename: str, metadata: Dict,
                                  classification: Dict) -> Tuple[Optional[str], str]:
        """Determine Level 3: Usually temporal organization"""
        
        # Extract date from filename or metadata
        date_info = self._extract_date_info(filename, metadata)
        
        if not date_info:
            # If no date info, try context-based
            return self._extract_context(filename, classification)
        
        # Build temporal path based on pattern
        year = date_info.get('year')
        quarter = date_info.get('quarter')
        month = date_info.get('month')
        week = date_info.get('week')
        
        if self.temporal_pattern == 'quarterly' and quarter:
            return f"{year}/Q{quarter}", f"Temporal: {year}/Q{quarter} (quarterly)"
        elif self.temporal_pattern == 'monthly' and month:
            month_name = datetime(year, month, 1).strftime('%B')
            return f"{year}/{month_name}", f"Temporal: {year}/{month_name} (monthly)"
        elif self.temporal_pattern == 'weekly' and week:
            return f"{year}/Week-{week:02d}", f"Temporal: {year}/Week-{week:02d} (weekly)"
        elif year:
            return str(year), f"Temporal: {year} (yearly)"
        
        return None, ""
    
    def _determine_quaternary_level(self, primary: str, secondary: Optional[str],
                                   filename: str, metadata: Dict,
                                   classification: Dict) -> Tuple[Optional[str], str]:
        """Determine Level 4: Specific context (optional, only if valuable)"""
        
        # Only add 4th level if it significantly improves organization
        # Examples: Client name, Project name, Event name, etc.
        
        # Extract client/company name
        client = self._extract_client_name(filename, metadata, classification)
        if client:
            return client, f"Context: {client} (client/company)"
        
        # Extract project name
        project = self._extract_project_name(filename, metadata, classification)
        if project:
            return project, f"Context: {project} (project)"
        
        # Extract event name for photos/videos
        if primary.lower() in ['photos', 'videos']:
            event = self._extract_event_name(filename, metadata)
            if event:
                return event, f"Context: {event} (event)"
        
        # Month name if we used quarterly in level 3
        date_info = self._extract_date_info(filename, metadata)
        if date_info and date_info.get('month') and 'Q' in str(secondary or ''):
            month_name = datetime(date_info['year'], date_info['month'], 1).strftime('%B')
            return month_name, f"Context: {month_name} (month within quarter)"
        
        return None, ""
    
    def _extract_date_info(self, filename: str, metadata: Dict) -> Optional[Dict[str, int]]:
        """Extract date information from filename or metadata"""
        
        # Try filename patterns first
        # Pattern: YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD
        date_patterns = [
            r'(20\d{2})[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])',  # YYYY-MM-DD
            r'(20\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])',  # YYYYMMDD
            r'(0[1-9]|[12]\d|3[01])[-_]?(0[1-9]|1[0-2])[-_]?(20\d{2})',  # DD-MM-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # Determine order based on pattern
                    if pattern.startswith(r'(20\d{2})'):
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    
                    quarter = (month - 1) // 3 + 1
                    # Calculate week of year (approximate)
                    date_obj = datetime(year, month, day)
                    week = date_obj.isocalendar()[1]
                    
                    return {
                        'year': year,
                        'month': month,
                        'day': day,
                        'quarter': quarter,
                        'week': week
                    }
        
        # Try year-only pattern
        year_match = re.search(r'\b(202[0-9])\b', filename)
        if year_match:
            return {'year': int(year_match.group(1))}
        
        # Fall back to file modification date
        if 'modified_time' in metadata:
            from datetime import datetime as dt
            mod_time = dt.fromtimestamp(metadata['modified_time'])
            return {
                'year': mod_time.year,
                'month': mod_time.month,
                'day': mod_time.day,
                'quarter': (mod_time.month - 1) // 3 + 1,
                'week': mod_time.isocalendar()[1]
            }
        
        return None
    
    def _extract_context(self, filename: str, _classification: Dict) -> Tuple[Optional[str], str]:
        """Extract context-based organization from filename"""
        
        # Common context patterns
        contexts = {
            r'client[-_]([a-zA-Z0-9]+)': 'Client-{}',
            r'project[-_]([a-zA-Z0-9]+)': 'Project-{}',
            r'event[-_]([a-zA-Z0-9]+)': 'Event-{}',
        }
        
        filename_lower = filename.lower()
        for pattern, template in contexts.items():
            match = re.search(pattern, filename_lower)
            if match:
                context_name = match.group(1).title()
                return template.format(context_name), f"Context: {template.format(context_name)}"
        
        return None, ""
    
    def _extract_client_name(self, filename: str, _metadata: Dict,
                           _classification: Dict) -> Optional[str]:
        """Extract client/company name from filename or content"""
        
        # Pattern: Client-<Name>, <Name>-Invoice, etc.
        patterns = [
            r'(?:client|company|corp)[-_]([a-zA-Z0-9]+)',
            r'([A-Z][a-zA-Z]+(?:[A-Z][a-zA-Z]+)+)[-_](?:invoice|receipt|contract)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        return None
    
    def _extract_project_name(self, filename: str, _metadata: Dict,
                            _classification: Dict) -> Optional[str]:
        """Extract project name from filename"""
        
        patterns = [
            r'(?:project|prj)[-_]([a-zA-Z0-9]+)',
            r'([A-Z][a-zA-Z0-9]{2,})[-_](?:design|code|spec|docs)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return f"Project-{match.group(1).title()}"
        
        return None
    
    def _extract_event_name(self, filename: str, _metadata: Dict) -> Optional[str]:
        """Extract event name for photos/videos"""
        
        patterns = [
            r'(?:event|party|trip|vacation)[-_]([a-zA-Z0-9]+)',
            r'([a-zA-Z]+)[-_](?:trip|vacation|party)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        return None


if __name__ == "__main__":
    # Test hierarchical organizer
    import json
    
    class MockConfig:
        max_hierarchy_depth = 4
        preferred_hierarchy_depth = 3
        use_temporal_organization = True
        temporal_pattern = 'monthly'
    
    organizer = HierarchicalOrganizer(MockConfig())
    
    # Test Case 1: Invoice with date
    print("="*70)
    print("TEST 1: Invoice with date")
    print("="*70)
    result = organizer.generate_hierarchy(
        filename="invoice_ClientAcme_2025-03-15.pdf",
        extension="pdf",
        file_metadata={'modified_time': 1710547200},  # March 2025
        classification={'category': 'Finance', 'confidence': 'high'}
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 2: Photo without date
    print("\n" + "="*70)
    print("TEST 2: Photo without clear date")
    print("="*70)
    result = organizer.generate_hierarchy(
        filename="family_vacation_beach.jpg",
        extension="jpg",
        file_metadata={'modified_time': 1704067200},  # Jan 2024
        classification={'category': 'Photos', 'confidence': 'high'}
    )
    print(json.dumps(result, indent=2))
    
    # Test Case 3: Work presentation
    print("\n" + "="*70)
    print("TEST 3: Work presentation")
    print("="*70)
    result = organizer.generate_hierarchy(
        filename="Q4_2024_Sales_Report_Final.pptx",
        extension="pptx",
        file_metadata={'modified_time': 1704067200},
        classification={'category': 'Work', 'confidence': 'high'}
    )
    print(json.dumps(result, indent=2))
