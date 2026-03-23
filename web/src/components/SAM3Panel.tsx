"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { COLORS } from '@/lib/constants';
import {
    getSAM3Status,
    sam3Segment,
    sam3Teams,
    sam3EnhanceTracks,
    getJobs,
    getVideoInfo,
    getVideoFrameUrl,
    ProcessingJob,
    VideoInfo,
} from '@/lib/api';
import {
    SAM3StatusResponse,
    SegmentationResponse,
    SegmentedObject,
    TeamSegmentationResponse,
    EnhanceTracksResponse,
} from '@/lib/types';

interface SAM3PanelProps {
    onBack?: () => void;
}

type AnalysisMode = 'segment' | 'teams' | 'enhance';

// Colors for bounding boxes
const BOX_COLORS = [
    '#00d4aa', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#84cc16', '#06b6d4'
];

const COLOR_OPTIONS = [
    { label: 'Red', value: 'red', color: '#ef4444' },
    { label: 'Blue', value: 'blue', color: '#3b82f6' },
    { label: 'Green', value: 'green', color: '#22c55e' },
    { label: 'Yellow', value: 'yellow', color: '#eab308' },
    { label: 'White', value: 'white', color: '#f8fafc' },
    { label: 'Black', value: 'black', color: '#1e293b' },
    { label: 'Orange', value: 'orange', color: '#f97316' },
    { label: 'Purple', value: 'purple', color: '#a855f7' },
];

export const SAM3Panel: React.FC<SAM3PanelProps> = ({ onBack }) => {
    // Status state
    const [status, setStatus] = useState<SAM3StatusResponse | null>(null);
    const [statusLoading, setStatusLoading] = useState(true);
    const [statusError, setStatusError] = useState<string | null>(null);

    // Jobs state
    const [jobs, setJobs] = useState<ProcessingJob[]>([]);
    const [selectedJobId, setSelectedJobId] = useState<string>('');

    // Analysis mode
    const [mode, setMode] = useState<AnalysisMode>('segment');

    // Segmentation state
    const [prompt, setPrompt] = useState('football player');
    const [frameNumber, setFrameNumber] = useState(0);
    const [confidence, setConfidence] = useState(0.5);

    // Team segmentation state
    const [homeColor, setHomeColor] = useState('blue');
    const [awayColor, setAwayColor] = useState('red');
    const [includeBall, setIncludeBall] = useState(true);

    // Results state
    const [loading, setLoading] = useState(false);
    const [segmentResult, setSegmentResult] = useState<SegmentationResponse | null>(null);
    const [teamResult, setTeamResult] = useState<TeamSegmentationResponse | null>(null);
    const [enhanceResult, setEnhanceResult] = useState<EnhanceTracksResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Image upload state
    const [uploadedImage, setUploadedImage] = useState<string | null>(null);
    const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imageRef = useRef<HTMLImageElement>(null);

    // Video frame state
    const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
    const [videoFrameUrl, setVideoFrameUrl] = useState<string | null>(null);
    const [frameLoading, setFrameLoading] = useState(false);

    // Load SAM3 status on mount
    useEffect(() => {
        const loadStatus = async () => {
            try {
                setStatusLoading(true);
                const s = await getSAM3Status();
                setStatus(s);
                setStatusError(null);
            } catch (err) {
                setStatusError(err instanceof Error ? err.message : 'Failed to load SAM3 status');
            } finally {
                setStatusLoading(false);
            }
        };
        loadStatus();
    }, []);

    // Load completed jobs
    useEffect(() => {
        const loadJobs = async () => {
            try {
                const response = await getJobs();
                const completedJobs = response.jobs.filter(j => j.status === 'completed');
                setJobs(completedJobs);
                if (completedJobs.length > 0 && !selectedJobId) {
                    setSelectedJobId(completedJobs[0].job_id);
                }
            } catch (err) {
                console.error('Failed to load jobs:', err);
            }
        };
        loadJobs();
    }, []);

    // Load video info when job is selected
    useEffect(() => {
        if (!selectedJobId) {
            setVideoInfo(null);
            setVideoFrameUrl(null);
            return;
        }

        const loadVideoInfo = async () => {
            try {
                const info = await getVideoInfo(selectedJobId);
                setVideoInfo(info);
                // Reset frame number if out of bounds
                if (frameNumber >= info.total_frames) {
                    setFrameNumber(0);
                }
            } catch (err) {
                console.error('Failed to load video info:', err);
                setVideoInfo(null);
            }
        };
        loadVideoInfo();
    }, [selectedJobId]);

    // Update frame preview URL when frame number or job changes
    useEffect(() => {
        if (selectedJobId && !uploadedImage) {
            setFrameLoading(true);
            const url = getVideoFrameUrl(selectedJobId, frameNumber);
            setVideoFrameUrl(url);
            // Also set as image preview URL for canvas rendering
            setImagePreviewUrl(url);
        }
    }, [selectedJobId, frameNumber, uploadedImage]);

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                const dataUrl = reader.result as string;
                const base64 = dataUrl.split(',')[1];
                setUploadedImage(base64);
                setImagePreviewUrl(dataUrl);
                setVideoFrameUrl(null); // Clear video frame preview
                setSegmentResult(null); // Clear previous results
            };
            reader.readAsDataURL(file);
        }
    };

    // Clear uploaded image when switching to video job
    const handleJobSelect = (jobId: string) => {
        setSelectedJobId(jobId);
        if (jobId) {
            setUploadedImage(null);
            setSegmentResult(null);
            setTeamResult(null);
        }
    };

    // Draw bounding boxes on canvas
    const drawResults = useCallback(() => {
        const canvas = canvasRef.current;
        const image = imageRef.current;
        if (!canvas || !image || !segmentResult?.objects.length) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Set canvas size to match image
        canvas.width = image.naturalWidth;
        canvas.height = image.naturalHeight;

        // Draw the image
        ctx.drawImage(image, 0, 0);

        // Draw bounding boxes for each detected object
        segmentResult.objects.forEach((obj, idx) => {
            if (!obj.bbox) return;

            const [x1, y1, x2, y2] = obj.bbox;
            const color = BOX_COLORS[idx % BOX_COLORS.length];

            // Draw box
            ctx.strokeStyle = color;
            ctx.lineWidth = 3;
            ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

            // Draw label background
            const label = `#${idx + 1} ${Math.round(obj.confidence * 100)}%`;
            ctx.font = 'bold 14px sans-serif';
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = color;
            ctx.fillRect(x1, y1 - 22, textWidth + 10, 22);

            // Draw label text
            ctx.fillStyle = '#000';
            ctx.fillText(label, x1 + 5, y1 - 6);

            // Draw centroid dot
            if (obj.centroid) {
                ctx.beginPath();
                ctx.arc(obj.centroid[0], obj.centroid[1], 5, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            }
        });
    }, [segmentResult]);

    // Redraw when results change
    useEffect(() => {
        if (segmentResult?.success && imagePreviewUrl) {
            // Wait for image to load then draw
            const img = imageRef.current;
            if (img) {
                if (img.complete) {
                    drawResults();
                } else {
                    img.onload = drawResults;
                }
            }
        }
    }, [segmentResult, imagePreviewUrl, drawResults]);

    const handleSegment = async () => {
        if (!prompt.trim()) {
            setError('Please enter a text prompt');
            return;
        }

        if (!uploadedImage && !selectedJobId) {
            setError('Please upload an image or select a video job');
            return;
        }

        setLoading(true);
        setError(null);
        setSegmentResult(null);

        try {
            const request = uploadedImage
                ? {
                    image_base64: uploadedImage,
                    prompt: prompt.trim(),
                    confidence_threshold: confidence,
                    return_masks: true,
                    return_bboxes: true,
                }
                : {
                    job_id: selectedJobId,
                    frame_number: frameNumber,
                    prompt: prompt.trim(),
                    confidence_threshold: confidence,
                    return_masks: true,
                    return_bboxes: true,
                };

            const result = await sam3Segment(request);
            setSegmentResult(result);

            if (!result.success) {
                setError(result.error || 'Segmentation failed');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Segmentation failed');
        } finally {
            setLoading(false);
        }
    };

    const handleTeamSegment = async () => {
        if (!selectedJobId) {
            setError('Please select a video job');
            return;
        }

        setLoading(true);
        setError(null);
        setTeamResult(null);

        try {
            const result = await sam3Teams({
                job_id: selectedJobId,
                frame_number: frameNumber,
                home_color_hint: homeColor,
                away_color_hint: awayColor,
                include_ball: includeBall,
            });
            setTeamResult(result);

            if (!result.success) {
                setError(result.error || 'Team segmentation failed');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Team segmentation failed');
        } finally {
            setLoading(false);
        }
    };

    const handleEnhanceTracks = async () => {
        if (!selectedJobId) {
            setError('Please select a video job');
            return;
        }

        setLoading(true);
        setError(null);
        setEnhanceResult(null);

        try {
            const result = await sam3EnhanceTracks(selectedJobId, {
                add_team_labels: true,
                add_masks: false,
                sample_frames: 10,
            });
            setEnhanceResult(result);

            if (!result.success) {
                setError(result.error || 'Track enhancement failed');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Track enhancement failed');
        } finally {
            setLoading(false);
        }
    };

    const rgbToHex = (rgb: [number, number, number]) => {
        return '#' + rgb.map(c => c.toString(16).padStart(2, '0')).join('');
    };

    const renderStatusBadge = () => {
        if (statusLoading) {
            return <span style={{ color: COLORS.textDim }}>Loading...</span>;
        }
        if (statusError || !status) {
            return <span style={{ color: COLORS.danger }}>Offline</span>;
        }
        return (
            <span style={{ color: status.hf_authenticated ? COLORS.accent : COLORS.warning }}>
                {status.hf_authenticated ? 'Ready' : 'No HF Token'}
            </span>
        );
    };

    const renderModeTab = (m: AnalysisMode, label: string, icon: string) => (
        <button
            onClick={() => setMode(m)}
            style={{
                flex: 1,
                padding: '12px 16px',
                background: mode === m ? COLORS.accentDim : 'transparent',
                border: 'none',
                borderRadius: 8,
                color: mode === m ? COLORS.accent : COLORS.textDim,
                fontWeight: 600,
                fontSize: 13,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
            }}
        >
            <span>{icon}</span>
            {label}
        </button>
    );

    return (
        <div style={{ padding: 20 }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
                <div>
                    <h1 style={{
                        margin: 0,
                        fontSize: 24,
                        fontWeight: 700,
                        fontFamily: "'Playfair Display', serif",
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                    }}>
                        <span style={{ fontSize: 28 }}>🎯</span>
                        SAM3 Analysis
                    </h1>
                    <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 4 }}>
                        Text-prompted segmentation powered by Meta SAM3
                    </div>
                </div>
                <div style={{
                    padding: '8px 16px',
                    background: COLORS.card,
                    borderRadius: 8,
                    border: `1px solid ${COLORS.border}`,
                    fontSize: 12,
                }}>
                    Status: {renderStatusBadge()}
                </div>
            </div>

            {/* Status Details */}
            {status && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: 12,
                    marginBottom: 24,
                }}>
                    <div style={{ background: COLORS.card, padding: 16, borderRadius: 12, border: `1px solid ${COLORS.border}` }}>
                        <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 4 }}>DEVICE</div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{(status.device || 'N/A').toUpperCase()}</div>
                    </div>
                    <div style={{ background: COLORS.card, padding: 16, borderRadius: 12, border: `1px solid ${COLORS.border}` }}>
                        <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 4 }}>GPU</div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: status.gpu_available ? COLORS.accent : COLORS.textDim }}>
                            {status.gpu_available ? status.gpu_name || 'Available' : 'Not Available'}
                        </div>
                    </div>
                    <div style={{ background: COLORS.card, padding: 16, borderRadius: 12, border: `1px solid ${COLORS.border}` }}>
                        <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 4 }}>MODEL</div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>
                            {status.model_loaded ? 'Loaded' : 'Not Loaded'}
                        </div>
                    </div>
                    <div style={{ background: COLORS.card, padding: 16, borderRadius: 12, border: `1px solid ${COLORS.border}` }}>
                        <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 4 }}>VARIANT</div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{status.model_variant || 'base'}</div>
                    </div>
                </div>
            )}

            {/* Mode Tabs */}
            <div style={{
                display: 'flex',
                gap: 8,
                marginBottom: 24,
                background: COLORS.card,
                padding: 8,
                borderRadius: 12,
                border: `1px solid ${COLORS.border}`,
            }}>
                {renderModeTab('segment', 'Text Segment', '✨')}
                {renderModeTab('teams', 'Team Analysis', '👥')}
                {renderModeTab('enhance', 'Enhance Tracks', '📊')}
            </div>

            {/* Analysis Form */}
            <div style={{
                background: COLORS.card,
                padding: 24,
                borderRadius: 16,
                border: `1px solid ${COLORS.border}`,
                marginBottom: 24,
            }}>
                {mode === 'segment' && (
                    <>
                        <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>
                            Text-Prompted Segmentation
                        </h3>
                        <p style={{ fontSize: 13, color: COLORS.textDim, marginBottom: 20 }}>
                            Describe what you want to segment (e.g., "football player in blue jersey", "goalkeeper", "soccer ball")
                        </p>

                        {/* Image Source Selection */}
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                IMAGE SOURCE
                            </label>
                            <div style={{ display: 'flex', gap: 12 }}>
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    style={{
                                        flex: 1,
                                        padding: '16px',
                                        background: uploadedImage ? COLORS.accentDim : COLORS.surface,
                                        border: `2px dashed ${uploadedImage ? COLORS.accent : COLORS.border}`,
                                        borderRadius: 12,
                                        color: uploadedImage ? COLORS.accent : COLORS.textDim,
                                        cursor: 'pointer',
                                        fontSize: 13,
                                    }}
                                >
                                    {uploadedImage ? '✓ Image Uploaded' : '📷 Upload Image'}
                                </button>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    onChange={handleImageUpload}
                                    style={{ display: 'none' }}
                                />

                                <div style={{ flex: 1 }}>
                                    <select
                                        value={selectedJobId}
                                        onChange={(e) => handleJobSelect(e.target.value)}
                                        style={{
                                            width: '100%',
                                            padding: '16px',
                                            background: COLORS.surface,
                                            border: `1px solid ${COLORS.border}`,
                                            borderRadius: 12,
                                            color: COLORS.text,
                                            fontSize: 13,
                                        }}
                                    >
                                        <option value="">Select Video Job</option>
                                        {jobs.map(job => (
                                            <option key={job.job_id} value={job.job_id}>
                                                {job.video_filename} ({job.players_tracked} tracks)
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Frame Number (if job selected) */}
                        {selectedJobId && !uploadedImage && (
                            <div style={{ marginBottom: 20 }}>
                                {/* Video Info Bar */}
                                {videoInfo && (
                                    <div style={{
                                        display: 'flex',
                                        gap: 16,
                                        padding: '8px 12px',
                                        background: COLORS.surface,
                                        borderRadius: 8,
                                        marginBottom: 12,
                                        fontSize: 11,
                                        color: COLORS.textDim,
                                    }}>
                                        <span>📹 {videoInfo.total_frames} frames</span>
                                        <span>⏱️ {videoInfo.duration_seconds.toFixed(1)}s</span>
                                        <span>🎬 {videoInfo.fps.toFixed(1)} fps</span>
                                        <span>📐 {videoInfo.width}×{videoInfo.height}</span>
                                    </div>
                                )}

                                <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                    FRAME: {frameNumber} {videoInfo ? `/ ${videoInfo.total_frames - 1}` : ''}
                                    {videoInfo && (
                                        <span style={{ marginLeft: 8, color: COLORS.accent }}>
                                            ({(frameNumber / videoInfo.fps).toFixed(2)}s)
                                        </span>
                                    )}
                                </label>

                                {/* Frame Slider */}
                                <input
                                    type="range"
                                    min={0}
                                    max={videoInfo ? videoInfo.total_frames - 1 : 1000}
                                    value={frameNumber}
                                    onChange={(e) => setFrameNumber(parseInt(e.target.value) || 0)}
                                    style={{ width: '100%', marginBottom: 12 }}
                                />

                                {/* Quick Jump Buttons */}
                                <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                                    <button
                                        onClick={() => setFrameNumber(0)}
                                        style={{
                                            padding: '6px 12px',
                                            background: COLORS.surface,
                                            border: `1px solid ${COLORS.border}`,
                                            borderRadius: 6,
                                            color: COLORS.textDim,
                                            cursor: 'pointer',
                                            fontSize: 11,
                                        }}
                                    >
                                        ⏮️ Start
                                    </button>
                                    <button
                                        onClick={() => setFrameNumber(Math.max(0, frameNumber - (videoInfo?.fps || 30)))}
                                        style={{
                                            padding: '6px 12px',
                                            background: COLORS.surface,
                                            border: `1px solid ${COLORS.border}`,
                                            borderRadius: 6,
                                            color: COLORS.textDim,
                                            cursor: 'pointer',
                                            fontSize: 11,
                                        }}
                                    >
                                        ⏪ -1s
                                    </button>
                                    <button
                                        onClick={() => setFrameNumber(Math.min((videoInfo?.total_frames || 1000) - 1, frameNumber + (videoInfo?.fps || 30)))}
                                        style={{
                                            padding: '6px 12px',
                                            background: COLORS.surface,
                                            border: `1px solid ${COLORS.border}`,
                                            borderRadius: 6,
                                            color: COLORS.textDim,
                                            cursor: 'pointer',
                                            fontSize: 11,
                                        }}
                                    >
                                        +1s ⏩
                                    </button>
                                    {videoInfo && (
                                        <button
                                            onClick={() => setFrameNumber(Math.floor(videoInfo.total_frames / 2))}
                                            style={{
                                                padding: '6px 12px',
                                                background: COLORS.surface,
                                                border: `1px solid ${COLORS.border}`,
                                                borderRadius: 6,
                                                color: COLORS.textDim,
                                                cursor: 'pointer',
                                                fontSize: 11,
                                            }}
                                        >
                                            ⏸️ Middle
                                        </button>
                                    )}
                                    {videoInfo && (
                                        <button
                                            onClick={() => setFrameNumber(videoInfo.total_frames - 1)}
                                            style={{
                                                padding: '6px 12px',
                                                background: COLORS.surface,
                                                border: `1px solid ${COLORS.border}`,
                                                borderRadius: 6,
                                                color: COLORS.textDim,
                                                cursor: 'pointer',
                                                fontSize: 11,
                                            }}
                                        >
                                            End ⏭️
                                        </button>
                                    )}
                                </div>

                                {/* Video Frame Preview */}
                                {videoFrameUrl && !segmentResult && (
                                    <div style={{
                                        borderRadius: 12,
                                        overflow: 'hidden',
                                        border: `1px solid ${COLORS.border}`,
                                        position: 'relative',
                                    }}>
                                        <img
                                            src={videoFrameUrl}
                                            alt={`Frame ${frameNumber}`}
                                            style={{ width: '100%', height: 'auto', display: 'block' }}
                                            onLoad={() => setFrameLoading(false)}
                                            onError={() => setFrameLoading(false)}
                                        />
                                        {frameLoading && (
                                            <div style={{
                                                position: 'absolute',
                                                top: 0,
                                                left: 0,
                                                right: 0,
                                                bottom: 0,
                                                background: 'rgba(0,0,0,0.5)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                color: COLORS.text,
                                            }}>
                                                Loading frame...
                                            </div>
                                        )}
                                        <div style={{
                                            padding: '8px 12px',
                                            background: COLORS.surface,
                                            fontSize: 12,
                                            color: COLORS.textDim,
                                        }}>
                                            📹 Frame {frameNumber} • Ready to analyze with: "{prompt || 'Enter a prompt above'}"
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Prompt Input */}
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                TEXT PROMPT
                            </label>
                            <input
                                type="text"
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                placeholder="e.g., football player in blue jersey"
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    background: COLORS.surface,
                                    border: `1px solid ${COLORS.border}`,
                                    borderRadius: 8,
                                    color: COLORS.text,
                                    fontSize: 14,
                                }}
                            />
                        </div>

                        {/* Confidence Threshold */}
                        <div style={{ marginBottom: 24 }}>
                            <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                CONFIDENCE THRESHOLD: {Math.round(confidence * 100)}%
                            </label>
                            <input
                                type="range"
                                min={0}
                                max={100}
                                value={confidence * 100}
                                onChange={(e) => setConfidence(parseInt(e.target.value) / 100)}
                                style={{ width: '100%' }}
                            />
                        </div>

                        {/* Image Preview */}
                        {imagePreviewUrl && !segmentResult && (
                            <div style={{
                                marginBottom: 20,
                                borderRadius: 12,
                                overflow: 'hidden',
                                border: `1px solid ${COLORS.border}`,
                            }}>
                                <img
                                    src={imagePreviewUrl}
                                    alt="Preview"
                                    style={{ width: '100%', height: 'auto', display: 'block' }}
                                />
                                <div style={{
                                    padding: '8px 12px',
                                    background: COLORS.surface,
                                    fontSize: 12,
                                    color: COLORS.textDim,
                                }}>
                                    Ready to analyze with prompt: "{prompt || 'Enter a prompt above'}"
                                </div>
                            </div>
                        )}

                        <button
                            onClick={handleSegment}
                            disabled={loading || (!uploadedImage && !selectedJobId)}
                            style={{
                                width: '100%',
                                padding: '14px',
                                background: loading ? COLORS.border : COLORS.accent,
                                border: 'none',
                                borderRadius: 10,
                                color: COLORS.bg,
                                fontWeight: 700,
                                fontSize: 14,
                                cursor: loading ? 'not-allowed' : 'pointer',
                                opacity: loading ? 0.7 : 1,
                            }}
                        >
                            {loading ? '⏳ Analyzing...' : '🎯 Run Segmentation'}
                        </button>
                    </>
                )}

                {mode === 'teams' && (
                    <>
                        <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>
                            Team Segmentation
                        </h3>
                        <p style={{ fontSize: 13, color: COLORS.textDim, marginBottom: 20 }}>
                            Automatically segment players into teams based on jersey colors
                        </p>

                        {/* Job Selection */}
                        <div style={{ marginBottom: 20 }}>
                            <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                SELECT VIDEO JOB
                            </label>
                            <select
                                value={selectedJobId}
                                onChange={(e) => handleJobSelect(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    background: COLORS.surface,
                                    border: `1px solid ${COLORS.border}`,
                                    borderRadius: 8,
                                    color: COLORS.text,
                                    fontSize: 14,
                                }}
                            >
                                <option value="">Select a completed job...</option>
                                {jobs.map(job => (
                                    <option key={job.job_id} value={job.job_id}>
                                        {job.video_filename}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Frame Number with Slider */}
                        {selectedJobId && (
                            <div style={{ marginBottom: 20 }}>
                                {/* Video Info Bar */}
                                {videoInfo && (
                                    <div style={{
                                        display: 'flex',
                                        gap: 16,
                                        padding: '8px 12px',
                                        background: COLORS.surface,
                                        borderRadius: 8,
                                        marginBottom: 12,
                                        fontSize: 11,
                                        color: COLORS.textDim,
                                    }}>
                                        <span>📹 {videoInfo.total_frames} frames</span>
                                        <span>⏱️ {videoInfo.duration_seconds.toFixed(1)}s</span>
                                        <span>🎬 {videoInfo.fps.toFixed(1)} fps</span>
                                    </div>
                                )}

                                <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                    FRAME: {frameNumber} {videoInfo ? `/ ${videoInfo.total_frames - 1}` : ''}
                                    {videoInfo && (
                                        <span style={{ marginLeft: 8, color: COLORS.accent }}>
                                            ({(frameNumber / videoInfo.fps).toFixed(2)}s)
                                        </span>
                                    )}
                                </label>

                                {/* Frame Slider */}
                                <input
                                    type="range"
                                    min={0}
                                    max={videoInfo ? videoInfo.total_frames - 1 : 1000}
                                    value={frameNumber}
                                    onChange={(e) => setFrameNumber(parseInt(e.target.value) || 0)}
                                    style={{ width: '100%', marginBottom: 12 }}
                                />

                                {/* Video Frame Preview */}
                                {videoFrameUrl && !teamResult && (
                                    <div style={{
                                        borderRadius: 12,
                                        overflow: 'hidden',
                                        border: `1px solid ${COLORS.border}`,
                                        marginBottom: 16,
                                    }}>
                                        <img
                                            src={videoFrameUrl}
                                            alt={`Frame ${frameNumber}`}
                                            style={{ width: '100%', height: 'auto', display: 'block' }}
                                        />
                                        <div style={{
                                            padding: '8px 12px',
                                            background: COLORS.surface,
                                            fontSize: 12,
                                            color: COLORS.textDim,
                                        }}>
                                            📹 Frame {frameNumber} • Select team colors and analyze
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Team Color Hints */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                            <div>
                                <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                    HOME TEAM COLOR
                                </label>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                    {COLOR_OPTIONS.map(c => (
                                        <button
                                            key={c.value}
                                            onClick={() => setHomeColor(c.value)}
                                            style={{
                                                width: 32,
                                                height: 32,
                                                background: c.color,
                                                border: homeColor === c.value ? `3px solid ${COLORS.accent}` : `2px solid ${COLORS.border}`,
                                                borderRadius: 6,
                                                cursor: 'pointer',
                                            }}
                                            title={c.label}
                                        />
                                    ))}
                                </div>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                    AWAY TEAM COLOR
                                </label>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                    {COLOR_OPTIONS.map(c => (
                                        <button
                                            key={c.value}
                                            onClick={() => setAwayColor(c.value)}
                                            style={{
                                                width: 32,
                                                height: 32,
                                                background: c.color,
                                                border: awayColor === c.value ? `3px solid ${COLORS.accent}` : `2px solid ${COLORS.border}`,
                                                borderRadius: 6,
                                                cursor: 'pointer',
                                            }}
                                            title={c.label}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Include Ball Toggle */}
                        <div style={{ marginBottom: 24 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}>
                                <input
                                    type="checkbox"
                                    checked={includeBall}
                                    onChange={(e) => setIncludeBall(e.target.checked)}
                                    style={{ width: 18, height: 18 }}
                                />
                                <span style={{ fontSize: 14 }}>Include ball detection</span>
                            </label>
                        </div>

                        <button
                            onClick={handleTeamSegment}
                            disabled={loading || !selectedJobId}
                            style={{
                                width: '100%',
                                padding: '14px',
                                background: loading ? COLORS.border : COLORS.accent,
                                border: 'none',
                                borderRadius: 10,
                                color: COLORS.bg,
                                fontWeight: 700,
                                fontSize: 14,
                                cursor: loading || !selectedJobId ? 'not-allowed' : 'pointer',
                                opacity: loading || !selectedJobId ? 0.7 : 1,
                            }}
                        >
                            {loading ? '⏳ Analyzing Teams...' : '👥 Analyze Teams'}
                        </button>
                    </>
                )}

                {mode === 'enhance' && (
                    <>
                        <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600 }}>
                            Enhance ByteTrack Results
                        </h3>
                        <p style={{ fontSize: 13, color: COLORS.textDim, marginBottom: 20 }}>
                            Add team labels and color data to existing tracks using SAM3 analysis
                        </p>

                        {/* Job Selection */}
                        <div style={{ marginBottom: 24 }}>
                            <label style={{ display: 'block', fontSize: 12, color: COLORS.textDim, marginBottom: 8 }}>
                                SELECT VIDEO JOB TO ENHANCE
                            </label>
                            <select
                                value={selectedJobId}
                                onChange={(e) => handleJobSelect(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '12px 16px',
                                    background: COLORS.surface,
                                    border: `1px solid ${COLORS.border}`,
                                    borderRadius: 8,
                                    color: COLORS.text,
                                    fontSize: 14,
                                }}
                            >
                                <option value="">Select a completed job...</option>
                                {jobs.map(job => (
                                    <option key={job.job_id} value={job.job_id}>
                                        {job.video_filename} ({job.players_tracked} tracks)
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button
                            onClick={handleEnhanceTracks}
                            disabled={loading || !selectedJobId}
                            style={{
                                width: '100%',
                                padding: '14px',
                                background: loading ? COLORS.border : COLORS.accent,
                                border: 'none',
                                borderRadius: 10,
                                color: COLORS.bg,
                                fontWeight: 700,
                                fontSize: 14,
                                cursor: loading || !selectedJobId ? 'not-allowed' : 'pointer',
                                opacity: loading || !selectedJobId ? 0.7 : 1,
                            }}
                        >
                            {loading ? '⏳ Enhancing Tracks...' : '📊 Enhance Tracks'}
                        </button>
                    </>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div style={{
                    padding: 16,
                    background: COLORS.dangerDim,
                    border: `1px solid ${COLORS.danger}`,
                    borderRadius: 12,
                    color: COLORS.danger,
                    marginBottom: 24,
                }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>Error</div>
                    <div style={{ fontSize: 13 }}>{error}</div>
                </div>
            )}

            {/* Segmentation Results */}
            {segmentResult && segmentResult.success && (
                <div style={{
                    background: COLORS.card,
                    padding: 24,
                    borderRadius: 16,
                    border: `1px solid ${COLORS.border}`,
                    marginBottom: 24,
                }}>
                    <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span>✅</span> Segmentation Results
                    </h3>

                    {/* Visual Output - Image with bounding boxes */}
                    {imagePreviewUrl && (
                        <div style={{
                            marginBottom: 20,
                            borderRadius: 12,
                            overflow: 'hidden',
                            border: `1px solid ${COLORS.border}`,
                            position: 'relative',
                        }}>
                            {/* Hidden image for reference */}
                            <img
                                ref={imageRef}
                                src={imagePreviewUrl}
                                alt="Source"
                                style={{ display: 'none' }}
                                onLoad={drawResults}
                            />
                            {/* Canvas with drawn bounding boxes */}
                            <canvas
                                ref={canvasRef}
                                style={{
                                    width: '100%',
                                    height: 'auto',
                                    display: 'block',
                                }}
                            />
                            {segmentResult.total_objects === 0 && (
                                <div style={{
                                    position: 'absolute',
                                    top: '50%',
                                    left: '50%',
                                    transform: 'translate(-50%, -50%)',
                                    background: 'rgba(0,0,0,0.8)',
                                    padding: '16px 24px',
                                    borderRadius: 8,
                                    color: COLORS.warning,
                                    fontWeight: 600,
                                }}>
                                    No objects found matching "{segmentResult.prompt}"
                                </div>
                            )}
                        </div>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 20 }}>
                        <div style={{ background: COLORS.surface, padding: 12, borderRadius: 8 }}>
                            <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.accent }}>{segmentResult.total_objects}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Objects Found</div>
                        </div>
                        <div style={{ background: COLORS.surface, padding: 12, borderRadius: 8 }}>
                            <div style={{ fontSize: 24, fontWeight: 700 }}>{Math.round(segmentResult.processing_time_ms / 1000)}s</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Processing Time</div>
                        </div>
                        <div style={{ background: COLORS.surface, padding: 12, borderRadius: 8 }}>
                            <div style={{ fontSize: 24, fontWeight: 700 }}>{segmentResult.frame_size[0]}×{segmentResult.frame_size[1]}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Frame Size</div>
                        </div>
                    </div>

                    {segmentResult.objects.length > 0 && (
                        <div>
                            <div style={{ fontSize: 12, color: COLORS.textDim, marginBottom: 12 }}>DETECTED OBJECTS</div>
                            <div style={{ display: 'grid', gap: 12 }}>
                                {segmentResult.objects.map((obj, idx) => (
                                    <div key={idx} style={{
                                        background: COLORS.surface,
                                        padding: 16,
                                        borderRadius: 12,
                                        border: `1px solid ${COLORS.border}`,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 16,
                                    }}>
                                        {obj.dominant_color && (
                                            <div style={{
                                                width: 40,
                                                height: 40,
                                                borderRadius: 8,
                                                background: rgbToHex(obj.dominant_color),
                                                border: `2px solid ${COLORS.border}`,
                                            }} />
                                        )}
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, marginBottom: 4 }}>Object #{obj.id + 1}</div>
                                            <div style={{ fontSize: 12, color: COLORS.textDim }}>
                                                Confidence: {Math.round(obj.confidence * 100)}% | Area: {obj.area.toLocaleString()}px
                                            </div>
                                        </div>
                                        {obj.bbox && (
                                            <div style={{ fontSize: 11, color: COLORS.textDim, textAlign: 'right' }}>
                                                <div>x: {Math.round(obj.bbox[0])}-{Math.round(obj.bbox[2])}</div>
                                                <div>y: {Math.round(obj.bbox[1])}-{Math.round(obj.bbox[3])}</div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Team Results */}
            {teamResult && teamResult.success && (
                <div style={{
                    background: COLORS.card,
                    padding: 24,
                    borderRadius: 16,
                    border: `1px solid ${COLORS.border}`,
                    marginBottom: 24,
                }}>
                    <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span>👥</span> Team Analysis Results
                    </h3>

                    <div style={{ display: 'grid', gap: 16 }}>
                        {teamResult.teams.map((team, idx) => (
                            <div key={idx} style={{
                                background: COLORS.surface,
                                padding: 16,
                                borderRadius: 12,
                                border: `1px solid ${COLORS.border}`,
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                                    {team.dominant_color && (
                                        <div style={{
                                            width: 24,
                                            height: 24,
                                            borderRadius: 6,
                                            background: rgbToHex(team.dominant_color),
                                            border: `2px solid ${COLORS.border}`,
                                        }} />
                                    )}
                                    <div style={{ fontWeight: 700, fontSize: 16, textTransform: 'capitalize' }}>
                                        {team.team_id} Team
                                    </div>
                                    <div style={{
                                        marginLeft: 'auto',
                                        background: COLORS.accentDim,
                                        color: COLORS.accent,
                                        padding: '4px 12px',
                                        borderRadius: 20,
                                        fontSize: 12,
                                        fontWeight: 600,
                                    }}>
                                        {team.player_count} players
                                    </div>
                                </div>
                            </div>
                        ))}

                        {teamResult.ball && (
                            <div style={{
                                background: COLORS.surface,
                                padding: 16,
                                borderRadius: 12,
                                border: `1px solid ${COLORS.warning}`,
                            }}>
                                <div style={{ fontWeight: 700, color: COLORS.warning }}>
                                    ⚽ Ball Detected
                                </div>
                                <div style={{ fontSize: 12, color: COLORS.textDim, marginTop: 4 }}>
                                    Confidence: {Math.round(teamResult.ball.confidence * 100)}%
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Enhance Results */}
            {enhanceResult && enhanceResult.success && (
                <div style={{
                    background: COLORS.card,
                    padding: 24,
                    borderRadius: 16,
                    border: `1px solid ${COLORS.border}`,
                }}>
                    <h3 style={{ margin: '0 0 16px', fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span>📊</span> Enhanced Tracks
                    </h3>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
                        <div style={{ background: COLORS.surface, padding: 16, borderRadius: 12, textAlign: 'center' }}>
                            <div style={{ fontSize: 28, fontWeight: 700, color: COLORS.blue }}>{enhanceResult.home_team_count}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Home Team</div>
                        </div>
                        <div style={{ background: COLORS.surface, padding: 16, borderRadius: 12, textAlign: 'center' }}>
                            <div style={{ fontSize: 28, fontWeight: 700, color: COLORS.danger }}>{enhanceResult.away_team_count}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Away Team</div>
                        </div>
                        <div style={{ background: COLORS.surface, padding: 16, borderRadius: 12, textAlign: 'center' }}>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{enhanceResult.referee_count}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Referees</div>
                        </div>
                        <div style={{ background: COLORS.surface, padding: 16, borderRadius: 12, textAlign: 'center' }}>
                            <div style={{ fontSize: 28, fontWeight: 700, color: COLORS.textDim }}>{enhanceResult.unknown_count}</div>
                            <div style={{ fontSize: 11, color: COLORS.textDim }}>Unknown</div>
                        </div>
                    </div>

                    <div style={{ fontSize: 12, color: COLORS.textDim }}>
                        Processed in {Math.round(enhanceResult.processing_time_ms / 1000)}s | {enhanceResult.total_tracks} total tracks
                    </div>
                </div>
            )}
        </div>
    );
};
