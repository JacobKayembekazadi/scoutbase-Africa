"""
SAM3 Model Loader
=================
Handles lazy loading and caching of SAM3 models from HuggingFace.
"""

import os
import logging
from typing import Optional, Any, Tuple
from pathlib import Path

from .config import SAM3Config, get_config

logger = logging.getLogger(__name__)


class SAM3ModelLoader:
    """
    Lazy loader for SAM3 models.

    The model is only loaded when first needed, and cached for subsequent use.
    Supports downloading from HuggingFace Hub with authentication.
    """

    def __init__(self, config: Optional[SAM3Config] = None):
        self.config = config or get_config()
        self._model: Optional[Any] = None
        self._processor: Optional[Any] = None
        self._device: Optional[str] = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._loaded

    @property
    def device(self) -> str:
        """Get the compute device."""
        if self._device is None:
            self._device = self.config.get_device()
        return self._device

    def _check_dependencies(self) -> Tuple[bool, str]:
        """Check if required dependencies are installed."""
        missing = []

        try:
            import torch
        except ImportError:
            missing.append("torch")

        try:
            import transformers
        except ImportError:
            missing.append("transformers")

        try:
            import huggingface_hub
        except ImportError:
            missing.append("huggingface-hub")

        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}"
        return True, ""

    def _authenticate_hf(self) -> bool:
        """Authenticate with HuggingFace Hub."""
        if not self.config.hf_token:
            logger.warning(
                "No HF_TOKEN configured. SAM3 checkpoints may not be accessible. "
                "Set HF_TOKEN environment variable with your HuggingFace token."
            )
            return False

        try:
            from huggingface_hub import login
            login(token=self.config.hf_token, add_to_git_credential=False)
            logger.info("Successfully authenticated with HuggingFace Hub")
            return True
        except Exception as e:
            logger.error(f"HuggingFace authentication failed: {e}")
            return False

    def _get_gpu_info(self) -> dict:
        """Get GPU information if available."""
        info = {
            "available": False,
            "name": None,
            "memory_gb": None,
        }

        try:
            import torch
            if torch.cuda.is_available():
                info["available"] = True
                info["name"] = torch.cuda.get_device_name(0)
                info["memory_gb"] = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3),
                    2
                )
        except Exception:
            pass

        return info

    def load(self, force_reload: bool = False) -> Tuple[Any, Any]:
        """
        Load the SAM3 model and processor.

        Args:
            force_reload: Force reloading even if already loaded

        Returns:
            Tuple of (model, processor)

        Raises:
            RuntimeError: If model loading fails
        """
        if self._loaded and not force_reload:
            return self._model, self._processor

        # Check dependencies
        deps_ok, deps_error = self._check_dependencies()
        if not deps_ok:
            raise RuntimeError(deps_error)

        # Authenticate with HuggingFace
        self._authenticate_hf()

        logger.info(f"Loading SAM3 model: {self.config.model_id}")
        logger.info(f"Device: {self.device}")

        try:
            import torch
            from transformers import (
                Sam3Model,
                Sam3Processor,
            )

            # Load processor - SAM3 supports text-prompted segmentation
            self._processor = Sam3Processor.from_pretrained(
                self.config.model_id,
                token=self.config.hf_token,
            )

            # Load model with appropriate settings
            model_kwargs = {
                "token": self.config.hf_token,
            }

            # Use flash attention if available and enabled
            use_flash = False
            if self.config.use_flash_attention:
                try:
                    import flash_attn
                    model_kwargs["attn_implementation"] = "flash_attention_2"
                    use_flash = True
                    logger.info("Using Flash Attention 2")
                except ImportError:
                    logger.info("Flash Attention not installed, using default attention")

            # Try to load the model
            try:
                self._model = Sam3Model.from_pretrained(
                    self.config.model_id,
                    **model_kwargs
                )
            except Exception as e:
                if use_flash and "flash" in str(e).lower():
                    # Retry without flash attention
                    logger.warning(f"Flash attention failed, retrying without: {e}")
                    model_kwargs.pop("attn_implementation", None)
                    self._model = Sam3Model.from_pretrained(
                        self.config.model_id,
                        **model_kwargs
                    )
                else:
                    raise

            # Move to device
            self._model = self._model.to(self.device)

            # Optional: compile model for faster inference
            if self.config.compile_model and hasattr(torch, "compile"):
                logger.info("Compiling model with torch.compile...")
                self._model = torch.compile(self._model)

            # Set to eval mode
            self._model.eval()

            self._loaded = True
            logger.info(f"SAM3 model loaded successfully on {self.device}")

            return self._model, self._processor

        except ImportError as e:
            # SAM3 might not be available yet, provide helpful message
            if "Sam3" in str(e) or "Sam2" in str(e):
                raise RuntimeError(
                    "SAM3 models not found in transformers. "
                    "Please ensure you have transformers>=5.0.0 installed "
                    "and the SAM3 models are available on HuggingFace. "
                    f"Original error: {e}"
                )
            raise

        except Exception as e:
            logger.error(f"Failed to load SAM3 model: {e}")
            raise RuntimeError(f"Failed to load SAM3 model: {e}")

    def unload(self):
        """Unload the model to free memory."""
        if self._model is not None:
            try:
                import torch
                del self._model
                self._model = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        self._processor = None
        self._loaded = False
        logger.info("SAM3 model unloaded")

    def get_status(self) -> dict:
        """Get current model status."""
        gpu_info = self._get_gpu_info()

        return {
            "available": True,
            "model_loaded": self._loaded,
            "model_variant": self.config.variant,
            "device": self.device,
            "gpu_available": gpu_info["available"],
            "gpu_name": gpu_info["name"],
            "gpu_memory_gb": gpu_info["memory_gb"],
            "hf_authenticated": self.config.is_hf_authenticated,
            "checkpoint_path": str(self.config.checkpoint_path),
        }


# Global model loader instance
_model_loader: Optional[SAM3ModelLoader] = None


def get_model() -> SAM3ModelLoader:
    """Get the global SAM3 model loader instance."""
    global _model_loader
    if _model_loader is None:
        _model_loader = SAM3ModelLoader()
    return _model_loader


def reset_model():
    """Reset the global model loader (useful for testing)."""
    global _model_loader
    if _model_loader is not None:
        _model_loader.unload()
    _model_loader = None
