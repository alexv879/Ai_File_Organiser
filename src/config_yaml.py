"""
YAML Configuration System for AI File Organiser

Copyright (c) 2025 Alexandru Emanuel Vasile. All rights reserved.
Proprietary Software - 200-Key Limited Release License

This module provides advanced YAML-based configuration with rule-based file organization,
advanced filtering, and flexible action definitions.

NOTICE: This software is proprietary and confidential. Unauthorized copying,
modification, distribution, or use is strictly prohibited.
See LICENSE.txt for full terms and conditions.

Version: 1.0.0
Author: Alexandru Emanuel Vasile
License: Proprietary (200-key limited release)
"""

import yaml
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Pattern
from datetime import datetime, timedelta
from dataclasses import dataclass
import mimetypes
from fnmatch import fnmatch
 


@dataclass
class FilterRule:
    """Advanced filter rule with multiple criteria."""
    name: str
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    date_modified_after: Optional[datetime] = None
    date_modified_before: Optional[datetime] = None
    date_created_after: Optional[datetime] = None
    date_created_before: Optional[datetime] = None
    patterns: Optional[List[str]] = None
    regex_patterns: Optional[List[Pattern]] = None
    mime_types: Optional[List[str]] = None
    extensions: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    exclude_regex: Optional[List[Pattern]] = None

    def matches(self, file_path: Path, file_stat: Optional[os.stat_result] = None) -> bool:
        """Check if file matches this filter rule."""
        if file_stat is None:
            try:
                file_stat = file_path.stat()
            except OSError:
                return False

        # Size filters
        if self.size_min and file_stat.st_size < self.size_min:
            return False
        if self.size_max and file_stat.st_size > self.size_max:
            return False

        # Date filters - Extract modification and creation timestamps
        # Use st_mtime for modification time (POSIX standard)
        mtime = datetime.fromtimestamp(file_stat.st_mtime)
        # Use st_birthtime (macOS/BSD) or fallback to st_ctime (Unix) for creation time
        # Reference: IEEE Std 1003.1-2008 (POSIX.1-2008) for file timestamps
        ctime = datetime.fromtimestamp(getattr(file_stat, 'st_birthtime', getattr(file_stat, 'st_ctime', file_stat.st_mtime)))

        if self.date_modified_after and mtime < self.date_modified_after:
            return False
        if self.date_modified_before and mtime > self.date_modified_before:
            return False
        if self.date_created_after and ctime < self.date_created_after:
            return False
        if self.date_created_before and ctime > self.date_created_before:
            return False

        # Pattern matching
        filename = file_path.name
        filepath_str = str(file_path)

        # Include patterns
        if self.patterns:
            if not any(fnmatch(filename, p) for p in self.patterns):
                return False

        if self.regex_patterns:
            if not any(p.search(filepath_str) for p in self.regex_patterns):
                return False

        # Exclude patterns
        if self.exclude_patterns:
            if any(fnmatch(filename, p) for p in self.exclude_patterns):
                return False

        if self.exclude_regex:
            if any(p.search(filepath_str) for p in self.exclude_regex):
                return False

        # MIME type filtering
        if self.mime_types:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type not in self.mime_types:
                return False

        # Extension filtering
        if self.extensions:
            if file_path.suffix.lower() not in [ext.lower() for ext in self.extensions]:
                return False

        return True


@dataclass
class ActionRule:
    """Action rule with templating and conflict resolution."""
    name: str
    action: str  # 'move', 'copy', 'delete', 'rename', 'script'
    destination: Optional[str] = None
    template: Optional[str] = None
    script: Optional[str] = None
    conflict_resolution: str = 'rename'  # 'rename', 'overwrite', 'skip'
    tags: Optional[List[str]] = None

    def execute(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action with given context."""
        if self.action == 'script' and self.script:
            return self._execute_script(file_path, context)
        elif self.action == 'move':
            return self._execute_move(file_path, context)
        elif self.action == 'copy':
            return self._execute_copy(file_path, context)
        elif self.action == 'delete':
            return self._execute_delete(file_path, context)
        elif self.action == 'rename':
            return self._execute_rename(file_path, context)

        return {'success': False, 'error': f'Unknown action: {self.action}'}

    def _execute_move(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute move action with templating."""
        dest_path = self._resolve_template(self.destination or self.template, context)
        if not dest_path:
            return {'success': False, 'error': 'No destination specified'}

        dest_file = Path(dest_path)
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        # Handle conflicts
        if dest_file.exists() and self.conflict_resolution == 'rename':
            counter = 1
            stem = dest_file.stem
            suffix = dest_file.suffix
            while dest_file.exists():
                dest_file = dest_file.parent / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            file_path.rename(dest_file)
            return {
                'success': True,
                'action': 'move',
                'from': str(file_path),
                'to': str(dest_file)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_copy(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute copy action."""
        dest_path = self._resolve_template(self.destination or self.template, context)
        if not dest_path:
            return {'success': False, 'error': 'No destination specified'}

        dest_file = Path(dest_path)
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            import shutil
            shutil.copy2(file_path, dest_file)
            return {
                'success': True,
                'action': 'copy',
                'from': str(file_path),
                'to': str(dest_file)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_delete(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delete action."""
        try:
            file_path.unlink()
            return {
                'success': True,
                'action': 'delete',
                'file': str(file_path)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_rename(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rename action."""
        new_name = self._resolve_template(self.template, context)
        if not new_name:
            return {'success': False, 'error': 'No template specified'}

        dest_file = file_path.parent / new_name

        try:
            file_path.rename(dest_file)
            return {
                'success': True,
                'action': 'rename',
                'from': str(file_path),
                'to': str(dest_file)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_script(self, file_path: Path, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python script action."""
        if not self.script:
            return {'success': False, 'error': 'No script specified'}

        try:
            # Create execution context
            script_context = {
                'file_path': file_path,
                'file_name': file_path.name,
                'file_stem': file_path.stem,
                'file_suffix': file_path.suffix,
                'file_size': file_path.stat().st_size,
                'file_mtime': datetime.fromtimestamp(file_path.stat().st_mtime),
                **context
            }

            # Execute script (in controlled environment)
            exec(self.script, {'__builtins__': {}}, script_context)

            return {
                'success': True,
                'action': 'script',
                'file': str(file_path)
            }
        except Exception as e:
            return {'success': False, 'error': f'Script execution failed: {str(e)}'}

    def _resolve_template(self, template: Optional[str], context: Dict[str, Any]) -> Optional[str]:
        """Resolve template string with context variables."""
        if not template:
            return None

        result = template
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if isinstance(value, datetime):
                value = value.strftime("%Y%m%d_%H%M%S")
            result = result.replace(placeholder, str(value))

        return result


class YAMLConfig:
    """
    YAML-based configuration system with advanced rules and filtering.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize YAML configuration.

        Args:
            config_path (str, optional): Path to YAML config file
        """
        if config_path is None:
            self.config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            self.config_path = Path(config_path)

        self._config: Dict[str, Any] = {}
        self._rules: List[Dict[str, Any]] = []
        self._filters: Dict[str, FilterRule] = {}
        self._actions: Dict[str, ActionRule] = {}

        self.load()

    def load(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            self._create_default_config()
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}

            self._parse_rules()
            self._parse_filters()
            self._parse_actions()

        except Exception as e:
            raise ValueError(f"Failed to load YAML config: {e}")

    def _create_default_config(self) -> None:
        """Create default YAML configuration."""
        default_config = {
            'version': '1.0',
            'settings': {
                'watched_folders': ['~/Desktop', '~/Downloads'],
                'base_destination': '~/Documents',
                'auto_mode': False,
                'dry_run': True,
                'parallel_processing': True,
                'max_workers': 4
            },
            'filters': {
                'large_files': {
                    'size_min': 104857600  # 100MB
                },
                'recent_files': {
                    'date_modified_after': '2024-01-01'
                },
                'documents': {
                    'extensions': ['.pdf', '.docx', '.txt'],
                    'mime_types': ['application/pdf', 'application/msword']
                }
            },
            'actions': {
                'organize_documents': {
                    'action': 'move',
                    'destination': '{base_destination}/Documents/{file_stem}{file_suffix}',
                    'conflict_resolution': 'rename'
                },
                'archive_large': {
                    'action': 'move',
                    'destination': '{base_destination}/Archive/{file_name}',
                    'conflict_resolution': 'rename'
                }
            },
            'rules': [
                {
                    'name': 'Document Organization',
                    'filters': ['documents'],
                    'actions': ['organize_documents'],
                    'tags': ['documents', 'auto']
                },
                {
                    'name': 'Large File Archive',
                    'filters': ['large_files'],
                    'actions': ['archive_large'],
                    'tags': ['archive', 'large_files']
                }
            ]
        }

        self._config = default_config
        self.save()

    def _parse_filters(self) -> None:
        """Parse filter definitions from config."""
        filters_config = self._config.get('filters', {})

        for filter_name, filter_config in filters_config.items():
            self._filters[filter_name] = self._parse_filter_rule(filter_name, filter_config)

    def _parse_filter_rule(self, name: str, config: Dict[str, Any]) -> FilterRule:
        """Parse individual filter rule."""
        # Parse date strings
        date_fields = ['date_modified_after', 'date_modified_before',
                      'date_created_after', 'date_created_before']

        parsed_config = {}
        for key, value in config.items():
            if key in date_fields and isinstance(value, str):
                try:
                    parsed_config[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    # Try relative dates like "7 days ago"
                    if 'days ago' in value:
                        days = int(value.split()[0])
                        parsed_config[key] = datetime.now() - timedelta(days=days)
                    else:
                        parsed_config[key] = None
            elif key in ['regex_patterns', 'exclude_regex']:
                if isinstance(value, list):
                    parsed_config[key] = [re.compile(p) for p in value]
                else:
                    parsed_config[key] = [re.compile(str(value))]
            else:
                parsed_config[key] = value

        return FilterRule(name=name, **parsed_config)

    def _parse_actions(self) -> None:
        """Parse action definitions from config."""
        actions_config = self._config.get('actions', {})

        for action_name, action_config in actions_config.items():
            self._actions[action_name] = ActionRule(name=action_name, **action_config)

    def _parse_rules(self) -> None:
        """Parse organization rules from config."""
        self._rules = self._config.get('rules', [])

    def get_matching_rules(self, file_path: Path, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get rules that match the given file and optional tags."""
        matching_rules = []

        for rule in self._rules:
            # Check tags if specified
            if tags and not self._rule_matches_tags(rule, tags):
                continue

            # Check filters
            if self._rule_matches_file(rule, file_path):
                matching_rules.append(rule)

        return matching_rules

    def _rule_matches_tags(self, rule: Dict[str, Any], tags: List[str]) -> bool:
        """Check if rule matches any of the specified tags."""
        rule_tags = rule.get('tags', [])
        return any(tag in rule_tags for tag in tags)

    def _rule_matches_file(self, rule: Dict[str, Any], file_path: Path) -> bool:
        """Check if rule's filters match the file."""
        filter_names = rule.get('filters', [])

        # If no filters specified, rule matches all files
        if not filter_names:
            return True

        # All specified filters must match
        for filter_name in filter_names:
            if filter_name not in self._filters:
                continue

            filter_rule = self._filters[filter_name]
            if not filter_rule.matches(file_path):
                return False

        return True

    def execute_rules(self, file_path: Path, tags: Optional[List[str]] = None,
                     dry_run: bool = True) -> List[Dict[str, Any]]:
        """Execute matching rules for a file."""
        results = []
        matching_rules = self.get_matching_rules(file_path, tags)

        for rule in matching_rules:
            rule_result = self._execute_rule(rule, file_path, dry_run)
            results.append({
                'rule': rule['name'],
                'success': rule_result['success'],
                'actions': rule_result.get('actions', []),
                'errors': rule_result.get('errors', [])
            })

        return results

    def _execute_rule(self, rule: Dict[str, Any], file_path: Path, dry_run: bool) -> Dict[str, Any]:
        """Execute a single rule."""
        actions = rule.get('actions', [])
        results = {'success': True, 'actions': [], 'errors': []}

        # Build context for templating
        context = self._build_context(file_path)

        for action_name in actions:
            if action_name not in self._actions:
                results['errors'].append(f'Unknown action: {action_name}')
                results['success'] = False
                continue

            action_rule = self._actions[action_name]

            if not dry_run:
                result = action_rule.execute(file_path, context)
            else:
                result = {
                    'success': True,
                    'action': action_rule.action,
                    'dry_run': True,
                    'template': action_rule.destination or action_rule.template
                }

            results['actions'].append(result)

            if not result['success']:
                results['success'] = False
                results['errors'].append(result.get('error', 'Unknown error'))

        return results

    def _build_context(self, file_path: Path) -> Dict[str, Any]:
        """Build context dictionary for template resolution."""
        stat = file_path.stat()

        return {
            'file_name': file_path.name,
            'file_stem': file_path.stem,
            'file_suffix': file_path.suffix,
            'file_size': stat.st_size,
            'file_mtime': datetime.fromtimestamp(stat.st_mtime),
            'file_ctime': datetime.fromtimestamp(getattr(stat, 'st_birthtime', getattr(stat, 'st_ctime', stat.st_mtime))),
            'base_destination': self.get('settings.base_destination', str(Path.home())),
            'year': datetime.now().year,
            'month': datetime.now().month,
            'day': datetime.now().day
        }

    def execute_rules_by_tags(self, file_path: Path, tags: List[str],
                             dry_run: bool = True) -> List[Dict[str, Any]]:
        """
        Execute rules that match the specified tags.

        Args:
            file_path: File to process
            tags: List of tags to match
            dry_run: If True, simulate execution

        Returns:
            List of execution results
        """
        return self.execute_rules(file_path, tags, dry_run)

    def execute_script_action(self, script: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Python script action.

        Args:
            script: Python script to execute
            context: Context variables available to the script

        Returns:
            Execution result
        """
        try:
            # Create a restricted execution environment
            exec_globals = {
                '__builtins__': {
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'sorted': sorted,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'abs': abs,
                    'round': round,
                    'print': print,
                }
            }

            # Add context variables
            exec_globals.update(context)

            # Execute the script
            exec(script, exec_globals)

            return {
                'success': True,
                'action': 'script',
                'message': 'Script executed successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'action': 'script',
                'error': f'Script execution failed: {str(e)}'
            }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key."""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def save(self) -> None:
        """Save configuration to YAML file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    def add_rule(self, rule: Dict[str, Any]) -> None:
        """Add a new organization rule."""
        self._rules.append(rule)
        self._config['rules'] = self._rules
        self.save()

    def add_filter(self, name: str, filter_config: Dict[str, Any]) -> None:
        """Add a new filter rule."""
        if 'filters' not in self._config:
            self._config['filters'] = {}

        self._config['filters'][name] = filter_config
        self._filters[name] = self._parse_filter_rule(name, filter_config)
        self.save()

    def add_action(self, name: str, action_config: Dict[str, Any]) -> None:
        """Add a new action rule."""
        if 'actions' not in self._config:
            self._config['actions'] = {}

        self._config['actions'][name] = action_config
        self._actions[name] = ActionRule(name=name, **action_config)
        self.save()


# Global YAML configuration instance
_yaml_config_instance: Optional[YAMLConfig] = None


def get_yaml_config(config_path: Optional[str] = None) -> YAMLConfig:
    """Get or create global YAML configuration instance."""
    global _yaml_config_instance
    if _yaml_config_instance is None:
        _yaml_config_instance = YAMLConfig(config_path)
    return _yaml_config_instance


if __name__ == "__main__":
    # Test YAML configuration
    config = get_yaml_config()
    print("YAML configuration loaded successfully!")

    # Test with a sample file
    test_file = Path(__file__)
    rules = config.get_matching_rules(test_file)
    print(f"Matching rules for {test_file.name}: {len(rules)}")

    for rule in rules:
        print(f"  - {rule['name']}")