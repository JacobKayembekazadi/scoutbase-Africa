export type VerificationStatus = 'verified' | 'partial' | 'unverified';

export interface PlayerStats {
    appearances: number;
    goals: number;
    assists: number;
    minutes: number;
    cards: {
        yellow: number;
        red: number;
    };
}

export interface CareerEntry {
    club: string;
    period: string;
    level: string;
    apps: number | null;
}

export interface MedicalInfo {
    injuries: number | null;
    lastInjury: string;
    clearance: string;
    fitnessScore: number | null;
}

export interface BehavioralInfo {
    training: number | null; // percentage
    discipline: string;
    languages: string[];
    leadership: string;
}

export interface ContractInfo {
    status: string;
    expiry: string;
    compensation: string;
    tms: string;
}

export interface Player {
    id: string;
    name: string;
    age: number;
    nation: string;
    flag: string;
    club: string;
    league: string;
    position: string;
    photo: string | null;
    verificationStatus: VerificationStatus;
    reliabilityScore: number;
    dataConfidence: number;
    stats: PlayerStats;
    career: CareerEntry[];
    medical: MedicalInfo;
    behavioral: BehavioralInfo;
    contract: ContractInfo;
    matchClips: number;
    fullMatches: number;
    scoutNotes: string;
}

export interface LeagueIntel {
    name: string;
    country: string;
    strength: number; // 1-10
    reliability: number; // percentage
    clubs: number;
    risk: 'Low' | 'Medium' | 'High';
}

// ---------------------------------------------------------------------------
// Track Assignment Types
// ---------------------------------------------------------------------------

export interface TrackAssignment {
    player_id: string;
    player_name: string;
    assigned_at: string;
    notes?: string;
}

export interface TrackData {
    track_id: number;
    frames_visible: number;
    estimated_minutes: number;
    sprint_count: number;
    avg_speed_px: number;
    max_speed_px: number;
    heat_map?: { zones: Record<string, number> } | number[][];
    visibility_pct: number;
    first_seen_minute: number;
    last_seen_minute: number;
    assignment?: TrackAssignment;
}

export interface TracksResponse {
    job_id: string;
    total_tracks: number;
    assigned_count: number;
    tracks: TrackData[];
}

// ---------------------------------------------------------------------------
// SAM3 Types
// ---------------------------------------------------------------------------

export interface SAM3StatusResponse {
    available: boolean;
    model_loaded: boolean;
    model_variant?: string;
    device: string;
    gpu_available: boolean;
    gpu_name?: string;
    gpu_memory_gb?: number;
    hf_authenticated: boolean;
    checkpoint_path?: string;
    error?: string;
}

export interface SegmentedObject {
    id: number;
    confidence: number;
    bbox?: [number, number, number, number]; // [x1, y1, x2, y2]
    mask_rle?: string;
    area: number;
    centroid: [number, number];
    dominant_color?: [number, number, number]; // RGB
}

export interface SegmentationRequest {
    image_base64?: string;
    frame_path?: string;
    job_id?: string;
    frame_number?: number;
    prompt: string;
    confidence_threshold?: number;
    return_masks?: boolean;
    return_bboxes?: boolean;
}

export interface SegmentationResponse {
    success: boolean;
    prompt: string;
    objects: SegmentedObject[];
    total_objects: number;
    processing_time_ms: number;
    frame_size: [number, number];
    error?: string;
}

export interface TrackingRequest {
    job_id: string;
    prompt: string;
    start_frame?: number;
    end_frame?: number;
    sample_rate?: number;
    max_objects?: number;
}

export interface TrackedFrame {
    frame_number: number;
    timestamp_ms: number;
    objects: SegmentedObject[];
}

export interface TrackingResponse {
    success: boolean;
    job_id: string;
    prompt: string;
    total_frames_processed: number;
    frames: TrackedFrame[];
    processing_time_ms: number;
    error?: string;
}

export interface TeamSegmentationRequest {
    job_id: string;
    frame_number?: number;
    home_color_hint?: string;
    away_color_hint?: string;
    include_ball?: boolean;
    include_referee?: boolean;
}

export interface TeamData {
    team_id: 'home' | 'away' | 'referee' | 'unknown';
    player_count: number;
    dominant_color?: [number, number, number];
    players: SegmentedObject[];
}

export interface TeamSegmentationResponse {
    success: boolean;
    job_id: string;
    frame_number?: number;
    teams: TeamData[];
    ball?: SegmentedObject;
    processing_time_ms: number;
    error?: string;
}

export interface EnhanceTracksRequest {
    prompt?: string;
    add_masks?: boolean;
    add_team_labels?: boolean;
    sample_frames?: number;
}

export interface EnhancedTrack {
    track_id: number;
    team_label?: 'home' | 'away' | 'referee' | 'unknown';
    dominant_color?: [number, number, number];
    jersey_number?: string;
    confidence: number;
    sample_masks?: string[];
}

export interface EnhanceTracksResponse {
    success: boolean;
    job_id: string;
    enhanced_tracks: EnhancedTrack[];
    total_tracks: number;
    home_team_count: number;
    away_team_count: number;
    referee_count: number;
    unknown_count: number;
    processing_time_ms: number;
    error?: string;
}
