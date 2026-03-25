"""
ScoutBase — MediaPipe Pose Analysis Module
Extracts body mechanics from detected players for injury risk and performance assessment.
"""
import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple

mp_pose = mp.solutions.pose

@dataclass
class PoseMetrics:
    """Per-player pose analysis metrics across frames."""
    track_id: int
    frames_analyzed: int = 0
    avg_knee_angle_left: float = 0.0
    avg_knee_angle_right: float = 0.0
    avg_hip_angle_left: float = 0.0
    avg_hip_angle_right: float = 0.0
    avg_shoulder_symmetry: float = 0.0  # 0 = perfect symmetry, higher = asymmetric
    avg_body_lean: float = 0.0  # degrees from vertical
    stride_length_estimate: float = 0.0
    posture_degradation: float = 0.0  # how much posture worsens over time (fatigue indicator)
    asymmetry_score: float = 0.0  # overall body asymmetry (injury risk)
    sprint_form_score: float = 0.0  # 0-100 based on knee drive, arm swing, lean

    # Raw data for detailed analysis
    knee_angles_over_time: List[float] = field(default_factory=list)
    body_lean_over_time: List[float] = field(default_factory=list)

def calculate_angle(a, b, c):
    """Calculate angle at point b given three 2D points."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

def analyze_player_pose(frame: np.ndarray, bbox: Tuple[int,int,int,int]) -> Optional[Dict]:
    """
    Run MediaPipe Pose on a cropped player region.
    bbox = (x1, y1, x2, y2)
    Returns dict of landmark angles and metrics, or None if pose not detected.
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = frame.shape[:2]
    # Pad bbox slightly for better pose detection
    pad = 10
    x1, y1 = max(0, x1-pad), max(0, y1-pad)
    x2, y2 = min(w, x2+pad), min(h, y2+pad)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0 or crop.shape[0] < 50 or crop.shape[1] < 30:
        return None

    with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.3) as pose:
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if not results.pose_landmarks:
            return None

        lm = results.pose_landmarks.landmark
        ch, cw = crop.shape[:2]

        def pt(idx):
            return (lm[idx].x * cw, lm[idx].y * ch)

        # Key angles
        try:
            left_knee_angle = calculate_angle(pt(23), pt(25), pt(27))  # hip-knee-ankle
            right_knee_angle = calculate_angle(pt(24), pt(26), pt(28))
            left_hip_angle = calculate_angle(pt(11), pt(23), pt(25))  # shoulder-hip-knee
            right_hip_angle = calculate_angle(pt(12), pt(24), pt(26))

            # Shoulder symmetry
            left_shoulder = pt(11)
            right_shoulder = pt(12)
            shoulder_diff = abs(left_shoulder[1] - right_shoulder[1])

            # Body lean (angle of spine from vertical)
            mid_shoulder = ((left_shoulder[0]+right_shoulder[0])/2, (left_shoulder[1]+right_shoulder[1])/2)
            mid_hip = ((lm[23].x*cw + lm[24].x*cw)/2, (lm[23].y*ch + lm[24].y*ch)/2)
            spine_dx = mid_shoulder[0] - mid_hip[0]
            spine_dy = mid_shoulder[1] - mid_hip[1]
            body_lean = abs(np.degrees(np.arctan2(spine_dx, -spine_dy)))

            return {
                "left_knee_angle": round(left_knee_angle, 1),
                "right_knee_angle": round(right_knee_angle, 1),
                "left_hip_angle": round(left_hip_angle, 1),
                "right_hip_angle": round(right_hip_angle, 1),
                "shoulder_symmetry": round(shoulder_diff, 1),
                "body_lean": round(body_lean, 1),
                "knee_asymmetry": round(abs(left_knee_angle - right_knee_angle), 1),
            }
        except (IndexError, ValueError):
            return None

def analyze_match_poses(video_path: str, tracking_results: Dict, sample_rate: int = 30) -> Dict[int, Dict]:
    """
    Run pose analysis on tracked players from a processed match.

    Args:
        video_path: Path to original video
        tracking_results: Dict from process_match containing player tracking data
        sample_rate: Analyze every Nth frame (default: every 30th = 1/sec at 30fps)

    Returns:
        Dict mapping track_id -> PoseMetrics as dict
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {}

    # Build frame -> [(track_id, bbox)] lookup from tracking data
    players_data = tracking_results.get("players", [])

    # Handle both dict (from to_dict()) and list formats
    if isinstance(players_data, dict):
        players_list = []
        for tid_str, pdata in players_data.items():
            pdata["track_id"] = int(tid_str)
            players_list.append(pdata)
        players_data = players_list

    pose_data = {}  # track_id -> list of frame metrics
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % sample_rate != 0:
            frame_num += 1
            continue

        # For each tracked player, find their bbox at this frame
        for player in players_data:
            tid = player.get("track_id", 0)
            bboxes = player.get("bboxes", [])
            frame_indices = player.get("frame_indices", [])

            if frame_num in frame_indices:
                idx = frame_indices.index(frame_num)
                if idx < len(bboxes):
                    bbox = bboxes[idx]
                    metrics = analyze_player_pose(frame, bbox)
                    if metrics:
                        if tid not in pose_data:
                            pose_data[tid] = []
                        pose_data[tid].append(metrics)

        frame_num += 1

    cap.release()

    # Aggregate per-player
    results = {}
    for tid, frames in pose_data.items():
        if not frames:
            continue

        n = len(frames)
        avg = lambda key: round(sum(f.get(key, 0) for f in frames) / n, 1)

        # Calculate posture degradation (compare first half vs second half)
        mid = n // 2
        if mid > 0:
            first_lean = sum(f.get("body_lean", 0) for f in frames[:mid]) / mid
            second_lean = sum(f.get("body_lean", 0) for f in frames[mid:]) / (n - mid)
            degradation = round(second_lean - first_lean, 1)
        else:
            degradation = 0.0

        # Sprint form score (heuristic: good knee drive + slight forward lean + symmetry)
        avg_knee = (avg("left_knee_angle") + avg("right_knee_angle")) / 2
        avg_lean = avg("body_lean")
        asymmetry = avg("knee_asymmetry")

        # Score: optimal knee ~90-110, lean ~5-15, low asymmetry
        knee_score = max(0, 100 - abs(avg_knee - 100) * 2)
        lean_score = max(0, 100 - abs(avg_lean - 10) * 5)
        sym_score = max(0, 100 - asymmetry * 5)
        sprint_score = round((knee_score + lean_score + sym_score) / 3)

        results[tid] = {
            "track_id": tid,
            "frames_analyzed": n,
            "avg_knee_angle_left": avg("left_knee_angle"),
            "avg_knee_angle_right": avg("right_knee_angle"),
            "avg_hip_angle_left": avg("left_hip_angle"),
            "avg_hip_angle_right": avg("right_hip_angle"),
            "shoulder_symmetry": avg("shoulder_symmetry"),
            "body_lean": avg("body_lean"),
            "knee_asymmetry": avg("knee_asymmetry"),
            "posture_degradation": degradation,
            "sprint_form_score": sprint_score,
            "body_lean_over_time": [f.get("body_lean", 0) for f in frames],
        }

    return results
