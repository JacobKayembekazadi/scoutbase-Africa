"""
ScoutBase Africa — Match Video Processing Pipeline
===================================================
Core pipeline: Video → YOLO Detection → ByteTrack Tracking → Per-Player Stats

This is the heart of the platform. It takes raw match footage and produces
structured player tracking data that feeds the ScoutBase dashboard.

Requirements:
    pip install ultralytics trackers supervision opencv-python numpy

Usage:
    python process_match.py --video path/to/match.mp4 --output results/

    Or import and use programmatically:
    from process_match import process_match_video
    results = process_match_video("match.mp4", output_dir="results/")
"""

import cv2
import json
import numpy as np
import argparse
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict

# Pose analysis and clip extraction are imported lazily to avoid
# hard failures if optional deps (mediapipe, ffmpeg) are missing.


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

import supervision as sv
from ultralytics import YOLO
from trackers import ByteTrackTracker


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class PlayerTrackingData:
    """Accumulated tracking data for a single player (track_id)."""
    track_id: int
    frames_visible: int = 0
    first_seen_frame: int = 0
    last_seen_frame: int = 0
    positions: list = field(default_factory=list)        # [(x_center, y_center), ...]
    bboxes: list = field(default_factory=list)            # [(x1, y1, x2, y2), ...]
    frame_indices: list = field(default_factory=list)     # [frame_num, ...]
    speeds: list = field(default_factory=list)            # [pixels_per_frame, ...]
    zones: list = field(default_factory=list)             # ["left_third", "center", "right_third"]
    sprint_count: int = 0
    max_speed: float = 0.0

    @property
    def estimated_minutes(self) -> float:
        """Estimate minutes on pitch based on frames visible vs total frames."""
        if not self.frame_indices:
            return 0.0
        frame_span = self.last_seen_frame - self.first_seen_frame + 1
        return frame_span  # Will be converted to minutes using FPS

    @property
    def avg_speed(self) -> float:
        if not self.speeds:
            return 0.0
        return sum(self.speeds) / len(self.speeds)

    @property
    def heat_map_data(self) -> dict:
        """Generate simplified heat map from position history."""
        if not self.positions:
            return {"zones": {}}
        zone_counts = defaultdict(int)
        for zone in self.zones:
            zone_counts[zone] += 1
        total = len(self.zones)
        return {
            "zones": {k: round(v / total * 100, 1) for k, v in zone_counts.items()}
        }

    def to_dict(self) -> dict:
        """Serialize for JSON output / database storage."""
        return {
            "track_id": self.track_id,
            "frames_visible": self.frames_visible,
            "first_seen_frame": self.first_seen_frame,
            "last_seen_frame": self.last_seen_frame,
            "estimated_minutes": round(self.estimated_minutes, 1),
            "sprint_count": self.sprint_count,
            "max_speed_px": round(self.max_speed, 2),
            "avg_speed_px": round(self.avg_speed, 2),
            "heat_map": self.heat_map_data,
            "total_positions": len(self.positions),
        }


@dataclass
class MatchProcessingResult:
    """Complete output from processing a match video."""
    video_path: str
    total_frames: int
    fps: float
    duration_seconds: float
    resolution: tuple
    players_tracked: int
    processing_time_seconds: float
    player_data: dict = field(default_factory=dict)  # track_id -> PlayerTrackingData

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration_seconds": round(self.duration_seconds, 1),
            "resolution": list(self.resolution),
            "players_tracked": self.players_tracked,
            "processing_time_seconds": round(self.processing_time_seconds, 1),
            "players": {
                str(tid): pdata.to_dict()
                for tid, pdata in self.player_data.items()
            },
        }


# ---------------------------------------------------------------------------
# Pitch Zone Classification
# ---------------------------------------------------------------------------

def classify_zone(x_center: float, frame_width: int) -> str:
    """Classify position into pitch thirds based on x-coordinate."""
    third = frame_width / 3
    if x_center < third:
        return "defensive_third"
    elif x_center < 2 * third:
        return "middle_third"
    else:
        return "attacking_third"


def classify_vertical_zone(y_center: float, frame_height: int) -> str:
    """Classify vertical position (left/center/right wing)."""
    third = frame_height / 3
    if y_center < third:
        return "left_flank"
    elif y_center < 2 * third:
        return "central"
    else:
        return "right_flank"


# ---------------------------------------------------------------------------
# Core Processing Pipeline
# ---------------------------------------------------------------------------

def process_match_video(
    video_path: str,
    output_dir: str = "results",
    model_path: str = "yolo11n.pt",
    confidence_threshold: float = 0.3,
    target_classes: list = None,
    generate_annotated_video: bool = True,
    sprint_threshold: float = 15.0,
    max_frames: Optional[int] = None,
    process_every_n: int = 1,
) -> MatchProcessingResult:
    """
    Process a match video through the full detection + tracking pipeline.

    Args:
        video_path: Path to input match video
        output_dir: Directory for output files
        model_path: YOLO model to use (yolo11n.pt, yolo11s.pt, yolo11m.pt)
                    Nano is fast, Medium is more accurate. Use what your hardware allows.
        confidence_threshold: Min detection confidence (lower = more detections, more noise)
        target_classes: COCO class IDs to track. Default [0] = persons only.
                        Set to [0, 32] to include sports ball.
        generate_annotated_video: Whether to output video with bounding boxes + track IDs
        sprint_threshold: Pixel displacement per frame to count as a sprint
        max_frames: Limit frames processed (useful for testing)
        process_every_n: Process every Nth frame (1 = all, 2 = half, etc.)

    Returns:
        MatchProcessingResult with all player tracking data
    """
    if target_classes is None:
        target_classes = [0]  # COCO class 0 = person

    start_time = time.time()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # --- Initialize Models ---
    print(f"Loading YOLO model: {model_path}")
    model = YOLO(model_path)

    print("Initializing ByteTrack tracker")
    tracker = ByteTrackTracker()

    # --- Open Video ---
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0

    if max_frames:
        total_frames = min(total_frames, max_frames)

    print(f"Video: {width}x{height} @ {fps:.1f} FPS, {total_frames} frames, {duration:.1f}s")

    # --- Annotated Video Writer ---
    video_writer = None
    if generate_annotated_video:
        annotated_path = str(output_path / "annotated_output.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(annotated_path, fourcc, fps, (width, height))

    # --- Annotators for visualization ---
    box_annotator = sv.BoxAnnotator(thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
    trace_annotator = sv.TraceAnnotator(thickness=1, trace_length=60)

    # --- Tracking State ---
    player_tracks: dict[int, PlayerTrackingData] = {}
    frame_count = 0
    processed_count = 0

    print(f"\nProcessing {total_frames} frames...")
    print("=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if max_frames and frame_count > max_frames:
            break

        # Skip frames if process_every_n > 1
        if frame_count % process_every_n != 0:
            continue

        processed_count += 1

        # --- Detection ---
        results = model(frame, verbose=False, conf=confidence_threshold)[0]
        detections = sv.Detections.from_ultralytics(results)

        # Filter to target classes (persons only by default)
        mask = np.isin(detections.class_id, target_classes)
        detections = detections[mask]

        # --- Tracking ---
        detections = tracker.update(detections)

        # --- Extract Per-Player Data ---
        if detections.tracker_id is not None:
            for i, track_id in enumerate(detections.tracker_id):
                tid = int(track_id)
                bbox = detections.xyxy[i]  # [x1, y1, x2, y2]
                x_center = (bbox[0] + bbox[2]) / 2
                y_center = (bbox[1] + bbox[3]) / 2

                # Initialize new track
                if tid not in player_tracks:
                    player_tracks[tid] = PlayerTrackingData(
                        track_id=tid,
                        first_seen_frame=frame_count,
                    )

                pt = player_tracks[tid]
                pt.frames_visible += 1
                pt.last_seen_frame = frame_count
                pt.positions.append((float(x_center), float(y_center)))
                pt.bboxes.append([float(b) for b in bbox])
                pt.frame_indices.append(frame_count)

                # Zone classification
                h_zone = classify_zone(x_center, width)
                pt.zones.append(h_zone)

                # Speed calculation (pixel displacement from last position)
                if len(pt.positions) >= 2:
                    prev = pt.positions[-2]
                    dx = x_center - prev[0]
                    dy = y_center - prev[1]
                    speed = np.sqrt(dx**2 + dy**2)
                    pt.speeds.append(float(speed))

                    if speed > pt.max_speed:
                        pt.max_speed = speed

                    if speed > sprint_threshold:
                        pt.sprint_count += 1

        # --- Annotate Frame ---
        if video_writer and detections.tracker_id is not None:
            labels = [f"#{tid}" for tid in detections.tracker_id]
            annotated = frame.copy()
            annotated = box_annotator.annotate(annotated, detections)
            annotated = label_annotator.annotate(annotated, detections, labels=labels)
            annotated = trace_annotator.annotate(annotated, detections)
            video_writer.write(annotated)
        elif video_writer:
            video_writer.write(frame)

        # Progress
        if processed_count % 100 == 0:
            elapsed = time.time() - start_time
            fps_actual = processed_count / elapsed
            pct = frame_count / total_frames * 100
            active_tracks = len([t for t in player_tracks.values()
                               if t.last_seen_frame >= frame_count - int(fps * 5)])
            print(f"  Frame {frame_count}/{total_frames} ({pct:.0f}%) | "
                  f"{fps_actual:.1f} FPS | "
                  f"Active tracks: {active_tracks} | "
                  f"Total tracked: {len(player_tracks)}")

    # --- Cleanup ---
    cap.release()
    if video_writer:
        video_writer.release()

    processing_time = time.time() - start_time

    # --- Build Result ---
    result = MatchProcessingResult(
        video_path=video_path,
        total_frames=frame_count,
        fps=fps,
        duration_seconds=duration,
        resolution=(width, height),
        players_tracked=len(player_tracks),
        processing_time_seconds=processing_time,
        player_data=player_tracks,
    )

    # --- Convert frame counts to minutes for each player ---
    for tid, pt in player_tracks.items():
        frame_span = pt.last_seen_frame - pt.first_seen_frame + 1
        # Overwrite estimated_minutes with actual calculation using FPS
        # (stored in the to_dict method via frame_span / fps)
        pass  # The property handles this

    # --- Save Results ---
    results_dict = result.to_dict()

    # Enrich with minute-based calculations
    for tid_str, pdata in results_dict["players"].items():
        pdata["estimated_minutes"] = round(
            pdata["estimated_minutes"] / fps, 1
        ) if fps > 0 else 0
        pdata["first_seen_minute"] = round(
            player_tracks[int(tid_str)].first_seen_frame / fps / 60, 1
        ) if fps > 0 else 0
        pdata["last_seen_minute"] = round(
            player_tracks[int(tid_str)].last_seen_frame / fps / 60, 1
        ) if fps > 0 else 0
        pdata["visibility_pct"] = round(
            pdata["frames_visible"] / frame_count * 100, 1
        ) if frame_count > 0 else 0

    # Save JSON
    json_path = output_path / "tracking_results.json"
    with open(json_path, "w") as f:
        json.dump(results_dict, f, indent=2, cls=NumpyEncoder)
    print(f"\nResults saved to {json_path}")

    # Save per-player summary CSV
    csv_path = output_path / "player_summary.csv"
    with open(csv_path, "w") as f:
        headers = [
            "track_id", "frames_visible", "estimated_minutes",
            "first_seen_minute", "last_seen_minute", "visibility_pct",
            "sprint_count", "avg_speed_px", "max_speed_px",
            "defensive_third_pct", "middle_third_pct", "attacking_third_pct"
        ]
        f.write(",".join(headers) + "\n")
        for tid_str, pdata in results_dict["players"].items():
            heat = pdata.get("heat_map", {}).get("zones", {})
            row = [
                tid_str,
                str(pdata["frames_visible"]),
                str(pdata["estimated_minutes"]),
                str(pdata.get("first_seen_minute", 0)),
                str(pdata.get("last_seen_minute", 0)),
                str(pdata.get("visibility_pct", 0)),
                str(pdata["sprint_count"]),
                str(pdata["avg_speed_px"]),
                str(pdata["max_speed_px"]),
                str(heat.get("defensive_third", 0)),
                str(heat.get("middle_third", 0)),
                str(heat.get("attacking_third", 0)),
            ]
            f.write(",".join(row) + "\n")
    print(f"Player summary saved to {csv_path}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"PROCESSING COMPLETE")
    print(f"=" * 60)
    print(f"  Video:           {video_path}")
    print(f"  Duration:        {duration:.1f}s ({duration/60:.1f} min)")
    print(f"  Frames:          {frame_count} ({processed_count} processed)")
    print(f"  Processing time: {processing_time:.1f}s")
    print(f"  Processing FPS:  {processed_count / processing_time:.1f}")
    print(f"  Players tracked: {len(player_tracks)}")
    if generate_annotated_video:
        print(f"  Annotated video: {output_path / 'annotated_output.mp4'}")
    print()

    # Top players by visibility
    sorted_players = sorted(
        results_dict["players"].items(),
        key=lambda x: x[1]["frames_visible"],
        reverse=True,
    )
    print(f"  Top tracked players:")
    for tid, pdata in sorted_players[:10]:
        print(f"    Player #{tid}: {pdata['estimated_minutes']:.1f} min, "
              f"{pdata['sprint_count']} sprints, "
              f"visibility {pdata['visibility_pct']:.0f}%")

    # -----------------------------------------------------------------------
    # Post-pipeline: Pose Analysis (MediaPipe)
    # -----------------------------------------------------------------------
    try:
        from pose_analysis import analyze_match_poses
        print("\n[Pose] Running MediaPipe pose analysis...")
        # Build a player list that includes bboxes/frame_indices for pose analysis
        players_for_pose = []
        for tid, pt in player_tracks.items():
            players_for_pose.append({
                "track_id": tid,
                "bboxes": pt.bboxes,
                "frame_indices": pt.frame_indices,
            })
        pose_input = {"players": players_for_pose}
        pose_results = analyze_match_poses(video_path, pose_input, sample_rate=30)
        results_dict["pose_analysis"] = pose_results
        print(f"[Pose] Analyzed {len(pose_results)} players")
        # Persist updated results
        with open(json_path, "w") as f:
            json.dump(results_dict, f, indent=2, cls=NumpyEncoder)
    except Exception as e:
        results_dict["pose_analysis"] = {"error": str(e)}
        print(f"[Pose] WARNING: Pose analysis failed: {e}")

    # -----------------------------------------------------------------------
    # Post-pipeline: Clip Extraction (FFmpeg)
    # -----------------------------------------------------------------------
    try:
        from clip_extractor import extract_player_clips, create_highlight_reel, generate_thumbnail
        print("\n[Clips] Extracting player clips...")
        clips_dir = str(output_path / "clips")
        # Build tracking data with bboxes/frame_indices for clip extraction
        clip_input = {
            "fps": fps,
            "players": players_for_pose,  # reuse list from pose analysis
        }
        player_clips = extract_player_clips(video_path, clip_input, clips_dir)
        results_dict["player_clips"] = {str(k): v for k, v in player_clips.items()}
        print(f"[Clips] Extracted clips for {len(player_clips)} players")

        # Create highlight reel
        highlight_path = str(output_path / "highlights.mp4")
        highlight = create_highlight_reel(video_path, {
            "fps": fps,
            "players": [
                {
                    "track_id": tid,
                    "frame_indices": pt.frame_indices,
                    "sprint_count": pt.sprint_count,
                    "max_speed_px": pt.max_speed,
                }
                for tid, pt in player_tracks.items()
            ]
        }, highlight_path)
        results_dict["highlight_reel"] = highlight
        if highlight:
            print(f"[Clips] Highlight reel: {highlight}")

        # Generate thumbnail from annotated video (or original)
        thumb_src = str(output_path / "annotated_output.mp4")
        if not Path(thumb_src).exists():
            thumb_src = video_path
        thumb_path = str(output_path / "thumbnail.jpg")
        thumb = generate_thumbnail(thumb_src, thumb_path)
        results_dict["thumbnail"] = thumb
        if thumb:
            print(f"[Clips] Thumbnail: {thumb}")

        # Persist updated results
        with open(json_path, "w") as f:
            json.dump(results_dict, f, indent=2, cls=NumpyEncoder)
    except Exception as e:
        results_dict["player_clips"] = {"error": str(e)}
        print(f"[Clips] WARNING: Clip extraction failed: {e}")

    return result


# ---------------------------------------------------------------------------
# AI Report Generation (Optional — requires API key)
# ---------------------------------------------------------------------------

def generate_scout_report(
    tracking_data: dict,
    match_context: dict = None,
    api_key: str = None,
) -> str:
    """
    Generate a natural language scout report from tracking data using an LLM.

    Args:
        tracking_data: Output from process_match_video().to_dict()
        match_context: Optional dict with match details (teams, competition, date)
        api_key: Gemini or Anthropic API key

    Returns:
        Scout report as a string
    """
    # Build prompt from tracking data
    match_info = match_context or {}
    prompt = f"""You are a professional football scout. Analyze this tracking data 
from a match and write a concise scouting report for each significant player.

Match Information:
- Duration: {tracking_data['duration_seconds'] / 60:.0f} minutes
- Competition: {match_info.get('competition', 'Unknown')}
- Teams: {match_info.get('home_team', 'Team A')} vs {match_info.get('away_team', 'Team B')}
- Date: {match_info.get('date', 'Unknown')}

Player Tracking Data:
"""
    for tid, pdata in tracking_data["players"].items():
        if pdata["estimated_minutes"] < 5:
            continue  # Skip briefly seen players
        prompt += f"""
Player #{tid}:
  - Estimated minutes: {pdata['estimated_minutes']}
  - Sprint count: {pdata['sprint_count']}
  - Max speed (relative): {pdata['max_speed_px']:.1f}
  - Avg speed (relative): {pdata['avg_speed_px']:.1f}
  - Pitch zones: {json.dumps(pdata.get('heat_map', {}).get('zones', {}))}
  - Visibility: {pdata.get('visibility_pct', 0):.0f}%
"""

    prompt += """
For each player with significant playing time, provide:
1. Estimated position based on their movement patterns and zones
2. Work rate assessment (based on sprint count and average speed)
3. Positional discipline (based on zone distribution)
4. Notable patterns
5. Overall assessment

Format as a structured report. Be specific and data-driven.
"""

    # If no API key, return the prompt for manual use
    if not api_key:
        return f"[Scout report prompt generated — pass to your preferred LLM]\n\n{prompt}"

    # Use Google Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text
    except ImportError:
        # Fallback: use Anthropic
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except ImportError:
            return f"[Install google-generativeai or anthropic to auto-generate reports]\n\n{prompt}"


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ScoutBase — Process match video through AI vision pipeline"
    )
    parser.add_argument("--video", required=True, help="Path to match video file")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument("--model", default="yolo11n.pt",
                       help="YOLO model (yolo11n.pt, yolo11s.pt, yolo11m.pt)")
    parser.add_argument("--confidence", type=float, default=0.3,
                       help="Detection confidence threshold")
    parser.add_argument("--no-video", action="store_true",
                       help="Skip annotated video generation")
    parser.add_argument("--max-frames", type=int, default=None,
                       help="Limit frames to process (for testing)")
    parser.add_argument("--skip-frames", type=int, default=1,
                       help="Process every Nth frame (1=all, 2=half, etc.)")
    parser.add_argument("--gemini-key", default=None,
                       help="Gemini API key for auto scout report generation")

    args = parser.parse_args()

    result = process_match_video(
        video_path=args.video,
        output_dir=args.output,
        model_path=args.model,
        confidence_threshold=args.confidence,
        generate_annotated_video=not args.no_video,
        max_frames=args.max_frames,
        process_every_n=args.skip_frames,
    )

    # Generate scout report if API key provided
    if args.gemini_key:
        print("\nGenerating AI scout report...")
        report = generate_scout_report(
            result.to_dict(),
            api_key=args.gemini_key,
        )
        report_path = Path(args.output) / "scout_report.txt"
        with open(report_path, "w") as f:
            f.write(report)
        print(f"Scout report saved to {report_path}")
