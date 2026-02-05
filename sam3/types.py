"""
SAM3 Type Definitions
=====================
Pydantic models for SAM3 API requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Segmentation Types
# ---------------------------------------------------------------------------

class SegmentationRequest(BaseModel):
    """Request for text-prompted frame segmentation."""

    # Either provide image_base64 or frame_path
    image_base64: Optional[str] = Field(
        None,
        description="Base64-encoded image data"
    )
    frame_path: Optional[str] = Field(
        None,
        description="Path to image file on server"
    )
    job_id: Optional[str] = Field(
        None,
        description="Job ID to extract frame from processed video"
    )
    frame_number: Optional[int] = Field(
        None,
        description="Frame number when using job_id"
    )

    # Segmentation parameters
    prompt: str = Field(
        ...,
        description="Text prompt describing what to segment (e.g., 'players in blue jerseys')"
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for segmentation"
    )
    return_masks: bool = Field(
        default=True,
        description="Whether to return binary mask data"
    )
    return_bboxes: bool = Field(
        default=True,
        description="Whether to return bounding boxes"
    )


class SegmentedObject(BaseModel):
    """A single segmented object from the frame."""

    id: int = Field(..., description="Object ID within this segmentation")
    confidence: float = Field(..., description="Segmentation confidence score")
    bbox: Optional[List[float]] = Field(
        None,
        description="Bounding box [x1, y1, x2, y2]"
    )
    mask_rle: Optional[str] = Field(
        None,
        description="Run-length encoded mask data"
    )
    area: int = Field(..., description="Mask area in pixels")
    centroid: List[float] = Field(..., description="Centroid [x, y]")
    dominant_color: Optional[List[int]] = Field(
        None,
        description="Dominant RGB color within mask"
    )


class SegmentationResponse(BaseModel):
    """Response from frame segmentation."""

    success: bool
    prompt: str
    objects: List[SegmentedObject] = Field(default_factory=list)
    total_objects: int = 0
    processing_time_ms: float = 0.0
    frame_size: List[int] = Field(
        default_factory=lambda: [0, 0],
        description="[width, height]"
    )
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Video Tracking Types
# ---------------------------------------------------------------------------

class TrackingRequest(BaseModel):
    """Request for video object tracking with SAM3."""

    job_id: str = Field(
        ...,
        description="Existing job ID with processed video"
    )
    prompt: str = Field(
        ...,
        description="Text prompt describing what to track"
    )
    start_frame: int = Field(
        default=0,
        ge=0,
        description="Frame to start tracking from"
    )
    end_frame: Optional[int] = Field(
        None,
        description="Frame to end tracking (None = end of video)"
    )
    sample_rate: int = Field(
        default=5,
        ge=1,
        description="Process every Nth frame"
    )
    max_objects: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Maximum objects to track"
    )


class TrackedFrame(BaseModel):
    """Tracking data for a single frame."""

    frame_number: int
    timestamp_ms: float
    objects: List[SegmentedObject]


class TrackingResponse(BaseModel):
    """Response from video tracking."""

    success: bool
    job_id: str
    prompt: str
    total_frames_processed: int = 0
    frames: List[TrackedFrame] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Team Segmentation Types
# ---------------------------------------------------------------------------

class TeamSegmentationRequest(BaseModel):
    """Request for team-based segmentation."""

    job_id: str = Field(..., description="Job ID with processed video")
    frame_number: Optional[int] = Field(
        None,
        description="Specific frame (None = sample multiple frames)"
    )
    home_color_hint: Optional[str] = Field(
        None,
        description="Hint for home team color (e.g., 'blue', 'red')"
    )
    away_color_hint: Optional[str] = Field(
        None,
        description="Hint for away team color"
    )
    include_ball: bool = Field(
        default=True,
        description="Whether to segment the ball"
    )
    include_referee: bool = Field(
        default=True,
        description="Whether to segment referee(s)"
    )


class TeamData(BaseModel):
    """Data for a segmented team."""

    team_id: str = Field(..., description="'home', 'away', 'referee', or 'ball'")
    player_count: int = 0
    dominant_color: Optional[List[int]] = Field(
        None,
        description="Dominant RGB color"
    )
    players: List[SegmentedObject] = Field(default_factory=list)


class TeamSegmentationResponse(BaseModel):
    """Response from team segmentation."""

    success: bool
    job_id: str
    frame_number: Optional[int] = None
    teams: List[TeamData] = Field(default_factory=list)
    ball: Optional[SegmentedObject] = None
    processing_time_ms: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# ByteTrack Enhancement Types
# ---------------------------------------------------------------------------

class EnhanceTracksRequest(BaseModel):
    """Request to enhance existing ByteTrack results with SAM3."""

    prompt: Optional[str] = Field(
        None,
        description="Filter tracks by text prompt"
    )
    add_masks: bool = Field(
        default=True,
        description="Add segmentation masks to tracks"
    )
    add_team_labels: bool = Field(
        default=True,
        description="Attempt to label tracks by team"
    )
    sample_frames: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of frames to sample for analysis"
    )


class EnhancedTrack(BaseModel):
    """A ByteTrack track enhanced with SAM3 data."""

    track_id: int
    team_label: Optional[str] = Field(
        None,
        description="'home', 'away', 'referee', or 'unknown'"
    )
    dominant_color: Optional[List[int]] = None
    jersey_number: Optional[str] = None
    confidence: float = 0.0
    sample_masks: Optional[List[str]] = Field(
        None,
        description="RLE masks from sampled frames"
    )


class EnhanceTracksResponse(BaseModel):
    """Response from track enhancement."""

    success: bool
    job_id: str
    enhanced_tracks: List[EnhancedTrack] = Field(default_factory=list)
    total_tracks: int = 0
    home_team_count: int = 0
    away_team_count: int = 0
    referee_count: int = 0
    unknown_count: int = 0
    processing_time_ms: float = 0.0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Status Types
# ---------------------------------------------------------------------------

class SAM3StatusResponse(BaseModel):
    """SAM3 module status response."""

    available: bool = Field(..., description="Whether SAM3 is available")
    model_loaded: bool = Field(
        default=False,
        description="Whether the model is currently loaded"
    )
    model_variant: Optional[str] = Field(
        None,
        description="Model variant (base/large/huge)"
    )
    device: str = Field(default="cpu", description="Compute device")
    gpu_available: bool = Field(
        default=False,
        description="Whether CUDA GPU is available"
    )
    gpu_name: Optional[str] = Field(None, description="GPU name if available")
    gpu_memory_gb: Optional[float] = Field(
        None,
        description="GPU memory in GB"
    )
    hf_authenticated: bool = Field(
        default=False,
        description="Whether HuggingFace auth is configured"
    )
    checkpoint_path: Optional[str] = Field(
        None,
        description="Path to model checkpoint"
    )
    error: Optional[str] = None
