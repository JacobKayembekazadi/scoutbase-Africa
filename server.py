"""
ScoutBase Africa — Processing API Server
=========================================
FastAPI server that accepts video uploads and processes them through
the YOLO + ByteTrack pipeline. Stores results in Supabase.

Run:
    uvicorn server:app --host 0.0.0.0 --port 8000

Or with auto-reload for development:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import uuid
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from process_match import process_match_video, generate_scout_report

# SAM3 Integration (optional)
try:
    from sam3 import (
        SAM3Processor,
        SAM3StatusResponse,
        SegmentationRequest,
        SegmentationResponse,
        TrackingRequest,
        TrackingResponse,
        TeamSegmentationRequest,
        TeamSegmentationResponse,
        EnhanceTracksRequest,
        EnhanceTracksResponse,
    )
    sam3_processor = SAM3Processor()
    SAM3_AVAILABLE = True
except ImportError as e:
    SAM3_AVAILABLE = False
    sam3_processor = None
    print(f"SAM3 module not available: {e}")

# Optional: Supabase integration
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    supabase: Optional[Client] = (
        create_client(SUPABASE_URL, SUPABASE_KEY)
        if SUPABASE_URL and SUPABASE_KEY
        else None
    )
except ImportError:
    supabase = None

app = FastAPI(
    title="ScoutBase Processing API",
    description="Video processing pipeline for player tracking and analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (use Redis/DB in production)
jobs: dict = {}
players_db: Dict[int, dict] = {}
shortlist_db: set = set()
track_assignments: Dict[str, Dict[int, dict]] = {}  # {job_id: {track_id: assignment}}
next_player_id = 1

UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProcessingJob(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    video_filename: str
    created_at: str
    completed_at: Optional[str] = None
    match_id: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    competition: Optional[str] = None
    results_path: Optional[str] = None
    error: Optional[str] = None
    progress: float = 0.0
    players_tracked: int = 0


class ProcessingRequest(BaseModel):
    match_id: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    competition: Optional[str] = None
    match_date: Optional[str] = None
    model: str = "yolo11n.pt"
    confidence: float = 0.3
    generate_video: bool = True
    skip_frames: int = 1


# Player Models
class PlayerStats(BaseModel):
    appearances: int = 0
    goals: int = 0
    assists: int = 0
    minutes: int = 0
    cards: dict = {"yellow": 0, "red": 0}


class CareerEntry(BaseModel):
    club: str
    period: str
    level: str
    apps: Optional[int] = None


class MedicalInfo(BaseModel):
    injuries: Optional[int] = None
    lastInjury: str = "None"
    clearance: str = "Unknown"
    fitnessScore: Optional[int] = None


class BehavioralInfo(BaseModel):
    training: Optional[int] = None
    discipline: str = "Unknown"
    languages: List[str] = []
    leadership: str = "N/A"


class ContractInfo(BaseModel):
    status: str = "Unknown"
    expiry: str = "Unknown"
    compensation: str = "Unknown"
    tms: str = "Unknown"


class PlayerBase(BaseModel):
    name: str
    age: int
    nation: str
    flag: str
    club: str
    league: str
    position: str
    photo: Optional[str] = None
    verificationStatus: str = "unverified"
    reliabilityScore: int = 0
    dataConfidence: int = 0
    stats: PlayerStats = PlayerStats()
    career: List[CareerEntry] = []
    medical: MedicalInfo = MedicalInfo()
    behavioral: BehavioralInfo = BehavioralInfo()
    contract: ContractInfo = ContractInfo()
    matchClips: int = 0
    fullMatches: int = 0
    scoutNotes: str = ""


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    nation: Optional[str] = None
    flag: Optional[str] = None
    club: Optional[str] = None
    league: Optional[str] = None
    position: Optional[str] = None
    photo: Optional[str] = None
    verificationStatus: Optional[str] = None
    reliabilityScore: Optional[int] = None
    dataConfidence: Optional[int] = None
    stats: Optional[PlayerStats] = None
    career: Optional[List[CareerEntry]] = None
    medical: Optional[MedicalInfo] = None
    behavioral: Optional[BehavioralInfo] = None
    contract: Optional[ContractInfo] = None
    matchClips: Optional[int] = None
    fullMatches: Optional[int] = None
    scoutNotes: Optional[str] = None


class Player(PlayerBase):
    id: int


class LeagueIntel(BaseModel):
    name: str
    country: str
    strength: float
    reliability: int
    clubs: int
    risk: str


class TrackAssignment(BaseModel):
    player_id: int
    notes: Optional[str] = None


class PlayerCreateFromTrack(BaseModel):
    name: str
    age: int = 0
    nation: str = "Unknown"
    flag: str = "🏳️"
    club: str = "Unknown"
    league: str = "Unknown"
    position: str = "Unknown"
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Background Processing Task
# ---------------------------------------------------------------------------

async def process_video_task(job_id: str, video_path: str, config: dict):
    """Run the vision pipeline in the background."""
    job = jobs[job_id]
    job["status"] = "processing"
    job["progress"] = 0.1

    output_dir = RESULTS_DIR / job_id

    try:
        # Run the CPU/GPU-intensive processing in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_match_video(
                video_path=video_path,
                output_dir=str(output_dir),
                model_path=config.get("model", "yolo11n.pt"),
                confidence_threshold=config.get("confidence", 0.3),
                generate_annotated_video=config.get("generate_video", True),
                process_every_n=config.get("skip_frames", 1),
            )
        )

        results_dict = result.to_dict()

        # Generate AI scout report if API key is available
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            match_context = {
                "competition": config.get("competition", "Unknown"),
                "home_team": config.get("home_team", "Team A"),
                "away_team": config.get("away_team", "Team B"),
                "date": config.get("match_date", "Unknown"),
            }
            report = await loop.run_in_executor(
                None,
                lambda: generate_scout_report(results_dict, match_context, gemini_key)
            )
            report_path = output_dir / "scout_report.txt"
            with open(report_path, "w") as f:
                f.write(report)
            results_dict["scout_report"] = report

        # Store in Supabase if configured
        if supabase:
            await store_results_in_supabase(job_id, config, results_dict)

        # Update job
        job["status"] = "completed"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        job["results_path"] = str(output_dir)
        job["players_tracked"] = result.players_tracked
        job["progress"] = 1.0

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["progress"] = 0.0
        print(f"Processing failed for job {job_id}: {e}")
        import traceback
        traceback.print_exc()


async def store_results_in_supabase(job_id: str, config: dict, results: dict):
    """Store processing results in Supabase database."""
    if not supabase:
        return

    # Create match record
    match_data = {
        "id": config.get("match_id") or str(uuid.uuid4()),
        "home_team": config.get("home_team"),
        "away_team": config.get("away_team"),
        "competition": config.get("competition"),
        "match_date": config.get("match_date"),
        "processing_job_id": job_id,
        "total_frames": results.get("total_frames"),
        "duration_seconds": results.get("duration_seconds"),
        "players_tracked": results.get("players_tracked"),
    }
    supabase.table("matches").upsert(match_data).execute()

    # Store per-player tracking data
    for track_id, player_data in results.get("players", {}).items():
        tracking_record = {
            "id": str(uuid.uuid4()),
            "match_id": match_data["id"],
            "track_id": int(track_id),
            "frames_visible": player_data["frames_visible"],
            "estimated_minutes": player_data["estimated_minutes"],
            "sprint_count": player_data["sprint_count"],
            "avg_speed": player_data["avg_speed_px"],
            "max_speed": player_data["max_speed_px"],
            "heat_map": player_data.get("heat_map"),
            "visibility_pct": player_data.get("visibility_pct"),
            "first_seen_minute": player_data.get("first_seen_minute"),
            "last_seen_minute": player_data.get("last_seen_minute"),
        }
        supabase.table("tracking_data").insert(tracking_record).execute()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "supabase_connected": supabase is not None,
        "jobs_in_memory": len(jobs),
    }


@app.post("/process")
async def start_processing(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    home_team: str = Form(default=""),
    away_team: str = Form(default=""),
    competition: str = Form(default=""),
    match_date: str = Form(default=""),
    model: str = Form(default="yolo11n.pt"),
    confidence: float = Form(default=0.3),
    generate_video: bool = Form(default=True),
    skip_frames: int = Form(default=1),
):
    """Upload a match video and start processing."""
    # Validate file type
    allowed_types = [
        "video/mp4", "video/avi", "video/quicktime",
        "video/x-msvideo", "video/webm",
    ]
    if video.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported video type: {video.content_type}")

    # Create job
    job_id = str(uuid.uuid4())[:12]
    video_path = UPLOAD_DIR / f"{job_id}_{video.filename}"

    # Save uploaded video
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    # Create job record
    config = {
        "home_team": home_team,
        "away_team": away_team,
        "competition": competition,
        "match_date": match_date,
        "model": model,
        "confidence": confidence,
        "generate_video": generate_video,
        "skip_frames": skip_frames,
    }

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "video_filename": video.filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0.0,
        "players_tracked": 0,
        **{k: v for k, v in config.items()},
    }

    # Start background processing
    background_tasks.add_task(process_video_task, job_id, str(video_path), config)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video uploaded. Processing started.",
    }


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """Check processing job status."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/results/{job_id}")
async def get_results(job_id: str):
    """Get processing results for a completed job."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        return {"status": job["status"], "message": "Processing not yet complete"}

    results_path = Path(job["results_path"]) / "tracking_results.json"
    if not results_path.exists():
        raise HTTPException(500, "Results file not found")

    with open(results_path) as f:
        results = json.load(f)

    # Include scout report if available
    report_path = Path(job["results_path"]) / "scout_report.txt"
    if report_path.exists():
        with open(report_path) as f:
            results["scout_report"] = f.read()

    return results


@app.get("/results/{job_id}/video")
async def get_annotated_video(job_id: str):
    """Download the annotated video with tracking overlays."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Processing not yet complete")

    video_path = Path(job["results_path"]) / "annotated_output.mp4"
    if not video_path.exists():
        raise HTTPException(404, "Annotated video not available")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"scoutbase_tracked_{job_id}.mp4",
    )


@app.get("/results/{job_id}/frame/{frame_number}")
async def get_video_frame(job_id: str, frame_number: int):
    """Extract and return a single frame from the video as JPEG image."""
    import cv2
    import io
    from fastapi.responses import StreamingResponse

    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Processing not yet complete")

    # Try annotated video first, fall back to original
    video_path = Path(job["results_path"]) / "annotated_output.mp4"
    if not video_path.exists():
        # Try to find original upload
        uploads_dir = Path("uploads")
        video_files = list(uploads_dir.glob(f"{job_id}_*"))
        if video_files:
            video_path = video_files[0]
        else:
            raise HTTPException(404, "Video file not found")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(500, "Failed to open video file")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_number < 0 or frame_number >= total_frames:
            raise HTTPException(400, f"Frame number must be between 0 and {total_frames - 1}")

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            raise HTTPException(500, f"Failed to read frame {frame_number}")

        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        return StreamingResponse(
            io.BytesIO(buffer.tobytes()),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"inline; filename=frame_{frame_number}.jpg"}
        )
    finally:
        cap.release()


@app.get("/results/{job_id}/info")
async def get_video_info(job_id: str):
    """Get video metadata including total frames, fps, and duration."""
    import cv2

    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Processing not yet complete")

    video_path = Path(job["results_path"]) / "annotated_output.mp4"
    if not video_path.exists():
        uploads_dir = Path("uploads")
        video_files = list(uploads_dir.glob(f"{job_id}_*"))
        if video_files:
            video_path = video_files[0]
        else:
            raise HTTPException(404, "Video file not found")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(500, "Failed to open video file")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0

        return {
            "total_frames": total_frames,
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "duration_seconds": round(duration, 2),
        }
    finally:
        cap.release()


@app.get("/results/{job_id}/csv")
async def get_player_csv(job_id: str):
    """Download player summary CSV."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Processing not yet complete")

    csv_path = Path(job["results_path"]) / "player_summary.csv"
    if not csv_path.exists():
        raise HTTPException(404, "CSV not available")

    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"scoutbase_players_{job_id}.csv",
    )


@app.get("/jobs")
async def list_jobs():
    """List all processing jobs."""
    return {
        "jobs": sorted(
            jobs.values(),
            key=lambda j: j["created_at"],
            reverse=True,
        )
    }


# ---------------------------------------------------------------------------
# Track Assignment Endpoints
# ---------------------------------------------------------------------------

@app.get("/results/{job_id}/tracks")
async def get_job_tracks(job_id: str):
    """Get all tracks from a job with their assignments."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        return {"status": job["status"], "message": "Processing not yet complete"}

    results_path = Path(job["results_path"]) / "tracking_results.json"
    if not results_path.exists():
        raise HTTPException(500, "Results file not found")

    with open(results_path) as f:
        results = json.load(f)

    # Get assignments for this job
    job_assignments = track_assignments.get(job_id, {})

    # Build tracks list with assignments
    tracks = []
    for track_id_str, player_data in results.get("players", {}).items():
        track_id = int(track_id_str)
        assignment = job_assignments.get(track_id)

        track_info = {
            "track_id": track_id,
            "frames_visible": player_data.get("frames_visible", 0),
            "estimated_minutes": player_data.get("estimated_minutes", 0),
            "sprint_count": player_data.get("sprint_count", 0),
            "avg_speed_px": player_data.get("avg_speed_px", 0),
            "max_speed_px": player_data.get("max_speed_px", 0),
            "heat_map": player_data.get("heat_map"),
            "visibility_pct": player_data.get("visibility_pct", 0),
            "first_seen_minute": player_data.get("first_seen_minute", 0),
            "last_seen_minute": player_data.get("last_seen_minute", 0),
        }

        if assignment:
            player = players_db.get(assignment["player_id"])
            track_info["assignment"] = {
                "player_id": assignment["player_id"],
                "player_name": player["name"] if player else "Unknown",
                "assigned_at": assignment["assigned_at"],
                "notes": assignment.get("notes"),
            }

        tracks.append(track_info)

    # Sort by track_id
    tracks.sort(key=lambda t: t["track_id"])

    return {
        "job_id": job_id,
        "total_tracks": len(tracks),
        "assigned_count": len(job_assignments),
        "tracks": tracks,
    }


@app.post("/results/{job_id}/tracks/{track_id}/assign")
async def assign_track(job_id: str, track_id: int, assignment: TrackAssignment):
    """Assign a track to an existing player."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Job not yet completed")

    # Verify player exists
    if assignment.player_id not in players_db:
        raise HTTPException(404, f"Player {assignment.player_id} not found")

    # Verify track exists in results
    results_path = Path(job["results_path"]) / "tracking_results.json"
    if not results_path.exists():
        raise HTTPException(500, "Results file not found")

    with open(results_path) as f:
        results = json.load(f)

    if str(track_id) not in results.get("players", {}):
        raise HTTPException(404, f"Track {track_id} not found in job results")

    # Create or update assignment
    if job_id not in track_assignments:
        track_assignments[job_id] = {}

    track_assignments[job_id][track_id] = {
        "player_id": assignment.player_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "notes": assignment.notes,
    }

    player = players_db[assignment.player_id]
    return {
        "message": f"Track #{track_id} assigned to {player['name']}",
        "assignment": track_assignments[job_id][track_id],
    }


@app.post("/results/{job_id}/tracks/{track_id}/create-player")
async def create_player_from_track(job_id: str, track_id: int, player_data: PlayerCreateFromTrack):
    """Create a new player and assign this track to them."""
    global next_player_id

    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Job not yet completed")

    # Verify track exists
    results_path = Path(job["results_path"]) / "tracking_results.json"
    if not results_path.exists():
        raise HTTPException(500, "Results file not found")

    with open(results_path) as f:
        results = json.load(f)

    if str(track_id) not in results.get("players", {}):
        raise HTTPException(404, f"Track {track_id} not found in job results")

    # Create the new player
    new_player = {
        "id": next_player_id,
        "name": player_data.name,
        "age": player_data.age,
        "nation": player_data.nation,
        "flag": player_data.flag,
        "club": player_data.club,
        "league": player_data.league,
        "position": player_data.position,
        "photo": None,
        "verificationStatus": "unverified",
        "reliabilityScore": 0,
        "dataConfidence": 0,
        "stats": {"appearances": 0, "goals": 0, "assists": 0, "minutes": 0, "cards": {"yellow": 0, "red": 0}},
        "career": [],
        "medical": {"injuries": None, "lastInjury": "None", "clearance": "Unknown", "fitnessScore": None},
        "behavioral": {"training": None, "discipline": "Unknown", "languages": [], "leadership": "N/A"},
        "contract": {"status": "Unknown", "expiry": "Unknown", "compensation": "Unknown", "tms": "Unknown"},
        "matchClips": 0,
        "fullMatches": 0,
        "scoutNotes": player_data.notes or f"Created from video tracking (Job: {job_id}, Track: #{track_id})",
    }

    players_db[next_player_id] = new_player

    # Assign track to new player
    if job_id not in track_assignments:
        track_assignments[job_id] = {}

    track_assignments[job_id][track_id] = {
        "player_id": next_player_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "notes": player_data.notes,
    }

    next_player_id += 1

    return {
        "message": f"Created player '{new_player['name']}' and assigned Track #{track_id}",
        "player": new_player,
        "assignment": track_assignments[job_id][track_id],
    }


@app.delete("/results/{job_id}/tracks/{track_id}/unassign")
async def unassign_track(job_id: str, track_id: int):
    """Remove track assignment."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    if job_id not in track_assignments or track_id not in track_assignments[job_id]:
        raise HTTPException(404, "Assignment not found")

    del track_assignments[job_id][track_id]

    return {"message": f"Track #{track_id} unassigned"}


# ---------------------------------------------------------------------------
# Player Endpoints
# ---------------------------------------------------------------------------

@app.get("/players")
async def get_players(
    nation: Optional[str] = None,
    league: Optional[str] = None,
    position: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all players with optional filtering."""
    result = list(players_db.values())

    if nation:
        result = [p for p in result if p["nation"].lower() == nation.lower()]
    if league:
        result = [p for p in result if p["league"].lower() == league.lower()]
    if position:
        result = [p for p in result if p["position"].lower() == position.lower()]
    if search:
        search_lower = search.lower()
        result = [p for p in result if
                  search_lower in p["name"].lower() or
                  search_lower in p["club"].lower()]

    return {"players": result, "total": len(result)}


@app.get("/players/{player_id}")
async def get_player(player_id: int):
    """Get a single player by ID."""
    if player_id not in players_db:
        raise HTTPException(404, "Player not found")
    return players_db[player_id]


@app.post("/players")
async def create_player(player: PlayerCreate):
    """Create a new player."""
    global next_player_id
    player_dict = player.model_dump()
    player_dict["id"] = next_player_id
    players_db[next_player_id] = player_dict
    next_player_id += 1
    return player_dict


@app.put("/players/{player_id}")
async def update_player(player_id: int, player_update: PlayerUpdate):
    """Update an existing player."""
    if player_id not in players_db:
        raise HTTPException(404, "Player not found")

    existing = players_db[player_id]
    update_data = player_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None:
            existing[key] = value if not isinstance(value, BaseModel) else value.model_dump()

    return existing


# ---------------------------------------------------------------------------
# League Intelligence Endpoints
# ---------------------------------------------------------------------------

LEAGUE_INTEL_DATA = [
    {"name": "Rwanda Premier League", "country": "🇷🇼", "strength": 3.2, "reliability": 78, "clubs": 16, "risk": "Low"},
    {"name": "South Africa PSL", "country": "🇿🇦", "strength": 5.8, "reliability": 91, "clubs": 16, "risk": "Low"},
    {"name": "Burundi Primus League", "country": "🇧🇮", "strength": 1.8, "reliability": 34, "clubs": 16, "risk": "Medium"},
    {"name": "Tanzania Premier League", "country": "🇹🇿", "strength": 3.5, "reliability": 65, "clubs": 16, "risk": "Low"},
    {"name": "Kenya Premier League", "country": "🇰🇪", "strength": 3.8, "reliability": 72, "clubs": 18, "risk": "Low"},
    {"name": "Uganda Premier League", "country": "🇺🇬", "strength": 2.9, "reliability": 58, "clubs": 16, "risk": "Medium"},
]


@app.get("/leagues")
async def get_leagues():
    """Get league intelligence data."""
    return {"leagues": LEAGUE_INTEL_DATA}


# ---------------------------------------------------------------------------
# Shortlist Endpoints
# ---------------------------------------------------------------------------

@app.get("/shortlist")
async def get_shortlist():
    """Get the current shortlist of player IDs."""
    return {"shortlist": list(shortlist_db)}


@app.post("/shortlist/{player_id}")
async def add_to_shortlist(player_id: int):
    """Add a player to the shortlist."""
    if player_id not in players_db:
        raise HTTPException(404, "Player not found")
    shortlist_db.add(player_id)
    return {"message": f"Player {player_id} added to shortlist", "shortlist": list(shortlist_db)}


@app.delete("/shortlist/{player_id}")
async def remove_from_shortlist(player_id: int):
    """Remove a player from the shortlist."""
    shortlist_db.discard(player_id)
    return {"message": f"Player {player_id} removed from shortlist", "shortlist": list(shortlist_db)}


# ---------------------------------------------------------------------------
# SAM3 Endpoints
# ---------------------------------------------------------------------------

@app.get("/sam3/status")
async def sam3_status():
    """Check SAM3 module status and availability."""
    if not SAM3_AVAILABLE:
        return {
            "available": False,
            "model_loaded": False,
            "error": "SAM3 module not installed. Install with: pip install transformers huggingface-hub",
        }

    try:
        status = sam3_processor.get_status()
        return SAM3StatusResponse(**status)
    except Exception as e:
        return {
            "available": False,
            "model_loaded": False,
            "error": str(e),
        }


@app.post("/sam3/segment")
async def sam3_segment(request: SegmentationRequest):
    """
    Perform text-prompted segmentation on a single frame.

    Example:
        POST /sam3/segment
        {
            "job_id": "abc123",
            "frame_number": 100,
            "prompt": "players in blue jerseys",
            "confidence_threshold": 0.5
        }
    """
    if not SAM3_AVAILABLE:
        raise HTTPException(503, "SAM3 module not available")

    try:
        result = sam3_processor.segment_frame(request)
        return result
    except Exception as e:
        raise HTTPException(500, f"Segmentation failed: {e}")


@app.post("/sam3/track")
async def sam3_track(request: TrackingRequest, background_tasks: BackgroundTasks):
    """
    Track objects through video frames using SAM3.

    This endpoint processes video frames and returns tracking data.
    For long videos, consider using lower sample_rate.

    Example:
        POST /sam3/track
        {
            "job_id": "abc123",
            "prompt": "goalkeeper",
            "start_frame": 0,
            "end_frame": 1000,
            "sample_rate": 10
        }
    """
    if not SAM3_AVAILABLE:
        raise HTTPException(503, "SAM3 module not available")

    try:
        # For now, run synchronously. For long videos, add background processing.
        result = sam3_processor.track_video(request)
        return result
    except Exception as e:
        raise HTTPException(500, f"Tracking failed: {e}")


@app.post("/sam3/teams")
async def sam3_teams(request: TeamSegmentationRequest):
    """
    Segment players into teams based on jersey colors.

    Example:
        POST /sam3/teams
        {
            "job_id": "abc123",
            "frame_number": 500,
            "home_color_hint": "blue",
            "away_color_hint": "red",
            "include_ball": true
        }
    """
    if not SAM3_AVAILABLE:
        raise HTTPException(503, "SAM3 module not available")

    try:
        result = sam3_processor.segment_teams(request)
        return result
    except Exception as e:
        raise HTTPException(500, f"Team segmentation failed: {e}")


@app.post("/sam3/enhance/{job_id}/tracks")
async def sam3_enhance_tracks(job_id: str, request: EnhanceTracksRequest):
    """
    Enhance existing ByteTrack results with SAM3 analysis.

    This links SAM3 segmentation data to existing tracking results,
    adding team labels, dominant colors, and optional mask data.

    Example:
        POST /sam3/enhance/abc123/tracks
        {
            "prompt": "football player",
            "add_masks": false,
            "add_team_labels": true,
            "sample_frames": 20
        }
    """
    if not SAM3_AVAILABLE:
        raise HTTPException(503, "SAM3 module not available")

    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Job processing not yet complete")

    try:
        result = sam3_processor.enhance_tracks(job_id, request)
        return result
    except Exception as e:
        raise HTTPException(500, f"Track enhancement failed: {e}")


# ---------------------------------------------------------------------------
# Seed Demo Data
# ---------------------------------------------------------------------------

def seed_demo_data():
    """Seed the database with demo players on startup."""
    global next_player_id

    demo_players = [
        {
            "name": "Jean-Baptiste Mugisha", "age": 22, "nation": "Rwanda", "flag": "🇷🇼",
            "club": "APR FC", "league": "Rwanda Premier League", "position": "CM",
            "photo": None, "verificationStatus": "verified",
            "reliabilityScore": 87, "dataConfidence": 92,
            "stats": {"appearances": 68, "goals": 12, "assists": 19, "minutes": 5840, "cards": {"yellow": 6, "red": 0}},
            "career": [
                {"club": "APR FC", "period": "2023–Present", "level": "1st Division", "apps": 68},
                {"club": "Rayon Sports Academy", "period": "2020–2023", "level": "Academy", "apps": 45},
            ],
            "medical": {"injuries": 1, "lastInjury": "Minor hamstring strain", "clearance": "Full", "fitnessScore": 91},
            "behavioral": {"training": 96, "discipline": "Excellent", "languages": ["Kinyarwanda", "French", "English"], "leadership": "Emerging captain"},
            "contract": {"status": "Active", "expiry": "June 2027", "compensation": "Eligible", "tms": "Registered"},
            "matchClips": 14, "fullMatches": 6,
            "scoutNotes": "Exceptional work rate, intelligent off-ball movement. Strong in tight spaces. Ready for European 2nd tier.",
        },
        {
            "name": "Thabo Molefe", "age": 20, "nation": "South Africa", "flag": "🇿🇦",
            "club": "Orlando Pirates", "league": "PSL", "position": "LW",
            "photo": None, "verificationStatus": "verified",
            "reliabilityScore": 91, "dataConfidence": 95,
            "stats": {"appearances": 42, "goals": 15, "assists": 8, "minutes": 3200, "cards": {"yellow": 3, "red": 0}},
            "career": [
                {"club": "Orlando Pirates", "period": "2024–Present", "level": "1st Division", "apps": 42},
                {"club": "Pirates Academy", "period": "2021–2024", "level": "Academy", "apps": 60},
            ],
            "medical": {"injuries": 0, "lastInjury": "None", "clearance": "Full", "fitnessScore": 95},
            "behavioral": {"training": 98, "discipline": "Excellent", "languages": ["English", "Zulu", "Sotho"], "leadership": "Vocal in training"},
            "contract": {"status": "Active", "expiry": "Dec 2026", "compensation": "Eligible", "tms": "Registered"},
            "matchClips": 22, "fullMatches": 10,
            "scoutNotes": "Electric pace, direct runner. Decision-making improving. High ceiling. MLS or Championship level.",
        },
        {
            "name": "Emmanuel Habimana", "age": 24, "nation": "Rwanda", "flag": "🇷🇼",
            "club": "Kiyovu Sports", "league": "Rwanda Premier League", "position": "CB",
            "photo": None, "verificationStatus": "partial",
            "reliabilityScore": 64, "dataConfidence": 58,
            "stats": {"appearances": 55, "goals": 3, "assists": 2, "minutes": 4700, "cards": {"yellow": 11, "red": 1}},
            "career": [
                {"club": "Kiyovu Sports", "period": "2022–Present", "level": "1st Division", "apps": 55},
                {"club": "Musanze FC", "period": "2020–2022", "level": "2nd Division", "apps": 38},
                {"club": "Unknown Academy", "period": "2018–2020", "level": "Academy", "apps": None},
            ],
            "medical": {"injuries": 3, "lastInjury": "ACL reconstruction (2023)", "clearance": "Full - monitored", "fitnessScore": 78},
            "behavioral": {"training": 82, "discipline": "Good", "languages": ["Kinyarwanda", "French"], "leadership": "N/A"},
            "contract": {"status": "Active", "expiry": "June 2026", "compensation": "Disputed", "tms": "Pending"},
            "matchClips": 5, "fullMatches": 2,
            "scoutNotes": "Strong aerial presence, good reading of the game. ACL recovery looks good but needs monitoring. Career gap 2018-2020 unverified.",
        },
        {
            "name": "Sipho Ndlovu", "age": 19, "nation": "South Africa", "flag": "🇿🇦",
            "club": "Stellenbosch FC", "league": "PSL", "position": "ST",
            "photo": None, "verificationStatus": "verified",
            "reliabilityScore": 78, "dataConfidence": 85,
            "stats": {"appearances": 28, "goals": 11, "assists": 3, "minutes": 1900, "cards": {"yellow": 2, "red": 0}},
            "career": [
                {"club": "Stellenbosch FC", "period": "2025–Present", "level": "1st Division", "apps": 28},
                {"club": "Stellenbosch Academy", "period": "2022–2025", "level": "Academy", "apps": 52},
            ],
            "medical": {"injuries": 0, "lastInjury": "None", "clearance": "Full", "fitnessScore": 93},
            "behavioral": {"training": 90, "discipline": "Very Good", "languages": ["English", "Afrikaans", "Xhosa"], "leadership": "Quiet but focused"},
            "contract": {"status": "Active", "expiry": "June 2028", "compensation": "Eligible", "tms": "Registered"},
            "matchClips": 18, "fullMatches": 8,
            "scoutNotes": "Natural finisher, good movement in the box. Strong for his age. NCAA D1 programs already inquiring. Could go Europe or USA.",
        },
        {
            "name": "Patrick Irakoze", "age": 21, "nation": "Burundi", "flag": "🇧🇮",
            "club": "AS Kigali", "league": "Rwanda Premier League", "position": "RB",
            "photo": None, "verificationStatus": "unverified",
            "reliabilityScore": 38, "dataConfidence": 29,
            "stats": {"appearances": 30, "goals": 1, "assists": 7, "minutes": 2400, "cards": {"yellow": 8, "red": 2}},
            "career": [
                {"club": "AS Kigali", "period": "2024–Present", "level": "1st Division", "apps": 30},
                {"club": "Unknown (Burundi)", "period": "2021–2024", "level": "Unknown", "apps": None},
            ],
            "medical": {"injuries": None, "lastInjury": "No records", "clearance": "Unknown", "fitnessScore": None},
            "behavioral": {"training": None, "discipline": "Unknown", "languages": ["Kirundi", "French"], "leadership": "N/A"},
            "contract": {"status": "Active", "expiry": "Dec 2025", "compensation": "Unknown", "tms": "Not registered"},
            "matchClips": 2, "fullMatches": 0,
            "scoutNotes": "Athletically gifted, aggressive in duels. Significant data gaps — Burundi career unverified. High ceiling but high risk profile.",
        },
    ]

    for player_data in demo_players:
        player_data["id"] = next_player_id
        players_db[next_player_id] = player_data
        next_player_id += 1

    # Seed initial shortlist
    shortlist_db.add(1)  # Jean-Baptiste
    shortlist_db.add(2)  # Thabo
    shortlist_db.add(4)  # Sipho

    print(f"Seeded {len(demo_players)} demo players and {len(shortlist_db)} shortlisted players")


# Seed data on startup
seed_demo_data()
