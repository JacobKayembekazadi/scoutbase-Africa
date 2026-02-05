"use client";

import React, { useState, useEffect } from 'react';
import { COLORS } from '@/lib/constants';
import { Player, TrackData, TracksResponse } from '@/lib/types';
import {
    getJobTracks,
    getPlayers,
    assignTrackToPlayer,
    createPlayerFromTrack,
    unassignTrack,
    CreatePlayerFromTrackData,
} from '@/lib/api';

interface TrackAssignmentProps {
    jobId: string;
    onClose: () => void;
}

export const TrackAssignment: React.FC<TrackAssignmentProps> = ({ jobId, onClose }) => {
    const [tracks, setTracks] = useState<TrackData[]>([]);
    const [players, setPlayers] = useState<Player[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [assignedCount, setAssignedCount] = useState(0);
    const [expandedTrack, setExpandedTrack] = useState<number | null>(null);
    const [creatingPlayer, setCreatingPlayer] = useState<number | null>(null);
    const [newPlayerName, setNewPlayerName] = useState('');
    const [newPlayerPosition, setNewPlayerPosition] = useState('');

    useEffect(() => {
        loadData();
    }, [jobId]);

    const loadData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [tracksRes, playersRes] = await Promise.all([
                getJobTracks(jobId),
                getPlayers(),
            ]);
            setTracks(tracksRes.tracks);
            setAssignedCount(tracksRes.assigned_count);
            setPlayers(playersRes.players);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const handleAssign = async (trackId: number, playerId: number) => {
        try {
            await assignTrackToPlayer(jobId, trackId, playerId);
            await loadData();
            setExpandedTrack(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to assign track');
        }
    };

    const handleUnassign = async (trackId: number) => {
        try {
            await unassignTrack(jobId, trackId);
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to unassign track');
        }
    };

    const handleCreatePlayer = async (trackId: number) => {
        if (!newPlayerName.trim()) {
            setError('Please enter a player name');
            return;
        }

        try {
            const playerData: CreatePlayerFromTrackData = {
                name: newPlayerName.trim(),
                position: newPlayerPosition || 'Unknown',
            };
            await createPlayerFromTrack(jobId, trackId, playerData);
            setNewPlayerName('');
            setNewPlayerPosition('');
            setCreatingPlayer(null);
            await loadData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create player');
        }
    };

    const getZoneLabel = (track: TrackData): string => {
        if (!track.heat_map) return 'N/A';
        const zones = track.heat_map as { zones?: Record<string, number> };
        if (zones.zones) {
            const entries = Object.entries(zones.zones);
            if (entries.length === 0) return 'N/A';
            const [topZone, topPct] = entries.reduce((a, b) => a[1] > b[1] ? a : b);
            return `${Math.round(topPct)}% ${topZone}`;
        }
        return 'N/A';
    };

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.8)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                padding: 20,
            }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                style={{
                    background: COLORS.bg,
                    borderRadius: 16,
                    width: '100%',
                    maxWidth: 700,
                    maxHeight: '90vh',
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column',
                    border: `1px solid ${COLORS.border}`,
                }}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '20px 24px',
                        borderBottom: `1px solid ${COLORS.border}`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }}
                >
                    <div>
                        <h2 style={{
                            margin: 0,
                            fontSize: 20,
                            fontWeight: 700,
                            color: COLORS.text,
                            fontFamily: "'Playfair Display', serif",
                        }}>
                            Assign Players to Tracks
                        </h2>
                        <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 4 }}>
                            Job: {jobId.slice(0, 8)}... | {tracks.length} tracks detected | {assignedCount} assigned
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            fontSize: 24,
                            color: COLORS.textDim,
                            cursor: 'pointer',
                            padding: 4,
                        }}
                    >
                        &times;
                    </button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
                    {loading ? (
                        <div style={{ textAlign: 'center', padding: 40, color: COLORS.textDim }}>
                            Loading tracks...
                        </div>
                    ) : error ? (
                        <div style={{
                            padding: 16,
                            background: COLORS.dangerDim,
                            borderRadius: 8,
                            color: COLORS.danger,
                            marginBottom: 16,
                        }}>
                            {error}
                        </div>
                    ) : tracks.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: 40, color: COLORS.textDim }}>
                            No tracks found in this job.
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            {tracks.map((track) => (
                                <div
                                    key={track.track_id}
                                    style={{
                                        background: COLORS.card,
                                        border: `1px solid ${track.assignment ? COLORS.accent : COLORS.border}`,
                                        borderRadius: 12,
                                        padding: 16,
                                    }}
                                >
                                    {/* Track Header */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <span style={{
                                                    fontSize: 16,
                                                    fontWeight: 700,
                                                    color: COLORS.text,
                                                }}>
                                                    Track #{track.track_id}
                                                </span>
                                                <span style={{ fontSize: 13, color: COLORS.textDim }}>
                                                    {track.estimated_minutes.toFixed(1)} min | {track.sprint_count} sprints | {getZoneLabel(track)}
                                                </span>
                                            </div>

                                            {/* Assignment Status */}
                                            {track.assignment ? (
                                                <div style={{
                                                    marginTop: 8,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 8,
                                                }}>
                                                    <div style={{
                                                        width: '100%',
                                                        height: 6,
                                                        background: COLORS.accent,
                                                        borderRadius: 3,
                                                    }} />
                                                    <span style={{
                                                        fontSize: 13,
                                                        color: COLORS.accent,
                                                        fontWeight: 600,
                                                        whiteSpace: 'nowrap',
                                                    }}>
                                                        {track.assignment.player_name}
                                                    </span>
                                                </div>
                                            ) : (
                                                <div style={{
                                                    marginTop: 8,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 8,
                                                }}>
                                                    <div style={{
                                                        width: '100%',
                                                        height: 6,
                                                        background: COLORS.border,
                                                        borderRadius: 3,
                                                    }} />
                                                    <span style={{
                                                        fontSize: 13,
                                                        color: COLORS.textDim,
                                                        whiteSpace: 'nowrap',
                                                    }}>
                                                        Unassigned
                                                    </span>
                                                </div>
                                            )}
                                        </div>

                                        {/* Action Buttons */}
                                        <div style={{ display: 'flex', gap: 8, marginLeft: 16 }}>
                                            {track.assignment ? (
                                                <button
                                                    onClick={() => handleUnassign(track.track_id)}
                                                    style={{
                                                        padding: '6px 12px',
                                                        borderRadius: 6,
                                                        border: `1px solid ${COLORS.border}`,
                                                        background: 'transparent',
                                                        color: COLORS.textDim,
                                                        fontSize: 12,
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Unassign
                                                </button>
                                            ) : (
                                                <>
                                                    <button
                                                        onClick={() => setExpandedTrack(expandedTrack === track.track_id ? null : track.track_id)}
                                                        style={{
                                                            padding: '6px 12px',
                                                            borderRadius: 6,
                                                            border: `1px solid ${COLORS.accent}`,
                                                            background: COLORS.accentDim,
                                                            color: COLORS.accent,
                                                            fontSize: 12,
                                                            fontWeight: 600,
                                                            cursor: 'pointer',
                                                        }}
                                                    >
                                                        Select Player
                                                    </button>
                                                    <button
                                                        onClick={() => setCreatingPlayer(creatingPlayer === track.track_id ? null : track.track_id)}
                                                        style={{
                                                            padding: '6px 12px',
                                                            borderRadius: 6,
                                                            border: `1px solid ${COLORS.border}`,
                                                            background: 'transparent',
                                                            color: COLORS.text,
                                                            fontSize: 12,
                                                            cursor: 'pointer',
                                                        }}
                                                    >
                                                        + New
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </div>

                                    {/* Player Selection Dropdown */}
                                    {expandedTrack === track.track_id && !track.assignment && (
                                        <div style={{
                                            marginTop: 16,
                                            padding: 12,
                                            background: COLORS.surface,
                                            borderRadius: 8,
                                            maxHeight: 200,
                                            overflow: 'auto',
                                        }}>
                                            <div style={{
                                                fontSize: 12,
                                                color: COLORS.textDim,
                                                marginBottom: 8,
                                                fontWeight: 600,
                                            }}>
                                                Select a player:
                                            </div>
                                            {players.length === 0 ? (
                                                <div style={{ fontSize: 13, color: COLORS.textDim }}>
                                                    No players in database. Create a new player first.
                                                </div>
                                            ) : (
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                    {players.map((player) => (
                                                        <button
                                                            key={player.id}
                                                            onClick={() => handleAssign(track.track_id, player.id)}
                                                            style={{
                                                                padding: '10px 12px',
                                                                borderRadius: 6,
                                                                border: 'none',
                                                                background: COLORS.card,
                                                                color: COLORS.text,
                                                                textAlign: 'left',
                                                                cursor: 'pointer',
                                                                display: 'flex',
                                                                justifyContent: 'space-between',
                                                                alignItems: 'center',
                                                            }}
                                                        >
                                                            <span>
                                                                {player.flag} {player.name}
                                                            </span>
                                                            <span style={{ fontSize: 12, color: COLORS.textDim }}>
                                                                {player.position} | {player.club}
                                                            </span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Create New Player Form */}
                                    {creatingPlayer === track.track_id && !track.assignment && (
                                        <div style={{
                                            marginTop: 16,
                                            padding: 12,
                                            background: COLORS.surface,
                                            borderRadius: 8,
                                        }}>
                                            <div style={{
                                                fontSize: 12,
                                                color: COLORS.textDim,
                                                marginBottom: 12,
                                                fontWeight: 600,
                                            }}>
                                                Create new player:
                                            </div>
                                            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                                                <input
                                                    type="text"
                                                    placeholder="Player name"
                                                    value={newPlayerName}
                                                    onChange={(e) => setNewPlayerName(e.target.value)}
                                                    style={{
                                                        flex: 1,
                                                        padding: '8px 12px',
                                                        borderRadius: 6,
                                                        border: `1px solid ${COLORS.border}`,
                                                        background: COLORS.card,
                                                        color: COLORS.text,
                                                        fontSize: 13,
                                                    }}
                                                />
                                                <select
                                                    value={newPlayerPosition}
                                                    onChange={(e) => setNewPlayerPosition(e.target.value)}
                                                    style={{
                                                        padding: '8px 12px',
                                                        borderRadius: 6,
                                                        border: `1px solid ${COLORS.border}`,
                                                        background: COLORS.card,
                                                        color: COLORS.text,
                                                        fontSize: 13,
                                                    }}
                                                >
                                                    <option value="">Position</option>
                                                    <option value="GK">GK</option>
                                                    <option value="CB">CB</option>
                                                    <option value="LB">LB</option>
                                                    <option value="RB">RB</option>
                                                    <option value="DM">DM</option>
                                                    <option value="CM">CM</option>
                                                    <option value="AM">AM</option>
                                                    <option value="LW">LW</option>
                                                    <option value="RW">RW</option>
                                                    <option value="ST">ST</option>
                                                </select>
                                            </div>
                                            <div style={{ display: 'flex', gap: 8 }}>
                                                <button
                                                    onClick={() => handleCreatePlayer(track.track_id)}
                                                    style={{
                                                        padding: '8px 16px',
                                                        borderRadius: 6,
                                                        border: 'none',
                                                        background: COLORS.accent,
                                                        color: COLORS.bg,
                                                        fontSize: 12,
                                                        fontWeight: 600,
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Create & Assign
                                                </button>
                                                <button
                                                    onClick={() => {
                                                        setCreatingPlayer(null);
                                                        setNewPlayerName('');
                                                        setNewPlayerPosition('');
                                                    }}
                                                    style={{
                                                        padding: '8px 16px',
                                                        borderRadius: 6,
                                                        border: `1px solid ${COLORS.border}`,
                                                        background: 'transparent',
                                                        color: COLORS.textDim,
                                                        fontSize: 12,
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div
                    style={{
                        padding: '16px 24px',
                        borderTop: `1px solid ${COLORS.border}`,
                        display: 'flex',
                        justifyContent: 'flex-end',
                        gap: 12,
                    }}
                >
                    <button
                        onClick={onClose}
                        style={{
                            padding: '10px 20px',
                            borderRadius: 8,
                            border: 'none',
                            background: COLORS.accent,
                            color: COLORS.bg,
                            fontSize: 13,
                            fontWeight: 600,
                            cursor: 'pointer',
                        }}
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
};
