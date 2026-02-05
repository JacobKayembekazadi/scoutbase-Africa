"""
SAM3 Processor
==============
Core segmentation and tracking logic using SAM3.
"""

import base64
import io
import logging
import time
from pathlib import Path
from typing import Optional, List, Tuple, Any, Dict
import json

import numpy as np

from .config import SAM3Config, get_config
from .model_loader import SAM3ModelLoader, get_model
from .types import (
    SegmentationRequest,
    SegmentationResponse,
    SegmentedObject,
    TrackingRequest,
    TrackingResponse,
    TrackedFrame,
    TeamSegmentationRequest,
    TeamSegmentationResponse,
    TeamData,
    EnhanceTracksRequest,
    EnhanceTracksResponse,
    EnhancedTrack,
)

logger = logging.getLogger(__name__)


class SAM3Processor:
    """
    High-level processor for SAM3 segmentation and tracking.

    Provides text-prompted segmentation, video tracking, team analysis,
    and integration with existing ByteTrack results.
    """

    def __init__(
        self,
        config: Optional[SAM3Config] = None,
        model_loader: Optional[SAM3ModelLoader] = None,
    ):
        self.config = config or get_config()
        self.model_loader = model_loader or get_model()
        self._results_dir = Path("results")

    def _ensure_model_loaded(self) -> Tuple[Any, Any]:
        """Ensure the model is loaded and return (model, processor)."""
        return self.model_loader.load()

    def _decode_image(self, request: SegmentationRequest) -> np.ndarray:
        """Decode image from request into numpy array."""
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV (cv2) is required for image processing")

        if request.image_base64:
            # Decode base64 image
            image_data = base64.b64decode(request.image_base64)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode base64 image")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        elif request.frame_path:
            # Load from file path
            image = cv2.imread(request.frame_path)
            if image is None:
                raise ValueError(f"Failed to load image from {request.frame_path}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        elif request.job_id:
            # Extract frame from processed video
            return self._extract_frame_from_job(
                request.job_id,
                request.frame_number or 0
            )

        else:
            raise ValueError(
                "Must provide image_base64, frame_path, or job_id+frame_number"
            )

    def _extract_frame_from_job(self, job_id: str, frame_number: int) -> np.ndarray:
        """Extract a frame from a processed job's video."""
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV (cv2) is required")

        # Find the original or annotated video
        results_path = self._results_dir / job_id
        video_path = results_path / "annotated_output.mp4"

        if not video_path.exists():
            # Try to find original upload
            uploads_dir = Path("uploads")
            video_files = list(uploads_dir.glob(f"{job_id}_*"))
            if video_files:
                video_path = video_files[0]
            else:
                raise ValueError(f"No video found for job {job_id}")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")

        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                raise ValueError(f"Failed to read frame {frame_number}")
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        finally:
            cap.release()

    def _mask_to_rle(self, mask: np.ndarray) -> str:
        """Convert binary mask to run-length encoding."""
        pixels = mask.flatten()
        pixels = np.concatenate([[0], pixels, [0]])
        runs = np.where(pixels[1:] != pixels[:-1])[0] + 1
        runs[1::2] -= runs[::2]
        return ",".join(map(str, runs))

    def _get_dominant_color(self, image: np.ndarray, mask: np.ndarray) -> List[int]:
        """Get dominant color within masked region."""
        # Apply mask
        masked = image[mask > 0]
        if len(masked) == 0:
            return [128, 128, 128]

        # Simple mean color (could use k-means for better results)
        mean_color = np.mean(masked, axis=0).astype(int)
        return mean_color.tolist()

    def _classify_by_color(
        self,
        dominant_colors: List[Tuple[int, List[int]]],
        home_hint: Optional[str] = None,
        away_hint: Optional[str] = None,
    ) -> Dict[int, str]:
        """Classify objects into teams based on color clustering."""
        if not dominant_colors:
            return {}

        # Simple color classification
        # In production, use k-means clustering
        classifications = {}

        # Color name mapping (simplified)
        color_names = {
            "red": ([180, 0, 0], [255, 100, 100]),
            "blue": ([0, 0, 180], [100, 100, 255]),
            "green": ([0, 180, 0], [100, 255, 100]),
            "white": ([200, 200, 200], [255, 255, 255]),
            "black": ([0, 0, 0], [60, 60, 60]),
            "yellow": ([180, 180, 0], [255, 255, 100]),
        }

        for obj_id, color in dominant_colors:
            r, g, b = color

            # Check for referee (typically black)
            if r < 60 and g < 60 and b < 60:
                classifications[obj_id] = "referee"
                continue

            # Classify based on hints or dominant channel
            if home_hint and away_hint:
                # Use hints to classify
                # Simplified: just use the most dominant channel
                if home_hint.lower() == "blue" and b > r and b > g:
                    classifications[obj_id] = "home"
                elif away_hint.lower() == "blue" and b > r and b > g:
                    classifications[obj_id] = "away"
                elif home_hint.lower() == "red" and r > b and r > g:
                    classifications[obj_id] = "home"
                elif away_hint.lower() == "red" and r > b and r > g:
                    classifications[obj_id] = "away"
                else:
                    classifications[obj_id] = "unknown"
            else:
                # No hints, assign based on clustering
                # This would need proper clustering in production
                classifications[obj_id] = "unknown"

        return classifications

    def segment_frame(self, request: SegmentationRequest) -> SegmentationResponse:
        """
        Perform text-prompted segmentation on a single frame.

        Args:
            request: Segmentation request with image and prompt

        Returns:
            SegmentationResponse with segmented objects
        """
        start_time = time.time()

        try:
            # Load model
            model, processor = self._ensure_model_loaded()

            # Decode image
            image = self._decode_image(request)
            h, w = image.shape[:2]

            # Prepare inputs
            import torch

            inputs = processor(
                images=image,
                input_text=request.prompt,
                return_tensors="pt",
            ).to(self.model_loader.device)

            # Run inference
            with torch.no_grad():
                outputs = model(**inputs)

            # Process outputs
            # Note: Actual output processing depends on the specific SAM2/3 API
            # This is a placeholder that would need adjustment for the real model
            masks = outputs.pred_masks if hasattr(outputs, 'pred_masks') else None
            scores = outputs.iou_scores if hasattr(outputs, 'iou_scores') else None

            objects = []

            if masks is not None:
                # Convert masks to numpy
                masks_np = masks.cpu().numpy()
                scores_np = scores.cpu().numpy() if scores is not None else None

                for i in range(masks_np.shape[0]):
                    mask = masks_np[i] > 0.5
                    score = float(scores_np[i]) if scores_np is not None else 0.5

                    if score < request.confidence_threshold:
                        continue

                    # Calculate properties
                    area = int(np.sum(mask))
                    if area == 0:
                        continue

                    # Centroid
                    y_coords, x_coords = np.where(mask)
                    centroid = [float(np.mean(x_coords)), float(np.mean(y_coords))]

                    # Bounding box
                    bbox = None
                    if request.return_bboxes:
                        x1, y1 = float(np.min(x_coords)), float(np.min(y_coords))
                        x2, y2 = float(np.max(x_coords)), float(np.max(y_coords))
                        bbox = [x1, y1, x2, y2]

                    # Mask RLE
                    mask_rle = None
                    if request.return_masks:
                        mask_rle = self._mask_to_rle(mask.astype(np.uint8))

                    # Dominant color
                    dominant_color = self._get_dominant_color(image, mask)

                    objects.append(SegmentedObject(
                        id=i,
                        confidence=score,
                        bbox=bbox,
                        mask_rle=mask_rle,
                        area=area,
                        centroid=centroid,
                        dominant_color=dominant_color,
                    ))

            processing_time = (time.time() - start_time) * 1000

            return SegmentationResponse(
                success=True,
                prompt=request.prompt,
                objects=objects,
                total_objects=len(objects),
                processing_time_ms=processing_time,
                frame_size=[w, h],
            )

        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            return SegmentationResponse(
                success=False,
                prompt=request.prompt,
                error=str(e),
            )

    def track_video(self, request: TrackingRequest) -> TrackingResponse:
        """
        Track objects through video frames using SAM3.

        Args:
            request: Tracking request with job_id and prompt

        Returns:
            TrackingResponse with per-frame tracking data
        """
        start_time = time.time()

        try:
            import cv2

            # Validate job exists
            results_path = self._results_dir / request.job_id
            if not results_path.exists():
                raise ValueError(f"Job {request.job_id} not found")

            # Find video file
            video_path = results_path / "annotated_output.mp4"
            if not video_path.exists():
                uploads_dir = Path("uploads")
                video_files = list(uploads_dir.glob(f"{request.job_id}_*"))
                if video_files:
                    video_path = video_files[0]
                else:
                    raise ValueError(f"No video found for job {request.job_id}")

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Failed to open video: {video_path}")

            try:
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                end_frame = request.end_frame or total_frames

                frames_data = []
                frame_idx = request.start_frame

                while frame_idx < end_frame:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Convert and segment
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    seg_request = SegmentationRequest(
                        image_base64=None,
                        frame_path=None,
                        prompt=request.prompt,
                        confidence_threshold=0.5,
                        return_masks=True,
                        return_bboxes=True,
                    )
                    # Directly pass image instead of encoding
                    # This is a simplified version - actual implementation would vary
                    seg_response = self._segment_array(rgb_frame, seg_request)

                    if seg_response.success:
                        timestamp_ms = (frame_idx / fps) * 1000 if fps > 0 else 0
                        frames_data.append(TrackedFrame(
                            frame_number=frame_idx,
                            timestamp_ms=timestamp_ms,
                            objects=seg_response.objects[:request.max_objects],
                        ))

                    frame_idx += request.sample_rate

            finally:
                cap.release()

            processing_time = (time.time() - start_time) * 1000

            return TrackingResponse(
                success=True,
                job_id=request.job_id,
                prompt=request.prompt,
                total_frames_processed=len(frames_data),
                frames=frames_data,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Video tracking failed: {e}")
            return TrackingResponse(
                success=False,
                job_id=request.job_id,
                prompt=request.prompt,
                error=str(e),
            )

    def _segment_array(
        self,
        image: np.ndarray,
        request: SegmentationRequest
    ) -> SegmentationResponse:
        """Segment a numpy array directly (internal helper)."""
        start_time = time.time()

        try:
            model, processor = self._ensure_model_loaded()

            h, w = image.shape[:2]

            import torch

            inputs = processor(
                images=image,
                input_text=request.prompt,
                return_tensors="pt",
            ).to(self.model_loader.device)

            with torch.no_grad():
                outputs = model(**inputs)

            # Process outputs (placeholder - adjust for actual SAM2/3 API)
            objects = []

            processing_time = (time.time() - start_time) * 1000

            return SegmentationResponse(
                success=True,
                prompt=request.prompt,
                objects=objects,
                total_objects=len(objects),
                processing_time_ms=processing_time,
                frame_size=[w, h],
            )

        except Exception as e:
            return SegmentationResponse(
                success=False,
                prompt=request.prompt,
                error=str(e),
            )

    def segment_teams(
        self,
        request: TeamSegmentationRequest
    ) -> TeamSegmentationResponse:
        """
        Segment players into teams based on jersey colors.

        Args:
            request: Team segmentation request

        Returns:
            TeamSegmentationResponse with team assignments
        """
        start_time = time.time()

        try:
            # First, segment all players
            seg_request = SegmentationRequest(
                job_id=request.job_id,
                frame_number=request.frame_number,
                prompt="football player on the field",
                confidence_threshold=0.5,
                return_masks=True,
                return_bboxes=True,
            )

            seg_response = self.segment_frame(seg_request)

            if not seg_response.success:
                raise ValueError(seg_response.error or "Segmentation failed")

            # Collect dominant colors
            color_data = [
                (obj.id, obj.dominant_color)
                for obj in seg_response.objects
                if obj.dominant_color
            ]

            # Classify into teams
            classifications = self._classify_by_color(
                color_data,
                request.home_color_hint,
                request.away_color_hint,
            )

            # Group by team
            teams_dict: Dict[str, TeamData] = {
                "home": TeamData(team_id="home"),
                "away": TeamData(team_id="away"),
                "referee": TeamData(team_id="referee"),
                "unknown": TeamData(team_id="unknown"),
            }

            for obj in seg_response.objects:
                team_label = classifications.get(obj.id, "unknown")
                if team_label in teams_dict:
                    teams_dict[team_label].players.append(obj)
                    teams_dict[team_label].player_count += 1

            # Calculate dominant colors for each team
            for team in teams_dict.values():
                if team.players:
                    colors = [p.dominant_color for p in team.players if p.dominant_color]
                    if colors:
                        avg_color = np.mean(colors, axis=0).astype(int).tolist()
                        team.dominant_color = avg_color

            # Segment ball if requested
            ball = None
            if request.include_ball:
                ball_request = SegmentationRequest(
                    job_id=request.job_id,
                    frame_number=request.frame_number,
                    prompt="football soccer ball",
                    confidence_threshold=0.3,
                    return_masks=True,
                    return_bboxes=True,
                )
                ball_response = self.segment_frame(ball_request)
                if ball_response.success and ball_response.objects:
                    ball = ball_response.objects[0]

            processing_time = (time.time() - start_time) * 1000

            return TeamSegmentationResponse(
                success=True,
                job_id=request.job_id,
                frame_number=request.frame_number,
                teams=[t for t in teams_dict.values() if t.player_count > 0],
                ball=ball,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Team segmentation failed: {e}")
            return TeamSegmentationResponse(
                success=False,
                job_id=request.job_id,
                error=str(e),
            )

    def enhance_tracks(
        self,
        job_id: str,
        request: EnhanceTracksRequest
    ) -> EnhanceTracksResponse:
        """
        Enhance existing ByteTrack results with SAM3 data.

        Args:
            job_id: Job ID with ByteTrack results
            request: Enhancement request

        Returns:
            EnhanceTracksResponse with enhanced track data
        """
        start_time = time.time()

        try:
            # Load existing tracking results
            results_path = self._results_dir / job_id / "tracking_results.json"
            if not results_path.exists():
                raise ValueError(f"No tracking results found for job {job_id}")

            with open(results_path) as f:
                tracking_data = json.load(f)

            players = tracking_data.get("players", {})
            if not players:
                raise ValueError("No player tracks in results")

            # Sample frames for analysis
            total_frames = tracking_data.get("total_frames", 0)
            if total_frames == 0:
                raise ValueError("No frames in tracking data")

            sample_interval = max(1, total_frames // request.sample_frames)
            sample_frame_nums = list(range(0, total_frames, sample_interval))[:request.sample_frames]

            # Analyze tracks
            enhanced_tracks = []
            track_colors: Dict[int, List[List[int]]] = {}

            for frame_num in sample_frame_nums:
                # Segment this frame
                prompt = request.prompt or "football player"
                seg_request = SegmentationRequest(
                    job_id=job_id,
                    frame_number=frame_num,
                    prompt=prompt,
                    confidence_threshold=0.5,
                    return_masks=request.add_masks,
                    return_bboxes=True,
                )

                seg_response = self.segment_frame(seg_request)

                if seg_response.success:
                    # Match segmented objects to tracks
                    # This is simplified - would need proper matching in production
                    for obj in seg_response.objects:
                        # Find closest track by bbox center
                        if obj.centroid and obj.dominant_color:
                            # Store color for averaging
                            # In production, match by IoU with track bbox
                            obj_id = obj.id  # Placeholder
                            if obj_id not in track_colors:
                                track_colors[obj_id] = []
                            track_colors[obj_id].append(obj.dominant_color)

            # Build enhanced tracks
            team_counts = {"home": 0, "away": 0, "referee": 0, "unknown": 0}

            for track_id_str, track_data in players.items():
                track_id = int(track_id_str)

                # Get average color if available
                colors = track_colors.get(track_id, [])
                dominant_color = None
                if colors:
                    dominant_color = np.mean(colors, axis=0).astype(int).tolist()

                # Classify team
                team_label = "unknown"
                if dominant_color:
                    r, g, b = dominant_color
                    if r < 60 and g < 60 and b < 60:
                        team_label = "referee"
                    # Add more classification logic as needed

                team_counts[team_label] = team_counts.get(team_label, 0) + 1

                enhanced_tracks.append(EnhancedTrack(
                    track_id=track_id,
                    team_label=team_label if request.add_team_labels else None,
                    dominant_color=dominant_color,
                    jersey_number=None,  # Would need OCR for this
                    confidence=0.8,
                ))

            processing_time = (time.time() - start_time) * 1000

            return EnhanceTracksResponse(
                success=True,
                job_id=job_id,
                enhanced_tracks=enhanced_tracks,
                total_tracks=len(enhanced_tracks),
                home_team_count=team_counts["home"],
                away_team_count=team_counts["away"],
                referee_count=team_counts["referee"],
                unknown_count=team_counts["unknown"],
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Track enhancement failed: {e}")
            return EnhanceTracksResponse(
                success=False,
                job_id=job_id,
                error=str(e),
            )

    def get_status(self) -> dict:
        """Get processor status."""
        return self.model_loader.get_status()
