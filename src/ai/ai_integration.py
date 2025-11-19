"""AI Integration - Connects multi-model AI system to file organizer."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict

from .models.model_selector import ModelSelector
from .models.base import ModelTier, ClassificationResult

logger = logging.getLogger(__name__)


class AIOrganizer:
    """Main AI integration for file organization.

    Handles intelligent model selection and file classification.
    """

    def __init__(self, config: Dict[str, Any], user_tier: ModelTier = ModelTier.FREE):
        """Initialize AI organizer.

        Args:
            config: Configuration with API keys and settings
            user_tier: User's subscription tier
        """
        self.config = config
        self.user_tier = user_tier

        # Initialize model selector
        self.model_selector = ModelSelector(config)

        # Get available models info
        available_models = self.model_selector.get_available_models_info()
        logger.info(f"Initialized AI Organizer with {len(available_models)} models available")

        for model_info in available_models:
            logger.info(f"  - {model_info['name']} ({model_info['type']}, {model_info['tier']})")

    def classify_file(
        self,
        file_path: str,
        deep_analysis: bool = False,
        prefer_local: bool = True
    ) -> Dict[str, Any]:
        """Classify file using best available AI model.

        Args:
            file_path: Path to file
            deep_analysis: Use deeper analysis (more expensive)
            prefer_local: Prefer local models when possible

        Returns:
            Dict: Classification result compatible with old system
        """
        path = Path(file_path)

        # Read file content for deep analysis
        file_content = None
        if deep_analysis:
            file_content = self._read_file_content(path)

        # Get basic metadata
        metadata = self._get_file_metadata(path)

        # Classify using model selector
        result: ClassificationResult = self.model_selector.classify_with_best_model(
            file_path=str(path),
            user_tier=self.user_tier,
            file_content=file_content,
            metadata=metadata
        )

        # Log result
        logger.info(
            f"Classified {path.name}: {result.category} "
            f"(confidence: {result.confidence:.2f}, model: {result.model_used}, "
            f"cost: ${result.cost_usd:.6f}, time: {result.processing_time_ms}ms)"
        )

        # Convert to dict format compatible with old system
        return self._convert_to_legacy_format(result)

    def _read_file_content(self, path: Path) -> Optional[str]:
        """Read file content for text files.

        Args:
            path: File path

        Returns:
            Optional[str]: File content if readable
        """
        # Only read text files
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.java', '.cpp', '.c',
            '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs', '.swift',
            '.kt', '.scala', '.sh', '.bash', '.yml', '.yaml', '.json',
            '.xml', '.html', '.css', '.sql', '.log', '.csv'
        }

        if path.suffix.lower() not in text_extensions:
            return None

        try:
            # Read up to 10KB of content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10000)
            return content
        except Exception as e:
            logger.warning(f"Could not read {path.name}: {e}")
            return None

    def _get_file_metadata(self, path: Path) -> Dict[str, Any]:
        """Get file metadata.

        Args:
            path: File path

        Returns:
            Dict: Metadata
        """
        try:
            stat = path.stat()
            return {
                'size_bytes': stat.st_size,
                'modified_time': stat.st_mtime,
                'created_time': stat.st_ctime,
                'extension': path.suffix.lower()
            }
        except Exception as e:
            logger.warning(f"Could not get metadata for {path.name}: {e}")
            return {}

    def _convert_to_legacy_format(self, result: ClassificationResult) -> Dict[str, Any]:
        """Convert new ClassificationResult to legacy format.

        Args:
            result: Classification result from new system

        Returns:
            Dict: Legacy format classification
        """
        return {
            'category': result.category,
            'subcategory': result.subcategory,
            'confidence': result.confidence,
            'suggested_path': result.suggested_path,
            'suggested_name': result.suggested_name,
            'tags': result.tags,
            'summary': result.summary,
            'entities': result.entities,
            'reasoning': result.reasoning,
            # Additional fields for new system
            'model_used': result.model_used,
            'processing_time_ms': result.processing_time_ms,
            'tokens_used': result.tokens_used,
            'cost_usd': result.cost_usd
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get AI usage statistics.

        Returns:
            Dict: Statistics
        """
        available_models = self.model_selector.get_available_models_info()

        return {
            'user_tier': self.user_tier.value,
            'available_models': len(available_models),
            'models': available_models
        }

    def estimate_cost(self, num_files: int, avg_tokens: int = 500) -> float:
        """Estimate cost for organizing files.

        Args:
            num_files: Number of files to organize
            avg_tokens: Average tokens per file

        Returns:
            float: Estimated cost in USD
        """
        # Get the model that would be used
        model = self.model_selector.select_model(
            file_path="example.txt",  # Dummy path
            user_tier=self.user_tier
        )

        if not model:
            return 0.0

        # Estimate cost per file
        cost_per_file = model.get_cost_estimate(avg_tokens)

        # Total cost
        total_cost = cost_per_file * num_files * 2  # *2 for input + output

        logger.info(
            f"Cost estimate: {num_files} files × ${cost_per_file:.6f} × 2 = ${total_cost:.4f} "
            f"(model: {model.model_name})"
        )

        return total_cost
