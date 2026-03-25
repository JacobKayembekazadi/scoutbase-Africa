"""
ScoutBase — FFmpeg Player Clip Extraction
Extracts individual player clips and highlight reels from processed match footage.
"""
import subprocess
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def extract_player_clips(
    video_path: str,
    tracking_data: Dict,
    output_dir: str,
    min_clip_seconds: float = 2.0,
    max_clip_seconds: float = 10.0,
    padding_seconds: float = 1.0
) -> Dict[int, List[str]]:
    """
    Extract video clips for each tracked player's key moments.

    Returns dict mapping track_id -> list of clip file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    fps = tracking_data.get("fps", 30)
    clips = {}

    players_data = tracking_data.get("players", [])

    # Handle both dict (from to_dict()) and list formats
    if isinstance(players_data, dict):
        players_list = []
        for tid_str, pdata in players_data.items():
            pdata["track_id"] = int(tid_str)
            players_list.append(pdata)
        players_data = players_list

    for player in players_data:
        tid = player.get("track_id", 0)
        frames = player.get("frame_indices", [])

        if not frames or len(frames) < fps * min_clip_seconds:
            continue

        # Find continuous segments where player is visible
        segments = _find_segments(frames, gap_threshold=int(fps*2))
        player_clips = []

        for i, (start_frame, end_frame) in enumerate(segments[:5]):  # Max 5 clips per player
            start_sec = max(0, start_frame / fps - padding_seconds)
            duration = min(max_clip_seconds, (end_frame - start_frame) / fps + padding_seconds * 2)

            if duration < min_clip_seconds:
                continue

            output_path = os.path.join(output_dir, f"player_{tid}_clip_{i}.mp4")

            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.2f}",
                "-i", video_path,
                "-t", f"{duration:.2f}",
                "-c:v", "libx264", "-preset", "fast",
                "-crf", "23",
                "-an",  # no audio for clips
                output_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, timeout=30)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    player_clips.append(output_path)
            except (subprocess.TimeoutExpired, Exception):
                continue

        if player_clips:
            clips[tid] = player_clips

    return clips


def create_highlight_reel(
    video_path: str,
    tracking_data: Dict,
    output_path: str,
    max_duration: float = 180.0,  # 3 minute highlight reel
    top_n_players: int = 5
) -> Optional[str]:
    """
    Create a highlight reel from the top N most active players.
    Selects highest-activity segments based on sprint count and speed.
    """
    fps = tracking_data.get("fps", 30)
    players = tracking_data.get("players", [])

    # Handle both dict (from to_dict()) and list formats
    if isinstance(players, dict):
        players_list = []
        for tid_str, pdata in players.items():
            pdata["track_id"] = int(tid_str)
            players_list.append(pdata)
        players = players_list

    if not players:
        return None

    # Rank players by activity (sprints + max speed)
    ranked = sorted(players, key=lambda p: (
        p.get("sprint_count", 0) * 2 + p.get("max_speed_px", p.get("max_speed", 0))
    ), reverse=True)[:top_n_players]

    # Collect best segments from top players
    segments = []
    for player in ranked:
        frames = player.get("frame_indices", [])
        if not frames:
            continue

        # Find segments with highest density (most action)
        player_segments = _find_segments(frames, gap_threshold=int(fps*2))
        for start, end in player_segments[:2]:
            start_sec = max(0, start / fps - 0.5)
            end_sec = end / fps + 0.5
            duration = end_sec - start_sec
            if duration >= 2.0:
                segments.append((start_sec, min(duration, 10.0)))

    if not segments:
        return None

    # Sort by time and limit total duration
    segments.sort(key=lambda s: s[0])

    # Create concat file for ffmpeg
    concat_dir = os.path.dirname(output_path)
    os.makedirs(concat_dir, exist_ok=True)
    concat_file = os.path.join(concat_dir, "concat_list.txt")

    temp_clips = []
    total_duration = 0

    for i, (start, dur) in enumerate(segments):
        if total_duration + dur > max_duration:
            break

        temp_path = os.path.join(concat_dir, f"_temp_highlight_{i}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start:.2f}",
            "-i", video_path,
            "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "23", "-an",
            temp_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                temp_clips.append(temp_path)
                total_duration += dur
        except Exception:
            continue

    if not temp_clips:
        return None

    # Concatenate clips
    with open(concat_file, "w") as f:
        for clip in temp_clips:
            f.write(f"file '{clip}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=60)
    except Exception:
        pass

    # Cleanup temp files
    for clip in temp_clips:
        try:
            os.remove(clip)
        except Exception:
            pass
    try:
        os.remove(concat_file)
    except Exception:
        pass

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    return None


def generate_thumbnail(video_path: str, output_path: str, timestamp: float = 1.0) -> Optional[str]:
    """Extract a single frame as a thumbnail JPEG."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.2f}",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
        if os.path.exists(output_path):
            return output_path
    except Exception:
        pass
    return None


def _find_segments(frame_indices: List[int], gap_threshold: int = 60) -> List[Tuple[int, int]]:
    """Find continuous segments in frame indices."""
    if not frame_indices:
        return []

    segments = []
    start = frame_indices[0]
    prev = frame_indices[0]

    for f in frame_indices[1:]:
        if f - prev > gap_threshold:
            segments.append((start, prev))
            start = f
        prev = f
    segments.append((start, prev))
    return segments
