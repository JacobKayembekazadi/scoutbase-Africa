"""
PostgreSQL Database Utilities (Production)
==========================================
Replaces SQLite (db_utils.py) with asyncpg for Supabase PostgreSQL.

Env vars:
    DATABASE_URL   — Full PostgreSQL connection string
    SUPABASE_URL   — Supabase project URL (used if DATABASE_URL not set)
    SUPABASE_DB_PASSWORD — Supabase DB password
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# Connection Pool
# ---------------------------------------------------------------------------

_pool: asyncpg.Pool = None


def _get_database_url() -> str:
    """Resolve database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Construct from Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL", "")
    db_password = os.getenv("SUPABASE_DB_PASSWORD", "")

    if supabase_url and db_password:
        # Extract project ref from URL: https://rauweyruhjficjnpkcjo.supabase.co
        ref = supabase_url.replace("https://", "").split(".")[0]
        return f"postgresql://postgres.{ref}:{db_password}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

    raise RuntimeError(
        "No database URL configured. Set DATABASE_URL or SUPABASE_URL + SUPABASE_DB_PASSWORD"
    )


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        url = _get_database_url()
        _pool = await asyncpg.create_pool(
            url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("[Database] PostgreSQL pool created")
    return _pool


async def close_pool():
    """Close the connection pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("[Database] PostgreSQL pool closed")


# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------

async def init_db():
    """Initialize the PostgreSQL database with schema."""
    pool = await get_pool()

    schema_file = DATA_DIR / "schema.postgres.sql"
    if not schema_file.exists():
        logger.warning("[Database] schema.postgres.sql not found, skipping init")
        return

    schema_sql = schema_file.read_text()

    async with pool.acquire() as conn:
        await conn.execute(schema_sql)

    logger.info("[Database] PostgreSQL schema initialized")


# ---------------------------------------------------------------------------
# Cache Sync (populate in-memory caches from PostgreSQL)
# ---------------------------------------------------------------------------

async def sync_cache_from_db() -> dict:
    """
    Load all data from PostgreSQL into in-memory caches.
    Returns dict with players_db, shortlist_db, track_assignments, jobs.
    """
    pool = await get_pool()
    players_db = {}
    shortlist_db = set()
    track_assignments = {}
    jobs = {}

    async with pool.acquire() as conn:
        # Load Players
        rows = await conn.fetch("SELECT * FROM players")
        for row in rows:
            p = dict(row)
            # JSONB columns are already parsed by asyncpg
            players_db[p["id"]] = p

        # Load Shortlist
        rows = await conn.fetch("SELECT player_id FROM shortlists")
        for row in rows:
            shortlist_db.add(row["player_id"])

        # Load Track Assignments
        rows = await conn.fetch("SELECT * FROM track_assignments")
        for row in rows:
            jid = row["job_id"]
            if jid not in track_assignments:
                track_assignments[jid] = {}
            track_assignments[jid][row["track_id"]] = {
                "player_id": row["player_id"],
                "assigned_at": row["assigned_at"].isoformat() if row["assigned_at"] else None,
                "notes": row["notes"],
            }

        # Load Jobs
        rows = await conn.fetch("SELECT * FROM processing_jobs")
        for row in rows:
            job = {
                "job_id": row["job_id"],
                "status": row["status"],
                "results_path": row["results_path"],
                "video_filename": row["video_filename"],
                "error": row["error"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            }
            # JSONB metadata is already a dict
            if row["metadata"]:
                job.update(row["metadata"])
            jobs[row["job_id"]] = job

    logger.info(f"[Cache] Synced {len(players_db)} players, {len(jobs)} jobs from PostgreSQL")
    return {
        "players_db": players_db,
        "shortlist_db": shortlist_db,
        "track_assignments": track_assignments,
        "jobs": jobs,
    }


# ---------------------------------------------------------------------------
# Write Operations
# ---------------------------------------------------------------------------

async def insert_player(player_id: str, data: dict):
    """Insert a new player."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO players (
                id, name, age, nation, position, club, league,
                verification_status, reliability_score, data_confidence_score,
                added_on, stats, medical, behavioral, contract, scout_notes
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
            """,
            player_id,
            data.get("name"),
            data.get("age"),
            data.get("nation"),
            data.get("position"),
            data.get("club"),
            data.get("league"),
            data.get("verificationStatus", "unverified"),
            data.get("reliabilityScore", 0),
            data.get("dataConfidence", 0),
            datetime.now().isoformat(),
            json.dumps(data.get("stats", {})),
            json.dumps(data.get("medical", {})),
            json.dumps(data.get("behavioral", {})),
            json.dumps(data.get("contract", {})),
            data.get("scoutNotes", ""),
        )


async def update_player(player_id: str, data: dict):
    """Update an existing player."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE players SET
                name=$1, age=$2, nation=$3, position=$4, club=$5, league=$6,
                verification_status=$7, reliability_score=$8, data_confidence_score=$9,
                stats=$10, medical=$11, behavioral=$12, contract=$13, scout_notes=$14
            WHERE id=$15
            """,
            data.get("name"),
            data.get("age"),
            data.get("nation"),
            data.get("position"),
            data.get("club"),
            data.get("league"),
            data.get("verificationStatus"),
            data.get("reliabilityScore"),
            data.get("dataConfidence"),
            json.dumps(data.get("stats", {})),
            json.dumps(data.get("medical", {})),
            json.dumps(data.get("behavioral", {})),
            json.dumps(data.get("contract", {})),
            data.get("scoutNotes", ""),
            player_id,
        )


async def player_exists(player_id: str) -> bool:
    """Check if a player exists."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM players WHERE id=$1", player_id)
        return row is not None


async def insert_job(job_id: str, status: str, video_filename: str, config: dict):
    """Insert a new processing job."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO processing_jobs (job_id, status, video_filename, metadata, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            """,
            job_id,
            status,
            video_filename,
            json.dumps(config),
        )


async def update_job_status(job_id: str, status: str, **kwargs):
    """Update job status and optional fields."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status == "completed":
            await conn.execute(
                """
                UPDATE processing_jobs
                SET status=$1, completed_at=NOW(), results_path=$2, metadata=$3
                WHERE job_id=$4
                """,
                status,
                kwargs.get("results_path"),
                json.dumps(kwargs.get("metadata", {})),
                job_id,
            )
        elif status == "failed":
            await conn.execute(
                "UPDATE processing_jobs SET status=$1, error=$2 WHERE job_id=$3",
                status,
                kwargs.get("error"),
                job_id,
            )
        else:
            await conn.execute(
                "UPDATE processing_jobs SET status=$1 WHERE job_id=$2",
                status,
                job_id,
            )


async def upsert_track_assignment(job_id: str, track_id: int, player_id: str, notes: str = None):
    """Insert or update a track assignment."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO track_assignments (job_id, track_id, player_id, assigned_at, notes)
            VALUES ($1, $2, $3, NOW(), $4)
            ON CONFLICT (job_id, track_id)
            DO UPDATE SET player_id=$3, assigned_at=NOW(), notes=$4
            """,
            job_id,
            track_id,
            player_id,
            notes,
        )


async def delete_track_assignment(job_id: str, track_id: int):
    """Remove a track assignment."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM track_assignments WHERE job_id=$1 AND track_id=$2",
            job_id,
            track_id,
        )


async def upsert_shortlist(user_id: str, player_id: str):
    """Add player to shortlist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO shortlists (user_id, player_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id, player_id) DO NOTHING
            """,
            user_id,
            player_id,
        )


async def delete_shortlist(user_id: str, player_id: str):
    """Remove player from shortlist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM shortlists WHERE user_id=$1 AND player_id=$2",
            user_id,
            player_id,
        )
