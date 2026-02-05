"""
SAM3 (Segment Anything Model 3) Integration Module
===================================================
Provides text-prompted segmentation and enhanced player tracking for football analysis.

This module is an optional enhancement layer on top of the existing YOLO+ByteTrack pipeline.
It enables:
- Text-prompted segmentation ("segment all players in blue jerseys")
- Specific player tracking by description
- Team differentiation by jersey color
- Ball and possession analysis

Usage:
    from sam3 import SAM3Processor, SAM3Config

    processor = SAM3Processor()
    result = processor.segment_frame(frame, prompt="players in blue jerseys")
"""

from .config import SAM3Config, get_config
from .model_loader import SAM3ModelLoader, get_model
from .processor import SAM3Processor
from .types import (
    SegmentationRequest,
    SegmentationResponse,
    TrackingRequest,
    TrackingResponse,
    TeamSegmentationRequest,
    TeamSegmentationResponse,
    EnhanceTracksRequest,
    EnhanceTracksResponse,
    SAM3StatusResponse,
    SegmentedObject,
    TeamData,
)

__all__ = [
    # Config
    "SAM3Config",
    "get_config",
    # Model
    "SAM3ModelLoader",
    "get_model",
    # Processor
    "SAM3Processor",
    # Types
    "SegmentationRequest",
    "SegmentationResponse",
    "TrackingRequest",
    "TrackingResponse",
    "TeamSegmentationRequest",
    "TeamSegmentationResponse",
    "EnhanceTracksRequest",
    "EnhanceTracksResponse",
    "SAM3StatusResponse",
    "SegmentedObject",
    "TeamData",
]

__version__ = "0.1.0"
