"""Intelligent model selection based on file type, complexity, and user tier."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

from .base import AIModel, ClassificationResult, ModelTier
from .ollama_model import OllamaModel
from .openai_model import OpenAIModel
from .claude_model import ClaudeModel

logger = logging.getLogger(__name__)


class FileComplexity(Enum):
    """File complexity levels."""
    SIMPLE = "simple"      # Extension-based categorization sufficient
    MEDIUM = "medium"      # Needs basic AI analysis
    COMPLEX = "complex"    # Requires advanced AI reasoning


class ModelSelector:
    """Intelligently selects the best AI model for file classification.

    Strategy:
    1. Use local models (Ollama) for simple files and FREE tier users
    2. Use fast cloud models (GPT-3.5, Claude Haiku) for medium complexity
    3. Use advanced models (GPT-4, Claude Sonnet) for complex files
    4. Consider user's subscription tier
    5. Fallback to simpler models if advanced unavailable
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize model selector.

        Args:
            config: Configuration with API keys and settings
        """
        self.config = config
        self.available_models: List[AIModel] = []

        # Initialize available models
        self._init_models()

    def _init_models(self):
        """Initialize all available models."""
        # Local Ollama (always try to initialize)
        try:
            ollama = OllamaModel(
                model=self.config.get("ollama_model", "qwen2.5:7b-instruct"),
                base_url=self.config.get("ollama_base_url", "http://localhost:11434")
            )
            if ollama.is_available():
                self.available_models.append(ollama)
                logger.info("Ollama model available")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")

        # OpenAI GPT models
        if self.config.get("openai_api_key"):
            try:
                # GPT-4 Turbo (advanced)
                gpt4_turbo = OpenAIModel(
                    api_key=self.config["openai_api_key"],
                    model="gpt-4-turbo"
                )
                if gpt4_turbo.is_available():
                    self.available_models.append(gpt4_turbo)
                    logger.info("GPT-4 Turbo available")

                # GPT-3.5 Turbo (fast/cheap)
                gpt35 = OpenAIModel(
                    api_key=self.config["openai_api_key"],
                    model="gpt-3.5-turbo"
                )
                if gpt35.is_available():
                    self.available_models.append(gpt35)
                    logger.info("GPT-3.5 Turbo available")

            except Exception as e:
                logger.warning(f"OpenAI models not available: {e}")

        # Anthropic Claude models
        if self.config.get("anthropic_api_key"):
            try:
                # Claude 3.5 Sonnet (advanced)
                claude_sonnet = ClaudeModel(
                    api_key=self.config["anthropic_api_key"],
                    model="claude-3-5-sonnet-20250122"
                )
                if claude_sonnet.is_available():
                    self.available_models.append(claude_sonnet)
                    logger.info("Claude 3.5 Sonnet available")

                # Claude Haiku (fast/cheap)
                claude_haiku = ClaudeModel(
                    api_key=self.config["anthropic_api_key"],
                    model="claude-3-haiku-20240307"
                )
                if claude_haiku.is_available():
                    self.available_models.append(claude_haiku)
                    logger.info("Claude Haiku available")

            except Exception as e:
                logger.warning(f"Claude models not available: {e}")

    def assess_file_complexity(
        self,
        file_path: str,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileComplexity:
        """Assess file complexity to determine required model sophistication.

        Args:
            file_path: Path to file
            file_content: Optional file content
            metadata: Optional metadata

        Returns:
            FileComplexity: Complexity assessment
        """
        filename = Path(file_path).name
        extension = Path(file_path).suffix.lower()

        # SIMPLE: Clear extension, no content analysis needed
        simple_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',  # Images
            '.mp4', '.avi', '.mkv', '.mov',           # Videos
            '.mp3', '.wav', '.flac',                  # Audio
            '.zip', '.rar', '.7z', '.tar', '.gz'      # Archives
        }

        if extension in simple_extensions:
            return FileComplexity.SIMPLE

        # COMPLEX: Requires deep understanding
        complex_indicators = [
            # Legal/financial documents
            'contract', 'agreement', 'invoice', 'receipt', 'legal',
            # Technical documents
            'specification', 'requirements', 'design', 'architecture',
            # Code with documentation
            'README', 'LICENSE', 'CHANGELOG',
        ]

        if any(indicator in filename.lower() for indicator in complex_indicators):
            return FileComplexity.COMPLEX

        # COMPLEX: Has substantial content to analyze
        if file_content and len(file_content) > 1000:
            return FileComplexity.COMPLEX

        # MEDIUM: Everything else
        return FileComplexity.MEDIUM

    def select_model(
        self,
        file_path: str,
        user_tier: ModelTier = ModelTier.FREE,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        prefer_local: bool = True
    ) -> Optional[AIModel]:
        """Select the best model for file classification.

        Args:
            file_path: Path to file
            user_tier: User's subscription tier
            file_content: Optional file content
            metadata: Optional metadata
            prefer_local: Prefer local models when possible

        Returns:
            Optional[AIModel]: Selected model or None if none available
        """
        complexity = self.assess_file_complexity(file_path, file_content, metadata)

        logger.info(f"File complexity: {complexity.value}, User tier: {user_tier.value}")

        # Strategy based on complexity and tier
        if complexity == FileComplexity.SIMPLE:
            # Simple files: Use fastest available model
            return self._get_fastest_model(user_tier)

        elif complexity == FileComplexity.MEDIUM:
            # Medium complexity: Balance speed and accuracy
            if user_tier == ModelTier.FREE:
                # Free tier: Use local only
                return self._get_model_by_name("ollama")

            elif user_tier in [ModelTier.STARTER, ModelTier.PRO]:
                # Paid tiers: Use fast cloud models
                if prefer_local and self._has_local_model():
                    return self._get_model_by_name("ollama")
                else:
                    return self._get_model_by_name("gpt-3.5-turbo") or \
                           self._get_model_by_name("claude-haiku") or \
                           self._get_model_by_name("ollama")

        else:  # COMPLEX
            # Complex files: Use most capable model for user's tier
            if user_tier == ModelTier.FREE:
                # Free tier: Best local model
                return self._get_model_by_name("ollama")

            elif user_tier == ModelTier.PRO:
                # Pro tier: Advanced models
                return self._get_model_by_name("gpt-4-turbo") or \
                       self._get_model_by_name("claude-3-5-sonnet") or \
                       self._get_model_by_name("gpt-3.5-turbo") or \
                       self._get_model_by_name("ollama")

            else:  # STARTER
                # Starter tier: Medium cloud models
                return self._get_model_by_name("gpt-3.5-turbo") or \
                       self._get_model_by_name("claude-haiku") or \
                       self._get_model_by_name("ollama")

        # Fallback: Any available model
        return self.available_models[0] if self.available_models else None

    def classify_with_best_model(
        self,
        file_path: str,
        user_tier: ModelTier = ModelTier.FREE,
        file_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ClassificationResult:
        """Classify file using the best available model.

        Args:
            file_path: Path to file
            user_tier: User's subscription tier
            file_content: Optional file content
            metadata: Optional metadata

        Returns:
            ClassificationResult: Classification result
        """
        model = self.select_model(file_path, user_tier, file_content, metadata)

        if not model:
            logger.error("No AI models available for classification")
            return ClassificationResult(
                category="Uncategorized",
                confidence=0.0,
                model_used="none"
            )

        logger.info(f"Using model: {model.model_name} for {Path(file_path).name}")

        return model.classify_file(file_path, file_content, metadata)

    def _get_fastest_model(self, user_tier: ModelTier) -> Optional[AIModel]:
        """Get fastest available model."""
        # Local is fastest
        if self._has_local_model():
            return self._get_model_by_name("ollama")

        # Then fast cloud models
        if user_tier != ModelTier.FREE:
            return self._get_model_by_name("claude-haiku") or \
                   self._get_model_by_name("gpt-3.5-turbo")

        return None

    def _has_local_model(self) -> bool:
        """Check if local model is available."""
        return any(m.model_type.value == "local" for m in self.available_models)

    def _get_model_by_name(self, name_fragment: str) -> Optional[AIModel]:
        """Get model by name fragment."""
        for model in self.available_models:
            if name_fragment.lower() in model.model_name.lower():
                return model
        return None

    def get_available_models_info(self) -> List[Dict[str, Any]]:
        """Get information about all available models.

        Returns:
            List[Dict]: List of model information
        """
        return [model.get_info() for model in self.available_models]
