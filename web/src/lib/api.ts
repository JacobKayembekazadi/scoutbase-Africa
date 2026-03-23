/**
 * ScoutBase Africa - API Client
 * Centralized API functions for communicating with the FastAPI backend
 */

import {
    Player,
    LeagueIntel,
    TracksResponse,
    TrackData,
    SAM3StatusResponse,
    SegmentationRequest,
    SegmentationResponse,
    TrackingRequest,
    TrackingResponse,
    TeamSegmentationRequest,
    TeamSegmentationResponse,
    EnhanceTracksRequest,
    EnhanceTracksResponse,
} from './types';

import { getFirebaseToken } from './firebase';

// In production, use Vercel rewrites proxy to avoid mixed content (HTTPS→HTTP)
// In dev, call the backend directly
const isDev = typeof window !== 'undefined' && window.location.hostname === 'localhost';
export const API_BASE = isDev
    ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    : '/api/backend';

// ---------------------------------------------------------------------------
// Request Timeout — RL3-8
// ---------------------------------------------------------------------------

const DEFAULT_TIMEOUT_MS = 30_000; // 30 seconds for normal requests

/**
 * Wrapper around fetch that enforces a timeout via AbortController
 * and injects Supabase JWT auth header when available.
 */
export async function fetchWithTimeout(
    input: RequestInfo | URL,
    init?: RequestInit & { timeoutMs?: number },
): Promise<Response> {
    const timeoutMs = init?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    // Inject Firebase auth header
    const headers = new Headers(init?.headers);
    try {
        const token = await getFirebaseToken();
        if (token) {
            headers.set('Authorization', `Bearer ${token}`);
        }
    } catch {
        // Auth not available (SSR or not logged in) — continue without token
    }

    try {
        const response = await fetch(input, {
            ...init,
            headers,
            signal: controller.signal,
        });
        return response;
    } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
            throw new Error(
                `Request timed out after ${timeoutMs / 1000}s. The server may be overloaded or unreachable.`
            );
        }
        throw err;
    } finally {
        clearTimeout(timer);
    }
}

// ---------------------------------------------------------------------------
// Error Handling
// ---------------------------------------------------------------------------

export class ApiError extends Error {
    constructor(public status: number, message: string) {
        super(message);
        this.name = 'ApiError';
    }
}

async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let message = response.statusText;
        try {
            const body = await response.text();
            // FastAPI returns errors as {"detail": "..."}, try to extract that
            try {
                const parsed = JSON.parse(body);
                message = parsed.detail || parsed.message || body;
            } catch {
                message = body || message;
            }
        } catch {
            // If we can't read the body at all, fall through to statusText
        }
        throw new ApiError(response.status, message);
    }
    return response.json();
}

// ---------------------------------------------------------------------------
// Player API
// ---------------------------------------------------------------------------

export interface PlayersResponse {
    players: Player[];
    total: number;
}

export interface PlayerFilters {
    nation?: string;
    league?: string;
    position?: string;
    search?: string;
}

export async function getPlayers(filters?: PlayerFilters): Promise<PlayersResponse> {
    const params = new URLSearchParams();
    if (filters?.nation) params.append('nation', filters.nation);
    if (filters?.league) params.append('league', filters.league);
    if (filters?.position) params.append('position', filters.position);
    if (filters?.search) params.append('search', filters.search);

    const queryString = params.toString();
    const url = `${API_BASE}/players${queryString ? `?${queryString}` : ''}`;

    const response = await fetchWithTimeout(url);
    return handleResponse<PlayersResponse>(response);
}

export async function getPlayer(id: string): Promise<Player> {
    const response = await fetchWithTimeout(`${API_BASE}/players/${id}`);
    return handleResponse<Player>(response);
}

export interface PlayerCreateData {
    name: string;
    age: number;
    nation: string;
    flag: string;
    club: string;
    league: string;
    position: string;
    photo?: string | null;
    verificationStatus?: string;
    reliabilityScore?: number;
    dataConfidence?: number;
    scoutNotes?: string;
}

export async function createPlayer(player: PlayerCreateData): Promise<Player> {
    const response = await fetchWithTimeout(`${API_BASE}/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(player),
    });
    return handleResponse<Player>(response);
}

export async function updatePlayer(id: string, updates: Partial<Player>): Promise<Player> {
    const response = await fetchWithTimeout(`${API_BASE}/players/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    return handleResponse<Player>(response);
}

// ---------------------------------------------------------------------------
// League Intelligence API
// ---------------------------------------------------------------------------

export interface LeaguesResponse {
    leagues: LeagueIntel[];
}

export async function getLeagues(): Promise<LeaguesResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/leagues`);
    return handleResponse<LeaguesResponse>(response);
}

// ---------------------------------------------------------------------------
// Shortlist API
// ---------------------------------------------------------------------------

export interface ShortlistResponse {
    shortlist: string[];
}

export async function getShortlist(): Promise<ShortlistResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/shortlist`);
    return handleResponse<ShortlistResponse>(response);
}

export async function addToShortlist(playerId: string): Promise<ShortlistResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/shortlist/${playerId}`, {
        method: 'POST',
    });
    return handleResponse<ShortlistResponse>(response);
}

export async function removeFromShortlist(playerId: string): Promise<ShortlistResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/shortlist/${playerId}`, {
        method: 'DELETE',
    });
    return handleResponse<ShortlistResponse>(response);
}

// ---------------------------------------------------------------------------
// Health Check
// ---------------------------------------------------------------------------

export interface HealthResponse {
    status: string;
    supabase_connected: boolean;
    jobs_in_memory: number;
}

export async function checkHealth(): Promise<HealthResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(response);
}

// ---------------------------------------------------------------------------
// Video Processing API (existing endpoints)
// ---------------------------------------------------------------------------

export interface ProcessingJob {
    job_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    video_filename: string;
    created_at: string;
    completed_at?: string;
    progress: number;
    players_tracked: number;
    error?: string;
}

export interface JobsResponse {
    jobs: ProcessingJob[];
}

export async function getJobs(): Promise<JobsResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/jobs`);
    return handleResponse<JobsResponse>(response);
}

export async function getJobStatus(jobId: string): Promise<ProcessingJob> {
    const response = await fetchWithTimeout(`${API_BASE}/status/${jobId}`);
    return handleResponse<ProcessingJob>(response);
}

export interface ProcessingResults {
    total_frames: number;
    duration_seconds: number;
    players_tracked: number;
    players: Record<string, {
        frames_visible: number;
        estimated_minutes: number;
        sprint_count: number;
        avg_speed_px: number;
        max_speed_px: number;
        heat_map?: number[][];
        visibility_pct?: number;
    }>;
    scout_report?: string;
}

export async function getJobResults(jobId: string): Promise<ProcessingResults> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}`);
    return handleResponse<ProcessingResults>(response);
}

export function getAnnotatedVideoUrl(jobId: string): string {
    return `${API_BASE}/results/${jobId}/video`;
}

export function getPlayerCsvUrl(jobId: string): string {
    return `${API_BASE}/results/${jobId}/csv`;
}

// ---------------------------------------------------------------------------
// Track Assignment API
// ---------------------------------------------------------------------------

export async function getJobTracks(jobId: string): Promise<TracksResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}/tracks`);
    return handleResponse<TracksResponse>(response);
}

export interface AssignTrackResponse {
    message: string;
    assignment: {
        player_id: string;
        assigned_at: string;
        notes?: string;
    };
}

export async function assignTrackToPlayer(
    jobId: string,
    trackId: number,
    playerId: string,
    notes?: string
): Promise<AssignTrackResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}/tracks/${trackId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId, notes }),
    });
    return handleResponse<AssignTrackResponse>(response);
}

export interface CreatePlayerFromTrackData {
    name: string;
    age?: number;
    nation?: string;
    flag?: string;
    club?: string;
    league?: string;
    position?: string;
    notes?: string;
}

export interface CreatePlayerFromTrackResponse {
    message: string;
    player: Player;
    assignment: {
        player_id: string;
        assigned_at: string;
        notes?: string;
    };
}

export async function createPlayerFromTrack(
    jobId: string,
    trackId: number,
    playerData: CreatePlayerFromTrackData
): Promise<CreatePlayerFromTrackResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}/tracks/${trackId}/create-player`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(playerData),
    });
    return handleResponse<CreatePlayerFromTrackResponse>(response);
}

export async function unassignTrack(jobId: string, trackId: number): Promise<{ message: string }> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}/tracks/${trackId}/unassign`, {
        method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
}

// ---------------------------------------------------------------------------
// SAM3 API (Segment Anything Model 3)
// ---------------------------------------------------------------------------

/**
 * Check SAM3 module status and availability.
 * Use this to verify GPU availability and model loading before making SAM3 requests.
 */
export async function getSAM3Status(): Promise<SAM3StatusResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/sam3/status`);
    return handleResponse<SAM3StatusResponse>(response);
}

/**
 * Perform text-prompted segmentation on a single frame.
 *
 * @example
 * ```typescript
 * const result = await sam3Segment({
 *   job_id: 'abc123',
 *   frame_number: 100,
 *   prompt: 'players in blue jerseys',
 *   confidence_threshold: 0.5,
 * });
 * ```
 */
export async function sam3Segment(request: SegmentationRequest): Promise<SegmentationResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/sam3/segment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        timeoutMs: 120_000, // 2 min — GPU-intensive
    });
    return handleResponse<SegmentationResponse>(response);
}

/**
 * Track objects through video frames using SAM3.
 * For long videos, use a higher sample_rate to reduce processing time.
 *
 * @example
 * ```typescript
 * const result = await sam3Track({
 *   job_id: 'abc123',
 *   prompt: 'goalkeeper',
 *   start_frame: 0,
 *   end_frame: 1000,
 *   sample_rate: 10,
 * });
 * ```
 */
export async function sam3Track(request: TrackingRequest): Promise<TrackingResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/sam3/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        timeoutMs: 120_000, // 2 min — GPU-intensive
    });
    return handleResponse<TrackingResponse>(response);
}

/**
 * Segment players into teams based on jersey colors.
 *
 * @example
 * ```typescript
 * const result = await sam3Teams({
 *   job_id: 'abc123',
 *   frame_number: 500,
 *   home_color_hint: 'blue',
 *   away_color_hint: 'red',
 *   include_ball: true,
 * });
 * ```
 */
export async function sam3Teams(request: TeamSegmentationRequest): Promise<TeamSegmentationResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/sam3/teams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        timeoutMs: 120_000, // 2 min — GPU-intensive
    });
    return handleResponse<TeamSegmentationResponse>(response);
}

/**
 * Enhance existing ByteTrack results with SAM3 analysis.
 * Adds team labels, dominant colors, and optional mask data to tracks.
 *
 * @example
 * ```typescript
 * const result = await sam3EnhanceTracks('abc123', {
 *   add_team_labels: true,
 *   add_masks: false,
 *   sample_frames: 20,
 * });
 * ```
 */
export async function sam3EnhanceTracks(
    jobId: string,
    request: EnhanceTracksRequest = {}
): Promise<EnhanceTracksResponse> {
    const response = await fetchWithTimeout(`${API_BASE}/sam3/enhance/${jobId}/tracks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        timeoutMs: 120_000, // 2 min — GPU-intensive
    });
    return handleResponse<EnhanceTracksResponse>(response);
}

// ---------------------------------------------------------------------------
// Video Frame API (for SAM3 visualization)
// ---------------------------------------------------------------------------

export interface VideoInfo {
    total_frames: number;
    fps: number;
    width: number;
    height: number;
    duration_seconds: number;
}

/**
 * Get video metadata including total frames, fps, and dimensions.
 */
export async function getVideoInfo(jobId: string): Promise<VideoInfo> {
    const response = await fetchWithTimeout(`${API_BASE}/results/${jobId}/info`);
    return handleResponse<VideoInfo>(response);
}

/**
 * Get the URL for a specific video frame as JPEG.
 * Use this to display frame previews in the UI.
 */
export function getVideoFrameUrl(jobId: string, frameNumber: number): string {
    return `${API_BASE}/results/${jobId}/frame/${frameNumber}`;
}
