"""Base classes for AI models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ModelType(Enum):
    """AI model types."""
    LOCAL = "local"      # Ollama, local inference
    CLOUD = "cloud"      # OpenAI, Claude, etc.
    HYBRID = "hybrid"    # Use both based on complexity


class ModelTier(Enum):
    """Model capability tiers for pricing."""
    FREE = "free"              # Local models only
    STARTER = "starter"        # Basic cloud models
    PRO = "pro"                # Advanced models (GPT-4, Claude)
    ENTERPRISE = "enterprise"  # Custom fine-tuned models


@dataclass
class ClassificationResult:
    """Result from AI file classification."""

    category: str                      # Primary category (e.g., "Documents", "Photos")
    subcategory: Optional[str] = None  # Subcategory (e.g., "Contracts", "Family Photos")
    confidence: float = 0.0            # Confidence score 0-1
    suggested_path: str = ""           # Suggested file path
    suggested_name: Optional[str] = None  # Suggested renamed filename
    tags: list[str] = None             # Extracted tags
    summary: Optional[str] = None      # Brief content summary
    entities: Dict[str, Any] = None    # Extracted entities (dates, names, etc.)
    reasoning: Optional[str] = None    # Model's reasoning (for transparency)
    model_used: str = ""               # Which model was used
    processing_time_ms: int = 0        # Processing time in milliseconds
    tokens_used: int = 0               # Tokens used (for cloud models)
    cost_usd: float = 0.0              # Estimated cost in USD

    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
        if self.entities is None:
            self.entities = {}


class AIModel(ABC):
    """Abstract base class for AI models."""

    def __init__(self, model_name: str, config: Dict[str, Any] = None):
        """Initialize AI model.

        Args:
            model_name: Name/identifier of the model
            config: Model-specific configuration
        """
        self.model_name = model_name
        self.config = config or {}
        self.model_type = ModelType.LOCAL
        self.model_tier = ModelTier.FREE

    @abstractmethod
    def is_available(self) -> bool:
        """Check if model is available/accessible.

        Returns:
            bool: True if model can be used
        """
        pass

    @abstractmethod
    def classify_file(
        self,
        file_path: str,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify a file.

        Args:
            file_path: Path to the file
            file_content: Optional file content (text)
            metadata: Optional file metadata

        Returns:
            ClassificationResult: Classification result
        """
        pass

    @abstractmethod
    def get_cost_estimate(self, input_tokens: int) -> float:
        """Estimate cost for processing tokens.

        Args:
            input_tokens: Number of input tokens

        Returns:
            float: Estimated cost in USD
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get model information.

        Returns:
            Dict: Model information
        """
        return {
            "name": self.model_name,
            "type": self.model_type.value,
            "tier": self.model_tier.value,
            "available": self.is_available(),
            "config": self.config
        }
