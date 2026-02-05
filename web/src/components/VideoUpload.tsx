"use client";

import React, { useState, useRef, useCallback } from 'react';
import { COLORS } from '@/lib/constants';
import { TrackAssignment } from './TrackAssignment';

interface UploadJob {
    job_id: string;
    status: 'queued' | 'processing' | 'completed' | 'failed';
    progress: number;
    players_tracked: number;
    video_filename: string;
    error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const VideoUpload = () => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [jobs, setJobs] = useState<UploadJob[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [assigningJobId, setAssigningJobId] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const pollJobStatus = useCallback(async (jobId: string) => {
        try {
            const res = await fetch(`${API_BASE}/status/${jobId}`);
            const data = await res.json();

            setJobs(prev => prev.map(j =>
                j.job_id === jobId ? { ...j, ...data } : j
            ));

            if (data.status === 'processing' || data.status === 'queued') {
                setTimeout(() => pollJobStatus(jobId), 2000);
            }
        } catch (err) {
            console.error('Failed to poll job status:', err);
        }
    }, []);

    const handleUpload = async (file: File) => {
        setUploading(true);
        setError(null);

        const formData = new FormData();
        formData.append('video', file);
        formData.append('home_team', 'Team A');
        formData.append('away_team', 'Team B');
        formData.append('competition', 'Demo Match');

        try {
            const res = await fetch(`${API_BASE}/process`, {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                throw new Error(`Upload failed: ${res.statusText}`);
            }

            const data = await res.json();

            setJobs(prev => [...prev, {
                job_id: data.job_id,
                status: 'queued',
                progress: 0,
                players_tracked: 0,
                video_filename: file.name,
            }]);

            // Start polling for status
            setTimeout(() => pollJobStatus(data.job_id), 2000);

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('video/')) {
            handleUpload(file);
        } else {
            setError('Please upload a video file');
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleUpload(file);
        }
    };

    const viewResults = async (jobId: string) => {
        try {
            const res = await fetch(`${API_BASE}/results/${jobId}`);
            const data = await res.json();
            console.log('Results:', data);
            // Could open a modal here to display results
            alert(`Tracked ${Object.keys(data.players || {}).length} players! Check console for full data.`);
        } catch (err) {
            console.error('Failed to fetch results:', err);
        }
    };

    return (
        <div style={{ padding: 20 }}>
            <h2 style={{ margin: "0 0 16px", fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>
                Upload Match Video
            </h2>

            {/* Drop Zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                    border: `2px dashed ${isDragging ? COLORS.accent : COLORS.border}`,
                    borderRadius: 12,
                    padding: 40,
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: isDragging ? COLORS.accentDim : COLORS.card,
                    transition: 'all 0.2s',
                    marginBottom: 20,
                }}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                />
                {uploading ? (
                    <div style={{ color: COLORS.accent }}>
                        <div style={{ fontSize: 32, marginBottom: 8 }}>⏳</div>
                        Uploading...
                    </div>
                ) : (
                    <>
                        <div style={{ fontSize: 32, marginBottom: 8 }}>🎬</div>
                        <div style={{ color: COLORS.text, fontWeight: 600 }}>
                            Drop a match video here
                        </div>
                        <div style={{ color: COLORS.textDim, fontSize: 13, marginTop: 4 }}>
                            or click to browse (MP4, AVI, WebM)
                        </div>
                    </>
                )}
            </div>

            {error && (
                <div style={{
                    padding: 12,
                    background: COLORS.dangerDim,
                    borderRadius: 8,
                    color: COLORS.danger,
                    marginBottom: 16,
                    fontSize: 13,
                }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Jobs List */}
            {jobs.length > 0 && (
                <div>
                    <h3 style={{ fontSize: 14, fontWeight: 600, color: COLORS.textDim, marginBottom: 12 }}>
                        Processing Jobs
                    </h3>
                    {jobs.map(job => (
                        <div key={job.job_id} style={{
                            background: COLORS.card,
                            border: `1px solid ${COLORS.border}`,
                            borderRadius: 10,
                            padding: 16,
                            marginBottom: 10,
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontWeight: 600, color: COLORS.text }}>{job.video_filename}</div>
                                    <div style={{ fontSize: 12, color: COLORS.textDim }}>Job: {job.job_id}</div>
                                </div>
                                <div style={{
                                    padding: "4px 10px",
                                    borderRadius: 20,
                                    fontSize: 11,
                                    fontWeight: 700,
                                    background: job.status === 'completed' ? COLORS.accentDim :
                                        job.status === 'failed' ? COLORS.dangerDim :
                                            job.status === 'processing' ? COLORS.warningDim : COLORS.surface,
                                    color: job.status === 'completed' ? COLORS.accent :
                                        job.status === 'failed' ? COLORS.danger :
                                            job.status === 'processing' ? COLORS.warning : COLORS.textDim,
                                    textTransform: 'uppercase',
                                }}>
                                    {job.status}
                                </div>
                            </div>

                            {job.status === 'processing' && (
                                <div style={{ marginTop: 12 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                        <span style={{ fontSize: 11, color: COLORS.textDim }}>Progress</span>
                                        <span style={{ fontSize: 11, color: COLORS.accent }}>{Math.round(job.progress * 100)}%</span>
                                    </div>
                                    <div style={{ height: 4, background: COLORS.border, borderRadius: 2, overflow: 'hidden' }}>
                                        <div style={{
                                            height: '100%',
                                            width: `${job.progress * 100}%`,
                                            background: COLORS.accent,
                                            transition: 'width 0.3s',
                                        }} />
                                    </div>
                                </div>
                            )}

                            {job.status === 'completed' && (
                                <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    <button
                                        onClick={() => viewResults(job.job_id)}
                                        style={{
                                            padding: "6px 14px",
                                            borderRadius: 6,
                                            border: "none",
                                            background: COLORS.accent,
                                            color: COLORS.bg,
                                            fontSize: 12,
                                            fontWeight: 600,
                                            cursor: "pointer",
                                        }}
                                    >
                                        View Results ({job.players_tracked} players)
                                    </button>
                                    <button
                                        onClick={() => setAssigningJobId(job.job_id)}
                                        style={{
                                            padding: "6px 14px",
                                            borderRadius: 6,
                                            border: `1px solid ${COLORS.accent}`,
                                            background: COLORS.accentDim,
                                            color: COLORS.accent,
                                            fontSize: 12,
                                            fontWeight: 600,
                                            cursor: "pointer",
                                        }}
                                    >
                                        Assign Players
                                    </button>
                                    <a
                                        href={`${API_BASE}/results/${job.job_id}/video`}
                                        download
                                        style={{
                                            padding: "6px 14px",
                                            borderRadius: 6,
                                            border: `1px solid ${COLORS.border}`,
                                            background: "transparent",
                                            color: COLORS.text,
                                            fontSize: 12,
                                            fontWeight: 600,
                                            textDecoration: 'none',
                                        }}
                                    >
                                        Download Tracked Video
                                    </a>
                                </div>
                            )}

                            {job.status === 'failed' && job.error && (
                                <div style={{ marginTop: 8, fontSize: 12, color: COLORS.danger }}>
                                    Error: {job.error}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Track Assignment Modal */}
            {assigningJobId && (
                <TrackAssignment
                    jobId={assigningJobId}
                    onClose={() => setAssigningJobId(null)}
                />
            )}
        </div>
    );
};
