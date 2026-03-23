-- ScoutBase Africa — PostgreSQL Schema (Supabase)
-- Translated from SQLite schema for production deployment

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    nation TEXT,
    position TEXT,
    club TEXT,
    league TEXT,
    flag TEXT,
    photo TEXT,
    verification_status TEXT DEFAULT 'unverified',
    reliability_score INTEGER DEFAULT 0,
    data_confidence_score INTEGER DEFAULT 0,
    stats JSONB DEFAULT '{}'::jsonb,
    medical JSONB DEFAULT '{}'::jsonb,
    behavioral JSONB DEFAULT '{}'::jsonb,
    contract JSONB DEFAULT '{}'::jsonb,
    career JSONB DEFAULT '[]'::jsonb,
    match_clips INTEGER DEFAULT 0,
    full_matches INTEGER DEFAULT 0,
    scout_notes TEXT,
    added_on TIMESTAMPTZ DEFAULT NOW()
);

-- Track assignments
CREATE TABLE IF NOT EXISTS track_assignments (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    UNIQUE(job_id, track_id)
);

-- Shortlists
CREATE TABLE IF NOT EXISTS shortlists (
    user_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    PRIMARY KEY (user_id, player_id)
);

-- Processing jobs
CREATE TABLE IF NOT EXISTS processing_jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    results_path TEXT,
    video_filename TEXT,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Scout notes
CREATE TABLE IF NOT EXISTS scout_notes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    note TEXT NOT NULL,
    rating INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_players_nation ON players(nation);
CREATE INDEX IF NOT EXISTS idx_players_position ON players(position);
CREATE INDEX IF NOT EXISTS idx_players_club ON players(club);
CREATE INDEX IF NOT EXISTS idx_track_assignments_job ON track_assignments(job_id);
CREATE INDEX IF NOT EXISTS idx_shortlists_player ON shortlists(player_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scout_notes_player ON scout_notes(player_id);
