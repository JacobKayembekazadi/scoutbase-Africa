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
import sys
import shutil
import signal
import atexit
import threading

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import uuid
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

import re

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Literal
from starlette.middleware.base import BaseHTTPMiddleware

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
    
# Global processing semaphore (BS4)
# Initialized in lifespan to ensure event loop binding
processing_semaphore: asyncio.Semaphore = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("[LifeSpan] Server Starting...")
    global processing_semaphore
    processing_semaphore = asyncio.Semaphore(1)

    # Init DB and Migrate
    await init_db()
    await migrate_json_to_db()
    await sync_cache_from_db()

    if not players_db:
        print("[LifeSpan] Fresh start. Seeding demo data...")
        # seed_demo_data() is now updated to write to DB directly
        await seed_demo_data_async()
        await sync_cache_from_db()

    # Issue 9: SAM3 Background Loading (P1 Fix)
    # Skip local model loading when using Modal GPU backend
    if SAM3_AVAILABLE and sam3_processor and SAM3_BACKEND != "modal":
        print("[LifeSpan] Warming up SAM3 model in background...")
        loop = asyncio.get_running_loop()
        # Offload heavy model loading to thread pool so API remains responsive
        loop.run_in_executor(None, sam3_processor.model_loader.load)
    elif SAM3_BACKEND == "modal":
        print("[LifeSpan] SAM3 using Modal GPU backend — skipping local model load")

    # Issue 3: Disk Cleanup Task (P2 Fix)
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(60) # Initial delay
                now = datetime.now()
                cutoff = now - timedelta(hours=24)
                
                # Cleanup uploads
                if UPLOAD_DIR.exists():
                    for f in UPLOAD_DIR.glob("*"):
                        if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                            try: f.unlink()
                            except: pass
                
                # Cleanup results
                if RESULTS_DIR.exists():
                    for d in RESULTS_DIR.iterdir():
                        if d.is_dir() and datetime.fromtimestamp(d.stat().st_mtime) < cutoff:
                            try: shutil.rmtree(d)
                            except: pass
                            
                await asyncio.sleep(3600) # Hourly
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Cleanup] Error: {e}")
                await asyncio.sleep(3600)
    
    cleanup_task = asyncio.create_task(cleanup_loop())
    
    # Start autosave
    globals().get("_start_autosave")()
    
    yield
    
    # Shutdown
    print("[LifeSpan] Shutting down...")
    cleanup_task.cancel()
    await close_db_pool()
    await asyncio.to_thread(globals().get("_save_state"))
    print("[LifeSpan] Goodbye.")

app = FastAPI(
    title="ScoutBase Processing API",
    description="Video processing pipeline for player tracking and analysis",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: Use explicit origins. Wildcard (*) with credentials is forbidden by spec.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware (RL4-11)
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ---------------------------------------------------------------------------
# Database persistence (PostgreSQL via asyncpg OR SQLite fallback)
# ---------------------------------------------------------------------------
USE_POSTGRES = bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_PASSWORD"))

if USE_POSTGRES:
    from db_utils_pg import (
        init_db, sync_cache_from_db as _pg_sync_cache,
        close_pool as close_db_pool,
        insert_player as db_insert_player,
        update_player as db_update_player,
        player_exists as db_player_exists,
        insert_job as db_insert_job,
        update_job_status as db_update_job_status,
        upsert_track_assignment as db_upsert_track_assignment,
        delete_track_assignment as db_delete_track_assignment,
        upsert_shortlist as db_upsert_shortlist,
        delete_shortlist as db_delete_shortlist,
    )
    async def migrate_json_to_db():
        pass  # No JSON migration for Postgres
    print("[Database] Using PostgreSQL (asyncpg)")
else:
    from db_utils import init_db, migrate_json_to_db, DB_PATH
    import aiosqlite
    async def close_db_pool():
        pass
    print("[Database] Using SQLite (aiosqlite) — set DATABASE_URL for PostgreSQL")

# SAM3 Modal backend (optional)
SAM3_BACKEND = os.getenv("SAM3_BACKEND", "local")  # "local" or "modal"
modal_sam3_client = None
if SAM3_BACKEND == "modal":
    try:
        from sam3.modal_backend import ModalSAM3Client
        modal_sam3_client = ModalSAM3Client()
        print("[SAM3] Using Modal GPU backend")
    except Exception as e:
        print(f"[SAM3] Modal backend failed to init: {e}, falling back to local")
        SAM3_BACKEND = "local"

# ---------------------------------------------------------------------------
# JWT Auth Middleware (Supabase token validation)
# ---------------------------------------------------------------------------
import jwt as pyjwt

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
AUTH_ENABLED = bool(SUPABASE_JWT_SECRET)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate Supabase JWT on protected endpoints."""

    OPEN_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for health/docs endpoints
        if path in self.OPEN_PATHS or not AUTH_ENABLED:
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                pyjwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
            except pyjwt.ExpiredSignatureError:
                return Response(status_code=401, content="Token expired")
            except pyjwt.InvalidTokenError:
                return Response(status_code=401, content="Invalid token")
        elif AUTH_ENABLED:
            # No token provided but auth is required
            return Response(status_code=401, content="Authorization required")

        return await call_next(request)

if AUTH_ENABLED:
    app.add_middleware(JWTAuthMiddleware)
    print("[Auth] JWT validation enabled")

# In-memory caches (for read performance)
# NOTE: for horizontal scaling, use Redis instead
jobs: dict = {}
players_db: Dict[str, dict] = {}
shortlist_db: set = set()
track_assignments: Dict[str, Dict[int, dict]] = {}
_player_id_lock = threading.Lock()

def _load_state():
    """No-op for legacy load, real loading happens in sync_cache_from_db."""
    return True

async def sync_cache_from_db():
    """Populate in-memory caches from database on startup."""
    global players_db, shortlist_db, track_assignments, jobs

    if USE_POSTGRES:
        # PostgreSQL path — asyncpg returns parsed JSONB automatically
        caches = await _pg_sync_cache()
        players_db = caches["players_db"]
        shortlist_db = caches["shortlist_db"]
        track_assignments = caches["track_assignments"]
        jobs = caches["jobs"]
        return

    # SQLite fallback path
    print("[Cache] Syncing from SQLite...")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Load Players
        async with db.execute("SELECT * FROM players") as cursor:
            async for row in cursor:
                p = dict(row)
                for field in ["stats", "medical", "behavioral", "contract"]:
                    if p.get(field):
                        try: p[field] = json.loads(p[field])
                        except: pass
                players_db[p["id"]] = p

        # Load Shortlist
        async with db.execute("SELECT player_id FROM shortlists") as cursor:
            async for row in cursor:
                shortlist_db.add(row["player_id"])

        # Load Assignments
        async with db.execute("SELECT * FROM track_assignments") as cursor:
            async for row in cursor:
                jid = row["job_id"]
                if jid not in track_assignments:
                    track_assignments[jid] = {}
                track_assignments[jid][row["track_id"]] = {
                    "player_id": row["player_id"],
                    "assigned_at": row["assigned_at"],
                    "notes": row["notes"]
                }

        # Load Jobs
        async with db.execute("SELECT * FROM processing_jobs") as cursor:
            async for row in cursor:
                job = {
                    "job_id": row["job_id"],
                    "status": row["status"],
                    "results_path": row["results_path"],
                    "video_filename": row["video_filename"],
                    "error": row["error"],
                    "created_at": row["created_at"],
                    "completed_at": row["completed_at"],
                }
                if row["metadata"]:
                    try: job.update(json.loads(row["metadata"]))
                    except: pass
                jobs[row["job_id"]] = job

    print(f"[Cache] Synced {len(players_db)} players, {len(jobs)} jobs")

async def _save_state_async():
    """
    No-op: All writes are now direct to DB. 
    Kept for compatibility with existing calls.
    We might use this for cache invalidation later.
    """
    pass

def _save_state():
    """No-op: DB writes are immediate."""
    pass

def _start_autosave():
    """No-op: DB persistence is immediate."""
    pass


def _start_autosave():
    """Schedule periodic auto-save. Error-resilient — RL3-9."""
    global _autosave_timer
    try:
        _save_state()
    except Exception as e:
        print(f"[Autosave] WARNING: Save failed, will retry next interval: {e}")
    _autosave_timer = threading.Timer(_AUTOSAVE_INTERVAL, _start_autosave)
    _autosave_timer.daemon = True
    _autosave_timer.start()


async def _save_state_async():
    """Non-blocking save for async handlers — RL3-3."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _save_state)


def _shutdown_handler(*args):
    """Graceful shutdown: save state before exit."""
    global _autosave_timer
    print("\n[Shutdown] Saving state before exit...")
    if _autosave_timer:
        _autosave_timer.cancel()
    _save_state()
    sys.exit(0)

# Register shutdown hooks
atexit.register(_save_state)
signal.signal(signal.SIGINT, _shutdown_handler)
signal.signal(signal.SIGTERM, _shutdown_handler)


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
    verificationStatus: Literal["verified", "partial", "unverified"] = "unverified"  # RL4-3
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

    @field_validator('reliabilityScore', 'dataConfidence')
    @classmethod
    def validate_score_range(cls, v: int) -> int:
        """Ensure scores are within 0-100 range (RL4-3)."""
        return max(0, min(100, v))

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        """Ensure age is reasonable (RL4-3)."""
        if v < 0 or v > 60:
            raise ValueError('Age must be between 0 and 60')
        return v


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
    id: str


class LeagueIntel(BaseModel):
    name: str
    country: str
    strength: float
    reliability: int
    clubs: int
    risk: str


class TrackAssignment(BaseModel):
    player_id: str
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
    
    # BS4: Ensure sequential processing to prevent GPU OOM
    global processing_semaphore
    if processing_semaphore is None:
        processing_semaphore = asyncio.Semaphore(1)
        
    async with processing_semaphore:
        job["status"] = "processing"
        job["progress"] = 0.1
        
        # Update DB status
        if USE_POSTGRES:
            await db_update_job_status(job_id, "processing")
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE processing_jobs SET status='processing' WHERE job_id=?", (job_id,))
                await db.commit()

        output_dir = RESULTS_DIR / job_id

        try:
            # Run the CPU/GPU-intensive processing in a thread pool
            loop = asyncio.get_running_loop()
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
                    "competition": config.get("competition") or "Unknown Competition",
                    "home_team": config.get("home_team") or "Unknown Home",
                    "away_team": config.get("away_team") or "Unknown Away",
                    "date": config.get("match_date") or "Unknown Date",
                }
                report = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: generate_scout_report(results_dict, match_context, gemini_key)
                )
                report_path = output_dir / "scout_report.txt"
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                results_dict["scout_report"] = report

            # Store in Supabase if configured
            if supabase:
                try:
                    await store_results_in_supabase(job_id, config, results_dict)
                except Exception as supa_err:
                    print(f"[Supabase] WARNING: Failed to store results for {job_id}: {supa_err}")

            # Update job in memory
            job["status"] = "completed"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["results_path"] = str(output_dir)
            job["players_tracked"] = result.players_tracked
            job["progress"] = 1.0
            
            # Update job in DB
            meta = config.copy()
            meta["players_tracked"] = result.players_tracked
            meta["progress"] = 1.0

            if USE_POSTGRES:
                await db_update_job_status(
                    job_id, "completed",
                    results_path=job["results_path"],
                    metadata=meta,
                )
            else:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        """
                        UPDATE processing_jobs
                        SET status = 'completed', completed_at = ?, results_path = ?, metadata = ?
                        WHERE job_id = ?
                        """,
                        (job["completed_at"], job["results_path"], json.dumps(meta), job_id)
                    )
                    await db.commit()

        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
            job["progress"] = 0.0
            print(f"Processing failed for job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update DB with failure
            if USE_POSTGRES:
                await db_update_job_status(job_id, "failed", error=str(e))
            else:
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "UPDATE processing_jobs SET status = 'failed', error = ? WHERE job_id = ?",
                        (str(e), job_id)
                    )
                    await db.commit()


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
        "max_upload_size_mb": MAX_UPLOAD_SIZE_MB,  # RL4-17: expose limit to frontend
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
    # Validate file type first (cheap check)
    allowed_types = [
        "video/mp4", "video/avi", "video/quicktime",
        "video/x-msvideo", "video/webm",
    ]
    if video.content_type and video.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported video type: {video.content_type}")

    # Create job
    job_id = str(uuid.uuid4())[:12]
    # RL4-1: Sanitize user-supplied filename to prevent path traversal
    safe_filename = _sanitize_filename(video.filename)
    video_path = UPLOAD_DIR / f"{job_id}_{safe_filename}"

    # Save uploaded video with streaming size check.
    # video.size can be None for chunked/streamed uploads, so we
    # enforce the limit during the actual write.
    bytes_written = 0
    try:
        with open(video_path, "wb") as f:
            while True:
                chunk = await video.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        413,
                        f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB. "
                        f"Upload exceeded limit at {bytes_written / 1024 / 1024:.0f}MB."
                    )
                f.write(chunk)
    except HTTPException:
        # Clean up partial file on size violation
        if video_path.exists():
            video_path.unlink()
        raise
    except Exception as e:
        # Clean up partial file on any write error
        if video_path.exists():
            video_path.unlink()
        raise HTTPException(500, f"Failed to save uploaded video: {e}")

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

    job_record = {
        "job_id": job_id,
        "status": "queued",
        "video_filename": safe_filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "progress": 0.0,
        "players_tracked": 0,
        **config
    }
    jobs[job_id] = job_record
    
    # Persist job to DB
    if USE_POSTGRES:
        await db_insert_job(job_id, "queued", safe_filename, config)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO processing_jobs (
                    job_id, status, video_filename, results_path, error,
                    created_at, completed_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id, "queued", safe_filename, None, None,
                    job_record["created_at"], None, json.dumps(config)
                )
            )
            await db.commit()

    # Start background processing
    background_tasks.add_task(process_video_task, job_id, str(video_path), config)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video uploaded. Processing started.",
        "file_size_mb": round(bytes_written / 1024 / 1024, 1),
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

    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

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

    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

    # RL4-5: Validate path stays within RESULTS_DIR
    video_path = _validate_path_containment(
        Path(job["results_path"]) / "annotated_output.mp4", RESULTS_DIR
    )
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

    if not job.get("results_path"):
        raise HTTPException(500, "Results path not set for this job")

    # Try annotated video first, fall back to original
    # RL4-5: Validate path stays within RESULTS_DIR
    video_path = _validate_path_containment(
        Path(job["results_path"]) / "annotated_output.mp4", RESULTS_DIR
    )
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
            headers={
                "Content-Disposition": f"inline; filename=frame_{frame_number}.jpg",
                # Allow the browser to cache frames for 5 minutes to reduce
                # redundant cv2.VideoCapture opens when the SAM3 slider is
                # dragged back and forth over the same region.
                "Cache-Control": "public, max-age=300",
            }
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

    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

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

    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

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

    # Guard against missing results_path (e.g. job completed but paths not set)
    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

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
                "player_name": player["name"] if player else "(Deleted Player)",
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
    """Assign a track to an existing player (SQLite)."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, "Job not yet completed")

    # Guard against missing results_path
    if not job.get("results_path"):
        raise HTTPException(500, "Results path not available for this job")

    # Update in DB
    if USE_POSTGRES:
        if not await db_player_exists(assignment.player_id):
            raise HTTPException(404, f"Player {assignment.player_id} not found")
        await db_upsert_track_assignment(job_id, track_id, assignment.player_id, assignment.notes)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT 1 FROM players WHERE id=?", (assignment.player_id,)) as cursor:
                if not await cursor.fetchone():
                    raise HTTPException(404, f"Player {assignment.player_id} not found")
            await db.execute(
                """
                INSERT OR REPLACE INTO track_assignments (job_id, track_id, player_id, assigned_at, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, track_id, assignment.player_id, datetime.now(timezone.utc).isoformat(), assignment.notes)
            )
            await db.commit()

    # Create or update assignment in cache
    if job_id not in track_assignments:
        track_assignments[job_id] = {}

    ass_dict = {
        "player_id": assignment.player_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "notes": assignment.notes,
    }
    track_assignments[job_id][track_id] = ass_dict

    return {
        "message": f"Track #{track_id} assigned to player {assignment.player_id}",
        "assignment": ass_dict,
    }


@app.post("/results/{job_id}/tracks/{track_id}/create-player")
async def create_player_from_track(job_id: str, track_id: int, player_data: PlayerCreateFromTrack):
    """Create a new player and assign this track to them (SQLite)."""
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
        
    # Generate new ID
    new_id = str(uuid.uuid4())
    
    # Store Player in DB
    player_db_data = {
        "name": player_data.name, "age": player_data.age, "nation": player_data.nation,
        "position": player_data.position, "club": player_data.club, "league": player_data.league,
        "verificationStatus": "unverified", "reliabilityScore": 0, "dataConfidence": 0,
        "scoutNotes": player_data.notes or f"Created from video tracking (Job: {job_id}, Track: #{track_id})",
    }
    if USE_POSTGRES:
        await db_insert_player(new_id, player_db_data)
        await db_upsert_track_assignment(job_id, track_id, new_id, player_data.notes)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO players (
                    id, name, age, nation, position, club, league,
                    verification_status, reliability_score, data_confidence_score,
                    added_on, stats, medical, behavioral, contract, scout_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id, player_data.name, player_data.age, player_data.nation,
                    player_data.position, player_data.club, player_data.league,
                    "unverified", 0, 0, datetime.now().isoformat(),
                    "{}", "{}", "{}", "{}",
                    player_data.notes or f"Created from video tracking (Job: {job_id}, Track: #{track_id})"
                )
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO track_assignments (job_id, track_id, player_id, assigned_at, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, track_id, new_id, datetime.now(timezone.utc).isoformat(), player_data.notes)
            )
            await db.commit()

    # Update caches
    new_player = {
        "id": new_id,
        "name": player_data.name,
        "age": player_data.age,
        "nation": player_data.nation,
        "club": player_data.club,
        "league": player_data.league,
        "position": player_data.position,
        "verificationStatus": "unverified",
        "scoutNotes": player_data.notes or f"Created from video tracking (Job: {job_id}, Track: #{track_id})"
    }
    players_db[new_id] = new_player
    
    if job_id not in track_assignments:
        track_assignments[job_id] = {}
        
    ass_dict = {
        "player_id": new_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "notes": player_data.notes,
    }
    track_assignments[job_id][track_id] = ass_dict

    return {
        "message": f"Created player '{player_data.name}' and assigned Track #{track_id}",
        "player": new_player,
        "assignment": ass_dict,
    }


@app.delete("/results/{job_id}/tracks/{track_id}/unassign")
async def unassign_track(job_id: str, track_id: int):
    """Remove track assignment."""
    if USE_POSTGRES:
        await db_delete_track_assignment(job_id, track_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM track_assignments WHERE job_id = ? AND track_id = ?",
                (job_id, track_id)
            )
            await db.commit()
    
    if job_id in track_assignments and track_id in track_assignments[job_id]:
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
async def get_player(player_id: str):
    """Get a single player by ID."""
    if player_id not in players_db:
        raise HTTPException(404, "Player not found")
    return players_db[player_id]


@app.post("/players")
async def create_player(player: PlayerCreate):
    """Create a new player."""
    player_dict = player.model_dump()
    new_id = str(uuid.uuid4())
    player_dict["id"] = new_id

    # Store in DB
    if USE_POSTGRES:
        await db_insert_player(new_id, player_dict)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO players (
                    id, name, age, nation, position, club, league,
                    verification_status, reliability_score, data_confidence_score,
                    added_on, stats, medical, behavioral, contract, scout_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id, player_dict["name"], player_dict["age"], player_dict["nation"],
                    player_dict["position"], player_dict["club"], player_dict["league"],
                    player_dict.get("verificationStatus", "unverified"),
                    player_dict.get("reliabilityScore", 0), player_dict.get("dataConfidence", 0),
                    datetime.now().isoformat(),
                    json.dumps(player_dict.get("stats", {})),
                    json.dumps(player_dict.get("medical", {})),
                    json.dumps(player_dict.get("behavioral", {})),
                    json.dumps(player_dict.get("contract", {})),
                    player_dict.get("scoutNotes", "")
                )
            )
            await db.commit()

    # Update cache
    players_db[new_id] = player_dict
    
    return player_dict


@app.put("/players/{player_id}")
async def update_player(player_id: str, player_update: PlayerUpdate):
    """Update an existing player."""
    if player_id not in players_db:
        if USE_POSTGRES:
            if not await db_player_exists(player_id):
                raise HTTPException(404, "Player not found")
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT 1 FROM players WHERE id = ?", (player_id,)) as cursor:
                    if not await cursor.fetchone():
                        raise HTTPException(404, "Player not found")

    existing = players_db.get(player_id, {})
    update_data = player_update.model_dump(exclude_unset=True)

    # Merge updates
    for key, value in update_data.items():
        existing[key] = value if not isinstance(value, BaseModel) else value.model_dump()

    # Persist to DB
    if USE_POSTGRES:
        await db_update_player(player_id, existing)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                UPDATE players SET
                    name = ?, age = ?, nation = ?, position = ?, club = ?, league = ?,
                    verification_status = ?, reliability_score = ?, data_confidence_score = ?,
                    stats = ?, medical = ?, behavioral = ?, contract = ?, scout_notes = ?
                WHERE id = ?
                """,
                (
                    existing.get("name"), existing.get("age"), existing.get("nation"),
                    existing.get("position"), existing.get("club"), existing.get("league"),
                    existing.get("verificationStatus"), existing.get("reliabilityScore"),
                    existing.get("dataConfidence"),
                    json.dumps(existing.get("stats", {})),
                    json.dumps(existing.get("medical", {})),
                    json.dumps(existing.get("behavioral", {})),
                    json.dumps(existing.get("contract", {})),
                    existing.get("scoutNotes", ""),
                    player_id
                )
            )
            await db.commit()

    # Update cache
    players_db[player_id] = existing
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
async def add_to_shortlist(player_id: str):
    """Add a player to the shortlist."""
    if player_id not in players_db:
        raise HTTPException(404, "Player not found")

    user_id = "1"  # MVP Admin

    if USE_POSTGRES:
        await db_upsert_shortlist(user_id, player_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO shortlists (user_id, player_id) VALUES (?, ?)",
                (user_id, player_id)
            )
            await db.commit()
    
    shortlist_db.add(player_id)
    return {"message": f"Player {player_id} added to shortlist", "shortlist": list(shortlist_db)}


@app.delete("/shortlist/{player_id}")
async def remove_from_shortlist(player_id: str):
    """Remove a player from the shortlist."""
    user_id = "1"  # MVP Admin

    if USE_POSTGRES:
        await db_delete_shortlist(user_id, player_id)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM shortlists WHERE user_id = ? AND player_id = ?",
                (user_id, player_id)
            )
            await db.commit()
        
    shortlist_db.discard(player_id)
    return {"message": f"Player {player_id} removed from shortlist", "shortlist": list(shortlist_db)}


# ---------------------------------------------------------------------------
# SAM3 Endpoints
# ---------------------------------------------------------------------------

@app.get("/sam3/status")
async def sam3_status():
    """Check SAM3 module status and availability."""
    # Modal backend check
    if SAM3_BACKEND == "modal" and modal_sam3_client:
        try:
            return modal_sam3_client.health_check()
        except Exception as e:
            return {"available": False, "model_loaded": False, "error": str(e), "backend": "modal"}

    # Local backend check
    if not SAM3_AVAILABLE:
        return {
            "available": False,
            "model_loaded": False,
            "error": "SAM3 module not installed. Install with: pip install transformers huggingface-hub",
            "backend": "local",
        }

    try:
        status = sam3_processor.get_status()
        status["backend"] = "local"
        return SAM3StatusResponse(**status)
    except Exception as e:
        return {"available": False, "model_loaded": False, "error": str(e), "backend": "local"}


@app.post("/sam3/segment")
async def sam3_segment(request: SegmentationRequest):
    """
    Perform text-prompted segmentation on a single frame.
    Routes to Modal GPU or local CPU based on SAM3_BACKEND env var.
    """
    # Modal backend path
    if SAM3_BACKEND == "modal" and modal_sam3_client:
        try:
            # Need to get image as base64 for Modal
            if request.image_base64:
                image_b64 = request.image_base64
            elif request.job_id:
                # Extract frame and encode as base64
                import cv2
                import base64 as b64mod
                frame = sam3_processor._extract_frame_from_job(
                    request.job_id, request.frame_number or 0
                ) if SAM3_AVAILABLE else None
                if frame is None:
                    raise HTTPException(400, "Cannot extract frame — local SAM3 module needed for frame extraction")
                _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                image_b64 = b64mod.b64encode(buffer).decode('utf-8')
            else:
                raise HTTPException(400, "Must provide image_base64 or job_id+frame_number")

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: modal_sam3_client.segment_frame(
                    image_base64=image_b64,
                    prompt=request.prompt,
                    confidence_threshold=request.confidence_threshold,
                    return_masks=request.return_masks,
                    return_bboxes=request.return_bboxes,
                )
            )
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Modal segmentation failed: {e}")

    # Local backend path
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

# Seed data logic is now in seed_demo_data_async below
async def seed_demo_data_async():
    """Seed DB with demo players."""
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
        }
    ]

    if USE_POSTGRES:
        for p in demo_players:
            pid = str(uuid.uuid4())
            await db_insert_player(pid, p)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            for p in demo_players:
                pid = str(uuid.uuid4())
                await db.execute(
                    """
                    INSERT INTO players (
                        id, name, age, nation, position, club, league,
                        verification_status, reliability_score, data_confidence_score,
                        added_on, stats, medical, behavioral, contract, scout_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid, p.get("name"), p.get("age"), p.get("nation"), p.get("position"),
                        p.get("club"), p.get("league"), p.get("verificationStatus", "unverified"),
                        p.get("reliabilityScore", 0), p.get("dataConfidence", 0),
                        datetime.now().isoformat(),
                        json.dumps(p.get("stats", {})),
                        json.dumps(p.get("medical", {})),
                        json.dumps(p.get("behavioral", {})),
                        json.dumps(p.get("contract", {})),
                        p.get("scoutNotes", "")
                    )
                )
            await db.commit()
    print(f"[Seed] Added {len(demo_players)} demo players")


# Startup logic moved to lifespan handler (RL4-9)
