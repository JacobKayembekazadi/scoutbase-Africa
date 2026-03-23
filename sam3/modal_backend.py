"""
SAM3 Modal Backend
==================
Offloads SAM3 inference to Modal serverless GPU.

Usage:
    # Deploy to Modal (one-time)
    modal deploy sam3/modal_backend.py

    # From the FastAPI server, call via HTTP
    SAM3_BACKEND=modal  →  routes to Modal endpoint
"""

import os
import logging
import time
import base64
import io
from typing import Optional, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modal App Definition (runs on Modal's cloud GPU)
# ---------------------------------------------------------------------------

try:
    import modal

    app = modal.App("scoutbase-sam3")

    # Volume for caching model weights across cold starts
    model_volume = modal.Volume.from_name("scoutbase-sam3-weights", create_if_missing=True)

    # Docker image with SAM3 dependencies
    sam3_image = (
        modal.Image.debian_slim(python_version="3.12")
        .pip_install(
            "torch",
            "torchvision",
            "transformers>=5.0.0",
            "huggingface-hub>=0.20.0",
            "safetensors>=0.4.0",
            "Pillow>=9.0.0",
            "numpy>=1.24.0",
            "opencv-python-headless>=4.8.0",
        )
    )

    @app.cls(
        image=sam3_image,
        gpu="A10G",
        timeout=300,
        volumes={"/weights": model_volume},
        secrets=[modal.Secret.from_name("huggingface-secret")],
    )
    class SAM3InferenceService:
        """SAM3 model running on Modal GPU."""

        @modal.enter()
        def load_model(self):
            """Called once when container starts — loads SAM3 model to GPU."""
            import torch
            from transformers import AutoProcessor, AutoModelForMaskGeneration

            variant = os.getenv("SAM3_VARIANT", "base")
            model_map = {
                "base": "facebook/sam2.1-hiera-base-plus",
                "large": "facebook/sam2.1-hiera-large",
            }
            model_name = model_map.get(variant, model_map["base"])

            cache_dir = "/weights"
            self.processor = AutoProcessor.from_pretrained(
                model_name, cache_dir=cache_dir
            )
            self.model = AutoModelForMaskGeneration.from_pretrained(
                model_name, cache_dir=cache_dir
            ).to("cuda")
            self.model.eval()
            self.device = "cuda"
            print(f"[Modal SAM3] Loaded {model_name} on {self.device}")

        @modal.method()
        def segment_frame(
            self,
            image_base64: str,
            prompt: str,
            confidence_threshold: float = 0.5,
            return_masks: bool = False,
            return_bboxes: bool = True,
        ) -> dict:
            """Run text-prompted segmentation on a single frame."""
            import torch
            import numpy as np
            from PIL import Image as PILImage

            start_time = time.time()

            # Decode image
            image_data = base64.b64decode(image_base64)
            pil_image = PILImage.open(io.BytesIO(image_data)).convert("RGB")
            image_np = np.array(pil_image)
            h, w = image_np.shape[:2]

            # Process with SAM3
            inputs = self.processor(
                images=pil_image,
                text=prompt,
                return_tensors="pt",
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

            # Post-process
            target_sizes = (
                inputs.get("original_sizes").tolist()
                if inputs.get("original_sizes") is not None
                else [[h, w]]
            )
            results = self.processor.post_process_instance_segmentation(
                outputs,
                threshold=confidence_threshold,
                mask_threshold=0.5,
                target_sizes=target_sizes,
            )[0]

            objects = []
            masks = results.get("masks", [])
            boxes = results.get("boxes", [])
            scores = results.get("scores", [])

            for i in range(len(masks)):
                mask = masks[i].cpu().numpy() if hasattr(masks[i], "cpu") else np.array(masks[i])
                score = float(scores[i]) if i < len(scores) else 0.5

                if score < confidence_threshold:
                    continue

                area = int(np.sum(mask))
                if area == 0:
                    continue

                y_coords, x_coords = np.where(mask)
                if len(x_coords) == 0:
                    continue

                centroid = [float(np.mean(x_coords)), float(np.mean(y_coords))]

                bbox = None
                if return_bboxes and i < len(boxes):
                    box = boxes[i].cpu().numpy() if hasattr(boxes[i], "cpu") else boxes[i]
                    bbox = [float(box[0]), float(box[1]), float(box[2]), float(box[3])]

                # Dominant color
                masked_pixels = image_np[mask > 0]
                dominant_color = (
                    np.mean(masked_pixels, axis=0).astype(int).tolist()
                    if len(masked_pixels) > 0
                    else [128, 128, 128]
                )

                mask_rle = None
                if return_masks:
                    pixels = mask.astype(np.uint8).flatten()
                    pixels = np.concatenate([[0], pixels, [0]])
                    runs = np.where(pixels[1:] != pixels[:-1])[0] + 1
                    runs[1::2] -= runs[::2]
                    mask_rle = ",".join(map(str, runs))

                objects.append(
                    {
                        "id": i,
                        "confidence": score,
                        "bbox": bbox,
                        "mask_rle": mask_rle,
                        "area": area,
                        "centroid": centroid,
                        "dominant_color": dominant_color,
                    }
                )

            processing_time = (time.time() - start_time) * 1000

            return {
                "success": True,
                "prompt": prompt,
                "objects": objects,
                "total_objects": len(objects),
                "processing_time_ms": processing_time,
                "frame_size": [w, h],
            }

        @modal.method()
        def health_check(self) -> dict:
            """Check if model is loaded and GPU is available."""
            import torch

            return {
                "available": True,
                "model_loaded": hasattr(self, "model"),
                "device": str(self.device),
                "gpu_available": torch.cuda.is_available(),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                "backend": "modal",
            }

    MODAL_AVAILABLE = True

except ImportError:
    MODAL_AVAILABLE = False
    logger.info("Modal not installed — SAM3 Modal backend unavailable")


# ---------------------------------------------------------------------------
# Client-side adapter (called from FastAPI server)
# ---------------------------------------------------------------------------

class ModalSAM3Client:
    """
    Client that calls the Modal-hosted SAM3 service.
    Used when SAM3_BACKEND=modal in the FastAPI server.
    """

    def __init__(self):
        if not MODAL_AVAILABLE:
            raise RuntimeError("Modal package not installed. pip install modal")
        self._cls = modal.Cls.from_name("scoutbase-sam3", "SAM3InferenceService")

    def segment_frame(self, image_base64: str, prompt: str, **kwargs) -> dict:
        """Call Modal SAM3 for single-frame segmentation."""
        try:
            result = self._cls().segment_frame.remote(
                image_base64=image_base64,
                prompt=prompt,
                **kwargs,
            )
            return result
        except Exception as e:
            logger.error(f"Modal SAM3 call failed: {e}")
            return {
                "success": False,
                "prompt": prompt,
                "error": f"Modal inference failed: {e}",
                "objects": [],
                "total_objects": 0,
            }

    def health_check(self) -> dict:
        """Check Modal SAM3 service health."""
        try:
            return self._cls().health_check.remote()
        except Exception as e:
            return {
                "available": False,
                "model_loaded": False,
                "error": f"Modal service unreachable: {e}",
                "backend": "modal",
            }
