-- ============================================================================
-- ScoutBase Africa — Database Schema
-- ============================================================================
-- Run this in your Supabase SQL Editor to set up the database.
-- Supabase project: https://supabase.com/dashboard
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Leagues
CREATE TABLE leagues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    country_code TEXT,
    strength_rating DECIMAL(3,1),       -- 1.0 to 10.0
    data_reliability_pct INTEGER,        -- 0-100
    match_reliability_index INTEGER,     -- 0-100
    clubs_count INTEGER,
    operational_risk TEXT CHECK (operational_risk IN ('low', 'medium', 'high')),
    registration_rules TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clubs
CREATE TABLE clubs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    league_id UUID REFERENCES leagues(id),
    country TEXT NOT NULL,
    level TEXT,                           -- '1st_division', '2nd_division', 'academy'
    credibility_score INTEGER,            -- 0-100
    logo_url TEXT,
    city TEXT,
    founded_year INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Players (Layer A: Identity & Verification)
CREATE TABLE players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    date_of_birth DATE,
    dob_verified BOOLEAN DEFAULT FALSE,
    nationality TEXT NOT NULL,
    nationalities TEXT[],                 -- Array for dual nationals
    current_club_id UUID REFERENCES clubs(id),
    position TEXT,                        -- 'GK', 'CB', 'LB', 'RB', 'CM', 'AM', 'LW', 'RW', 'ST'
    height_cm INTEGER,
    weight_kg INTEGER,
    height_weight_date DATE,             -- When measured
    photo_url TEXT,
    
    -- Verification
    verification_status TEXT DEFAULT 'unverified' 
        CHECK (verification_status IN ('verified', 'partial', 'unverified')),
    id_document_hash TEXT,               -- Hashed national ID / passport
    biometric_confirmed BOOLEAN DEFAULT FALSE,
    
    -- Agent info
    agent_name TEXT,
    agent_licensed BOOLEAN,
    agent_contact TEXT,
    
    -- Scores
    reliability_score INTEGER,            -- 0-100 (composite)
    data_confidence_score INTEGER,        -- 0-100 (data availability)
    
    -- Meta
    scout_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Player Career History (Layer B)
CREATE TABLE career_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    club_id UUID REFERENCES clubs(id),
    club_name TEXT,                       -- Fallback if club not in DB
    period_start DATE,
    period_end DATE,
    level TEXT,                           -- '1st_division', '2nd_division', 'academy'
    appearances INTEGER,
    goals INTEGER,
    assists INTEGER,
    minutes_played INTEGER,
    is_loan BOOLEAN DEFAULT FALSE,
    data_source TEXT,                     -- 'club', 'league', 'federation', 'scout', 'self_reported'
    verified BOOLEAN DEFAULT FALSE,
    gap_flagged BOOLEAN DEFAULT FALSE,    -- True if unexplained career gap
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- MATCH & PERFORMANCE DATA (Layer C)
-- ============================================================================

-- Matches
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    home_team TEXT,
    away_team TEXT,
    home_club_id UUID REFERENCES clubs(id),
    away_club_id UUID REFERENCES clubs(id),
    competition TEXT,
    league_id UUID REFERENCES leagues(id),
    match_date DATE,
    venue TEXT,
    score_home INTEGER,
    score_away INTEGER,
    
    -- Video processing
    processing_job_id TEXT,
    video_url TEXT,                       -- Supabase Storage URL
    annotated_video_url TEXT,             -- With tracking overlays
    total_frames INTEGER,
    duration_seconds DECIMAL(8,1),
    players_tracked INTEGER,
    
    -- Meta
    data_source TEXT,                     -- 'ai_processed', 'manual', 'federation'
    reliability_rating INTEGER,           -- 0-100
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Tracking Data (per-player-per-match from vision pipeline)
CREATE TABLE tracking_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id),  -- Linked after identification
    track_id INTEGER NOT NULL,              -- ByteTrack assigned ID
    
    -- Time
    frames_visible INTEGER,
    estimated_minutes DECIMAL(5,1),
    first_seen_minute DECIMAL(5,1),
    last_seen_minute DECIMAL(5,1),
    visibility_pct DECIMAL(5,1),
    started BOOLEAN,                        -- Manually tagged: start or sub
    subbed_on_minute DECIMAL(5,1),
    subbed_off_minute DECIMAL(5,1),
    
    -- Movement
    sprint_count INTEGER,
    avg_speed DECIMAL(8,2),
    max_speed DECIMAL(8,2),
    total_distance_est DECIMAL(10,2),       -- Estimated from pixel displacement
    heat_map JSONB,                         -- Zone distribution
    
    -- Events (manually tagged or AI-detected)
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Match Events (goals, cards, substitutions)
CREATE TABLE match_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id),
    track_id INTEGER,
    event_type TEXT NOT NULL,               -- 'goal', 'assist', 'yellow', 'red', 'sub_on', 'sub_off'
    minute DECIMAL(5,1),
    frame_number INTEGER,
    description TEXT,
    video_timestamp_seconds DECIMAL(8,1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- MEDICAL & PHYSICAL (Layer D)
-- ============================================================================

CREATE TABLE medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    record_type TEXT NOT NULL,              -- 'injury', 'surgery', 'fitness_test', 'clearance'
    title TEXT NOT NULL,
    severity TEXT,                           -- 'minor', 'moderate', 'severe'
    date_occurred DATE,
    recovery_weeks INTEGER,
    date_cleared DATE,
    clearance_status TEXT,                   -- 'full', 'monitored', 'restricted', 'pending'
    fitness_score INTEGER,                   -- 0-100
    document_url TEXT,                       -- Supabase Storage (access controlled)
    requires_consent BOOLEAN DEFAULT TRUE,
    consent_given BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VIDEO EVIDENCE (Layer E)
-- ============================================================================

CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID REFERENCES matches(id),
    player_id UUID REFERENCES players(id),
    video_type TEXT NOT NULL,               -- 'full_match', 'clip', 'training', 'highlight'
    title TEXT,
    storage_url TEXT NOT NULL,              -- Supabase Storage URL
    duration_seconds INTEGER,
    is_ai_tracked BOOLEAN DEFAULT FALSE,
    is_raw_footage BOOLEAN DEFAULT TRUE,    -- Not edited/highlights
    opponent TEXT,
    competition TEXT,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID,                        -- User who uploaded
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- BEHAVIORAL & PROFESSIONAL (Layer F)
-- ============================================================================

CREATE TABLE player_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    training_attendance_pct INTEGER,         -- 0-100
    discipline_rating TEXT,                  -- 'excellent', 'very_good', 'good', 'fair', 'poor'
    languages TEXT[],
    leadership_notes TEXT,
    adaptability_notes TEXT,
    travel_readiness BOOLEAN,
    coach_feedback JSONB,                   -- [{coach, rating, comment, date}]
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CONTRACT & LEGAL (Layer G)
-- ============================================================================

CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    club_id UUID REFERENCES clubs(id),
    status TEXT DEFAULT 'active',           -- 'active', 'expired', 'terminated', 'disputed'
    start_date DATE,
    expiry_date DATE,
    training_compensation TEXT,             -- 'eligible', 'not_eligible', 'disputed', 'unknown'
    fifa_tms_status TEXT,                   -- 'registered', 'pending', 'not_registered'
    release_clause BOOLEAN DEFAULT FALSE,
    release_clause_amount DECIMAL(12,2),
    currency TEXT DEFAULT 'USD',
    transfer_history JSONB,                 -- [{from, to, date, fee}]
    document_url TEXT,                      -- Supabase Storage
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SCOUT / CLUB OPERATIONS (Sticky Features)
-- ============================================================================

-- Organizations (clubs, agencies, colleges using ScoutBase)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,                     -- 'club', 'agency', 'college', 'federation', 'academy'
    country TEXT,
    plan TEXT DEFAULT 'free',               -- 'free', 'pro', 'enterprise'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users (scouts, coaches, admins)
CREATE TABLE users (
    id UUID PRIMARY KEY,                   -- Matches Supabase Auth UUID
    organization_id UUID REFERENCES organizations(id),
    full_name TEXT,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'scout',             -- 'admin', 'scout', 'coach', 'viewer'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shortlists
CREATE TABLE shortlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT DEFAULT 'Default Shortlist',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE shortlist_players (
    shortlist_id UUID REFERENCES shortlists(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    PRIMARY KEY (shortlist_id, player_id)
);

-- Scout Notes (private per-user)
CREATE TABLE scout_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    rating INTEGER,                        -- 1-10
    recommend_action TEXT,                 -- 'sign', 'monitor', 'trial', 'pass'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Processing Jobs (tracks video analysis pipeline runs)
CREATE TABLE processing_jobs (
    id TEXT PRIMARY KEY,
    match_id UUID REFERENCES matches(id),
    status TEXT DEFAULT 'queued',           -- 'queued', 'processing', 'completed', 'failed'
    video_filename TEXT,
    model_used TEXT,
    config JSONB,
    results_summary JSONB,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_players_nationality ON players(nationality);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_players_verification ON players(verification_status);
CREATE INDEX idx_players_club ON players(current_club_id);
CREATE INDEX idx_career_player ON career_history(player_id);
CREATE INDEX idx_tracking_match ON tracking_data(match_id);
CREATE INDEX idx_tracking_player ON tracking_data(player_id);
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_videos_match ON videos(match_id);
CREATE INDEX idx_videos_player ON videos(player_id);
CREATE INDEX idx_shortlist_user ON shortlists(user_id);
CREATE INDEX idx_scout_notes_player ON scout_notes(player_id);
CREATE INDEX idx_contracts_player ON contracts(player_id);
CREATE INDEX idx_contracts_expiry ON contracts(expiry_date);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) — Enable after setting up auth
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE scout_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE shortlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE shortlist_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_records ENABLE ROW LEVEL SECURITY;

-- Scout notes: users can only see their own
CREATE POLICY "Users can view own scout notes" ON scout_notes
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own scout notes" ON scout_notes
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own scout notes" ON scout_notes
    FOR UPDATE USING (auth.uid() = user_id);

-- Shortlists: users can only see their own
CREATE POLICY "Users can view own shortlists" ON shortlists
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can manage own shortlists" ON shortlists
    FOR ALL USING (auth.uid() = user_id);

-- Medical records: only visible if consent given (or user is admin)
CREATE POLICY "Medical records require consent" ON medical_records
    FOR SELECT USING (
        consent_given = TRUE 
        OR requires_consent = FALSE
    );

-- ============================================================================
-- SEED DATA — Sample leagues for demo
-- ============================================================================

INSERT INTO leagues (name, country, country_code, strength_rating, data_reliability_pct, clubs_count, operational_risk) VALUES
    ('Rwanda Premier League', 'Rwanda', 'RW', 3.2, 78, 16, 'low'),
    ('South Africa PSL', 'South Africa', 'ZA', 5.8, 91, 16, 'low'),
    ('Burundi Primus League', 'Burundi', 'BI', 1.8, 34, 16, 'medium'),
    ('DRC Linafoot', 'DR Congo', 'CD', 3.5, 42, 20, 'medium'),
    ('Kenya Premier League', 'Kenya', 'KE', 3.0, 65, 18, 'low'),
    ('Tanzania NBC Premier League', 'Tanzania', 'TZ', 2.8, 55, 16, 'low');
