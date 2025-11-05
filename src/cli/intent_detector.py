"""
AI File Organiser - Intent Detection

Detects user intent from natural language queries.

Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.
"""

from typing import Dict, List, Tuple
import re


class IntentDetector:
    """Detects user intent from natural language"""

    # Intent patterns with keywords
    PATTERNS = {
        'space_management': [
            r'free up space',
            r'disk (is )?full',
            r'c:? drive',
            r'running out of space',
            r'low (on )?disk',
            r'clean up (my )?computer',
            r'need (more )?space',
            r'storage full'
        ],
        'organization': [
            r'organize',
            r'sort',
            r'clean up (my )?files',
            r'tidy up',
            r'arrange',
            r'categorize',
            r'mess',
            r'chaotic'
        ],
        'duplicates': [
            r'duplicate',
            r'copies',
            r'same file',
            r'multiple (copies|versions)',
            r'redundant',
            r'repeated files'
        ],
        'content_discovery': [
            r'find (my )?',
            r'search (for )?',
            r'locate',
            r'where (are|is)',
            r'show (me )?',
            r'list (my )?'
        ],
        'backup': [
            r'backup',
            r'important files',
            r'what should i (backup|save)',
            r'prepare (for )?backup'
        ],
        'migration': [
            r'move (to|from)',
            r'transfer',
            r'migrate',
            r'copy (to|from)',
            r'offload'
        ]
    }

    # Suggested actions for each intent
    ACTIONS = {
        'space_management': [
            {
                'description': 'Find and remove duplicate files (SAFEST)',
                'command': 'aifo space --duplicates',
                'impact': 'Often saves 1-5 GB'
            },
            {
                'description': 'Find large old files (>100MB, 6+ months old)',
                'command': 'aifo space --large-old',
                'impact': 'Review before deleting'
            },
            {
                'description': 'Analyze what\'s using space',
                'command': 'aifo space --analyze',
                'impact': 'Shows space breakdown'
            },
            {
                'description': 'Migrate files to another drive (if you have D: or external)',
                'command': 'aifo space --migrate D:',
                'impact': 'Moves user folders safely'
            }
        ],
        'organization': [
            {
                'description': 'Organize Downloads folder',
                'command': 'aifo organize',
                'impact': 'Sorts files into categories'
            },
            {
                'description': 'Organize specific folder',
                'command': 'aifo organize ~/Documents',
                'impact': 'Customizable path'
            },
            {
                'description': 'Preview organization first (dry run)',
                'command': 'aifo organize --preview',
                'impact': 'See plan before executing'
            },
            {
                'description': 'Deep AI analysis for better categories',
                'command': 'aifo organize --deep',
                'impact': 'Slower but more accurate'
            }
        ],
        'duplicates': [
            {
                'description': 'Find duplicate files',
                'command': 'aifo find',
                'impact': 'Shows duplicates and wasted space'
            },
            {
                'description': 'Find and delete duplicates (keeps newest)',
                'command': 'aifo find --delete',
                'impact': 'Frees space automatically'
            },
            {
                'description': 'Find only large duplicates (>10MB)',
                'command': 'aifo find --min-size 10MB',
                'impact': 'Focus on big files'
            }
        ],
        'content_discovery': [
            {
                'description': 'Scan folder and show file types',
                'command': 'aifo scan',
                'impact': 'Quick inventory'
            },
            {
                'description': 'Detailed breakdown by file type',
                'command': 'aifo scan --detailed',
                'impact': 'See exactly what you have'
            }
        ],
        'backup': [
            {
                'description': 'Scan important folders',
                'command': 'aifo scan ~/Documents',
                'impact': 'See what needs backup'
            },
            {
                'description': 'Find duplicates first (no need to backup duplicates)',
                'command': 'aifo find',
                'impact': 'Reduce backup size'
            }
        ],
        'migration': [
            {
                'description': 'Migrate to D: drive',
                'command': 'aifo space --migrate D:',
                'impact': 'Moves Documents, Pictures, Videos, Downloads'
            },
            {
                'description': 'See what will be migrated (preview)',
                'command': 'aifo space --analyze',
                'impact': 'Shows folder sizes'
            }
        ]
    }

    def detect(self, query: str) -> Tuple[str, float]:
        """
        Detect intent from query

        Args:
            query: User's natural language query

        Returns:
            Tuple of (intent, confidence)
        """
        query_lower = query.lower()
        scores = {}

        for intent, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1

            if score > 0:
                scores[intent] = score

        if not scores:
            return 'unknown', 0.0

        # Get intent with highest score
        best_intent = max(scores.items(), key=lambda x: x[1])
        intent, score = best_intent

        # Calculate confidence (normalize to 0-1)
        max_possible = len(self.PATTERNS[intent])
        confidence = min(score / max_possible, 1.0)

        return intent, confidence

    def get_suggestions(self, intent: str) -> List[Dict]:
        """
        Get suggested actions for intent

        Args:
            intent: Detected intent

        Returns:
            List of action dictionaries
        """
        return self.ACTIONS.get(intent, [])

    def detect_and_suggest(self, query: str) -> Dict:
        """
        Detect intent and return suggestions

        Args:
            query: User's natural language query

        Returns:
            Dict with intent, confidence, and suggestions
        """
        intent, confidence = self.detect(query)

        return {
            'query': query,
            'intent': intent,
            'confidence': confidence,
            'suggestions': self.get_suggestions(intent)
        }

    def format_intent_name(self, intent: str) -> str:
        """Format intent name for display"""
        names = {
            'space_management': 'Space Management',
            'organization': 'File Organization',
            'duplicates': 'Duplicate Cleanup',
            'content_discovery': 'Content Discovery',
            'backup': 'Backup Preparation',
            'migration': 'File Migration',
            'unknown': 'Unknown Intent'
        }
        return names.get(intent, intent.title())
