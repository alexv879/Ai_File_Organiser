"""
Advanced configuration management using pydantic-settings.
Provides validated configuration loading from multiple sources.
Reference: Pydantic v2 settings management for application configuration
"""

import os
from pathlib import Path
from typing import List, Optional, Any, TYPE_CHECKING
from pydantic import BaseModel, Field
from pydantic import field_validator

# Pydantic-settings for configuration management
# Reference: pydantic-settings library for settings validation
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore
except ImportError:
    # Fallback for when pydantic-settings is not installed
    if TYPE_CHECKING:
        from pydantic_settings import BaseSettings, SettingsConfigDict
    else:
        BaseSettings = object  # type: ignore
        SettingsConfigDict = dict  # type: ignore


class FilterRule(BaseModel):
    """Advanced filter rule with validation."""
    name: str = Field(..., description="Filter name")
    type: str = Field(..., description="Filter type (size, date, pattern, mime, etc.)")
    condition: str = Field(..., description="Filter condition")
    value: Any = Field(..., description="Filter value")
    enabled: bool = Field(True, description="Whether filter is enabled")

    @field_validator('type')
    def validate_filter_type(cls, v):
        valid_types = ['size', 'date', 'pattern', 'mime', 'extension', 'exif', 'regex']
        if v not in valid_types:
            raise ValueError(f"Filter type must be one of {valid_types}")
        return v


class ActionRule(BaseModel):
    """Advanced action rule with validation."""
    name: str = Field(..., description="Action name")
    type: str = Field(..., description="Action type (move, copy, rename, delete, etc.)")
    target: str = Field(..., description="Action target path/pattern")
    template: Optional[str] = Field(None, description="Template for dynamic paths")
    conflict_resolution: str = Field("skip", description="How to handle conflicts")
    enabled: bool = Field(True, description="Whether action is enabled")

    @field_validator('type')
    def validate_action_type(cls, v):
        valid_types = ['move', 'copy', 'rename', 'delete', 'script', 'organize']
        if v not in valid_types:
            raise ValueError(f"Action type must be one of {valid_types}")
        return v

    @field_validator('conflict_resolution')
    def validate_conflict_resolution(cls, v):
        valid_resolutions = ['skip', 'overwrite', 'rename', 'error']
        if v not in valid_resolutions:
            raise ValueError(f"Conflict resolution must be one of {valid_resolutions}")
        return v


class AuthConfig(BaseModel):
    """Authentication configuration."""
    enabled: bool = Field(False, description="Enable authentication")
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Token expiration time")


class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = Field(True, description="Enable caching")
    directory: str = Field("./cache", description="Cache directory")
    size_limit: int = Field(int(1e9), description="Cache size limit in bytes")
    eviction_policy: str = Field("least-recently-used", description="Cache eviction policy")


class ParallelConfig(BaseModel):
    """Parallel processing configuration."""
    enabled: bool = Field(True, description="Enable parallel processing")
    max_workers: int = Field(4, description="Maximum worker threads")
    chunk_size: int = Field(100, description="Chunk size for batch operations")


class AdvancedConfig(BaseSettings):
    """Advanced configuration using pydantic-settings."""

    # Basic settings
    app_name: str = Field("AI File Organiser", description="Application name")
    version: str = Field("2.0.0", description="Application version")
    debug: bool = Field(False, description="Enable debug mode")

    # Paths
    base_directory: str = Field("./data", description="Base working directory")
    log_directory: str = Field("./logs", description="Log directory")
    config_directory: str = Field("./config", description="Configuration directory")

    # File organization rules
    filters: List[FilterRule] = Field(default_factory=list, description="File filter rules")
    actions: List[ActionRule] = Field(default_factory=list, description="File action rules")
    tags: List[str] = Field(default_factory=list, description="Available tags")

    # Advanced features
    auth: AuthConfig = Field(default_factory=lambda: AuthConfig(enabled=False, secret_key="", algorithm="HS256", access_token_expire_minutes=30), description="Authentication config")
    cache: CacheConfig = Field(default_factory=lambda: CacheConfig(enabled=True, directory="./cache", size_limit=int(1e9), eviction_policy="least-recently-used"), description="Cache configuration")
    parallel: ParallelConfig = Field(default_factory=lambda: ParallelConfig(enabled=True, max_workers=4, chunk_size=100), description="Parallel processing config")

    # Monitoring
    watch_directories: List[str] = Field(default_factory=lambda: ["./data"], description="Directories to watch")
    watch_patterns: List[str] = Field(default_factory=lambda: ["*"], description="File patterns to watch")

    # Performance
    batch_size: int = Field(1000, description="Batch size for operations")
    timeout: int = Field(300, description="Operation timeout in seconds")

    model_config = SettingsConfigDict(
        env_prefix='AIFO_',  # AI File Organiser prefix
        env_nested_delimiter='__',
        env_file='.env',
        env_file_encoding='utf-8',
        secrets_dir='/run/secrets',  # For Docker secrets
        json_file='config.json',
        yaml_file='config.yaml',
        toml_file='config.toml',
        pyproject_toml_table_header=('tool', 'ai-file-organiser'),
        extra='ignore',  # Ignore extra fields
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.base_directory,
            self.log_directory,
            self.config_directory,
            self.cache.directory
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def get_enabled_filters(self) -> List[FilterRule]:
        """Get all enabled filter rules."""
        return [f for f in self.filters if f.enabled]

    def get_enabled_actions(self) -> List[ActionRule]:
        """Get all enabled action rules."""
        return [a for a in self.actions if a.enabled]

    def get_filters_by_tag(self, tag: str) -> List[FilterRule]:
        """Get filters by tag (placeholder for future tag-based filtering)."""
        # For now, return all enabled filters
        # In the future, this could filter by tags
        return self.get_enabled_filters()

    def get_actions_by_tag(self, tag: str) -> List[ActionRule]:
        """Get actions by tag (placeholder for future tag-based filtering)."""
        # For now, return all enabled actions
        # In the future, this could filter by tags
        return self.get_enabled_actions()

    def validate_configuration(self) -> List[str]:
        """Validate the configuration and return any issues."""
        issues = []

        # Check directory permissions
        for directory in [self.base_directory, self.log_directory, self.config_directory]:
            path = Path(directory)
            if not path.exists():
                issues.append(f"Directory does not exist: {directory}")
            elif not os.access(path, os.R_OK | os.W_OK):
                issues.append(f"Insufficient permissions for directory: {directory}")

        # Check cache directory
        cache_path = Path(self.cache.directory)
        if not cache_path.exists():
            issues.append(f"Cache directory does not exist: {self.cache.directory}")
        elif not os.access(cache_path, os.R_OK | os.W_OK):
            issues.append(f"Insufficient permissions for cache directory: {self.cache.directory}")

        # Validate filter rules
        for i, filter_rule in enumerate(self.filters):
            if not filter_rule.name.strip():
                issues.append(f"Filter rule {i}: name cannot be empty")

        # Validate action rules
        for i, action_rule in enumerate(self.actions):
            if not action_rule.name.strip():
                issues.append(f"Action rule {i}: name cannot be empty")

        return issues

    def save_to_file(self, file_path: str, format: str = "yaml"):
        """Save configuration to file."""
        import yaml
        import json

        config_dict = self.model_dump()

        if format.lower() == "yaml":
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        elif format.lower() == "json":
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @classmethod
    def load_from_file(cls, file_path: str) -> "AdvancedConfig":
        """Load configuration from file."""
        import yaml
        import json

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        if file_path.endswith(('.yaml', '.yml')):
            with open(file_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        elif file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                config_dict = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        return cls(**config_dict)


# Global configuration instance
config = AdvancedConfig()