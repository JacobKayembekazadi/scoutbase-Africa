"""
SAM3 Configuration
==================
Environment-based configuration for SAM3 model loading and inference.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field


SAM3Variant = Literal["base", "large", "huge"]
SAM3Device = Literal["cuda", "cpu", "auto"]


@dataclass
class SAM3Config:
    """Configuration for SAM3 model and inference."""

    # HuggingFace authentication
    hf_token: Optional[str] = field(
        default_factory=lambda: os.getenv("HF_TOKEN")
    )

    # Model settings
    variant: SAM3Variant = field(
        default_factory=lambda: os.getenv("SAM3_VARIANT", "base")  # type: ignore
    )
    device: SAM3Device = field(
        default_factory=lambda: os.getenv("SAM3_DEVICE", "auto")  # type: ignore
    )

    # Paths
    checkpoint_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("SAM3_CHECKPOINT_DIR", "checkpoints")
        )
    )

    # Model loading
    lazy_load: bool = field(
        default_factory=lambda: os.getenv("SAM3_LAZY_LOAD", "true").lower() == "true"
    )
    offload_to_cpu: bool = field(
        default_factory=lambda: os.getenv("SAM3_OFFLOAD_CPU", "false").lower() == "true"
    )

    # Inference settings
    default_confidence: float = field(
        default_factory=lambda: float(os.getenv("SAM3_DEFAULT_CONFIDENCE", "0.5"))
    )
    max_objects_per_frame: int = field(
        default_factory=lambda: int(os.getenv("SAM3_MAX_OBJECTS", "50"))
    )

    # Performance
    use_flash_attention: bool = field(
        default_factory=lambda: os.getenv("SAM3_FLASH_ATTENTION", "false").lower() == "true"
    )
    compile_model: bool = field(
        default_factory=lambda: os.getenv("SAM3_COMPILE", "false").lower() == "true"
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure checkpoint directory exists
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Validate variant
        valid_variants = ("base", "large", "huge")
        if self.variant not in valid_variants:
            raise ValueError(
                f"Invalid SAM3 variant: {self.variant}. "
                f"Must be one of {valid_variants}"
            )

    @property
    def model_id(self) -> str:
        """Get the HuggingFace model ID based on variant."""
        # SAM3 model ID on HuggingFace - SAM3 supports text-prompted segmentation
        # All variants use the same model, different loading configurations
        model_map = {
            "base": "facebook/sam3",
            "large": "facebook/sam3",
            "huge": "facebook/sam3",
        }
        return model_map.get(self.variant, model_map["base"])

    @property
    def checkpoint_path(self) -> Path:
        """Get the local checkpoint path."""
        return self.checkpoint_dir / f"sam3_{self.variant}"

    @property
    def is_hf_authenticated(self) -> bool:
        """Check if HuggingFace authentication is configured."""
        return bool(self.hf_token)

    def get_device(self) -> str:
        """Resolve the compute device."""
        if self.device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return self.device


# Global config instance (lazy loaded)
_config: Optional[SAM3Config] = None


def get_config() -> SAM3Config:
    """Get the global SAM3 configuration instance."""
    global _config
    if _config is None:
        _config = SAM3Config()
    return _config


def reset_config():
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
