import React from 'react';
import { COLORS } from '@/lib/constants';

interface VideoModalProps {
    isOpen: boolean;
    onClose: () => void;
    videoLabel: string;
    duration: string;
    hasAI: boolean;
}

export const VideoModal = ({ isOpen, onClose, videoLabel, duration, hasAI }: VideoModalProps) => {
    if (!isOpen) return null;

    return (
        <div
            onClick={onClose}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.85)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
                padding: 20,
            }}
        >
            <div
                onClick={e => e.stopPropagation()}
                style={{
                    background: COLORS.card,
                    borderRadius: 16,
                    width: '100%',
                    maxWidth: 800,
                    overflow: 'hidden',
                    border: `1px solid ${COLORS.border}`,
                }}
            >
                {/* Header */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '14px 20px',
                    borderBottom: `1px solid ${COLORS.border}`,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{videoLabel}</span>
                        <span style={{ fontSize: 11, color: COLORS.textDim }}>{duration}</span>
                        {hasAI && (
                            <span style={{
                                fontSize: 9,
                                color: COLORS.accent,
                                background: COLORS.accentDim,
                                padding: '2px 8px',
                                borderRadius: 4,
                                fontWeight: 700,
                            }}>
                                AI TRACKED
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            color: COLORS.textDim,
                            cursor: 'pointer',
                            fontSize: 20,
                            padding: '4px 8px',
                        }}
                    >
                        ✕
                    </button>
                </div>

                {/* Video Placeholder */}
                <div style={{
                    aspectRatio: '16/9',
                    background: `linear-gradient(135deg, ${COLORS.bg}, ${COLORS.surface})`,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 16,
                }}>
                    <div style={{
                        width: 80,
                        height: 80,
                        borderRadius: '50%',
                        background: 'rgba(255,255,255,0.1)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: `2px solid ${COLORS.border}`,
                    }}>
                        <span style={{ fontSize: 32, color: COLORS.textDim }}>▶</span>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 14, color: COLORS.textDim, marginBottom: 4 }}>
                            Video playback coming soon
                        </div>
                        <div style={{ fontSize: 11, color: COLORS.textMuted }}>
                            Match footage will be streamable directly from this viewer
                        </div>
                    </div>
                </div>

                {/* Footer with AI insights */}
                {hasAI && (
                    <div style={{
                        padding: '14px 20px',
                        background: COLORS.accentDim,
                        borderTop: `1px solid rgba(0,212,170,0.2)`,
                    }}>
                        <div style={{ fontSize: 10, fontWeight: 700, color: COLORS.accent, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
                            AI Analysis Available
                        </div>
                        <div style={{ fontSize: 12, color: COLORS.text, lineHeight: 1.5 }}>
                            This footage has been processed through our YOLO + ByteTrack vision pipeline.
                            Available metrics: heat maps, distance covered, sprint analysis, key moments, and persistent player tracking.
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
