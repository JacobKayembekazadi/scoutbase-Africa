
# ---------------------------------------------------------------------------
# SQLite Database Wrapper
# ---------------------------------------------------------------------------
import aiosqlite

DB_PATH = DATA_DIR / "scoutbase.db"

async def init_db():
    """Initialize the SQLite database with schema."""
    if not DB_PATH.exists():
        print("[Database] Initializing fresh database...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        with open(DATA_DIR / "schema.sql", "r") as f:
            await db.executescript(f.read())
        await db.commit()
    print("[Database] Schema initialized.")

async def migrate_json_to_db():
    """Migrate legacy JSON state to SQLite."""
    if not _STATE_FILE.exists():
        return

    # Check if DB is empty
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM players") as cursor:
            (count,) = await cursor.fetchone()
            if count > 0:
                print("[Database] DB not empty, skipping JSON migration.")
                return

        print("[Database] Migrating legacy JSON state to SQLite...")
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Migrate Players
            players = state.get("players_db", {})
            for pid, p in players.items():
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
                        p.get("added_on", datetime.now().isoformat()),
                        json.dumps(p.get("stats", {})),
                        json.dumps(p.get("medical", {})),
                        json.dumps(p.get("behavioral", {})),
                        json.dumps(p.get("contract", {})),
                        p.get("scoutNotes", "")
                    )
                )

            # Migrate Shortlist (Assign to demo admin user)
            shortlist = state.get("shortlist_db", [])
            for pid in shortlist:
                await db.execute(
                    "INSERT OR IGNORE INTO shortlists (user_id, player_id) VALUES (?, ?)",
                    ("1", str(pid)) # Default admin ID "1" from Auth.js mock
                )
            
            # Migrate Jobs
            jobs_data = state.get("jobs", {})
            for jid, job in jobs_data.items():
                await db.execute(
                    """
                    INSERT INTO processing_jobs (
                        job_id, status, results_path, video_filename, 
                        error, created_at, completed_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        jid, job.get("status"), job.get("results_path"), job.get("video_filename"),
                        job.get("error"), job.get("created_at"), job.get("completed_at"),
                        json.dumps({k:v for k,v in job.items() if k not in ["job_id", "status", "results_path", "video_filename", "error"]})
                    )
                )

            await db.commit()
            print(f"[Database] Migration complete: {len(players)} players, {len(jobs_data)} jobs.")
            
            # Rename old state file to avoid re-migration
            _STATE_FILE.rename(_STATE_FILE.with_suffix(".json.bak"))
            
        except Exception as e:
            print(f"[Database] Migration failed: {e}")
            import traceback
            traceback.print_exc()
