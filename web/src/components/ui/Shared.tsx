import React from 'react';
import { COLORS } from '@/lib/constants';
import { VerificationStatus } from '@/lib/types';

export const VerificationBadge = ({ status }: { status: VerificationStatus }) => {
    const config = {
        verified: { label: "Verified", color: COLORS.accent, bg: COLORS.accentDim, icon: "✓" },
        partial: { label: "Partial", color: COLORS.warning, bg: COLORS.warningDim, icon: "⚠" },
        unverified: { label: "Unverified", color: COLORS.danger, bg: COLORS.dangerDim, icon: "✕" },
    };
    const c = config[status] || config.unverified;
    return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px", borderRadius: 20, fontSize: 10, fontWeight: 700, color: c.color, background: c.bg, letterSpacing: 0.5, textTransform: "uppercase" }}>
            {c.label}
        </span>
    );
};

export const ScoreRing = ({ score, size = 56, label, color }: { score: number | null, size?: number, label?: string, color?: string }) => {
    const radius = (size - 8) / 2;
    const circ = 2 * Math.PI * radius;
    const offset = score != null ? circ - (score / 100) * circ : circ;
    const c = color || (score != null && score >= 75 ? COLORS.accent : score != null && score >= 50 ? COLORS.warning : score != null ? COLORS.danger : COLORS.textMuted);

    return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={COLORS.border} strokeWidth={3} />
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={c} strokeWidth={3}
                    strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
                    style={{ transition: "stroke-dashoffset 1s ease" }} />
            </svg>
            <div style={{ position: "relative", marginTop: -size + 4, height: size - 4, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: size * 0.3, fontWeight: 700, color: c, fontFamily: "'JetBrains Mono', monospace" }}>
                    {score != null ? score : "—"}
                </span>
            </div>
            {label && <span style={{ fontSize: 8, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 600, marginTop: 2 }}>{label}</span>}
        </div>
    );
};

export const SectionTitle = ({ children, icon }: { children: React.ReactNode, icon?: React.ReactNode }) => (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        {icon && <span style={{ fontSize: 14 }}>{icon}</span>}
        <span style={{ fontSize: 11, fontWeight: 700, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 1.5 }}>{children}</span>
        <div style={{ flex: 1, height: 1, background: COLORS.border }} />
    </div>
);

interface VideoThumbProps {
    label: string;
    duration: string;
    hasAI: boolean;
    onClick?: () => void;
}

export const VideoThumb = ({ label, duration, hasAI, onClick }: VideoThumbProps) => (
    <div
        onClick={onClick}
        style={{ background: COLORS.surface, borderRadius: 8, overflow: "hidden", cursor: "pointer", border: `1px solid ${COLORS.border}`, transition: "all 0.2s" }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = COLORS.accent; e.currentTarget.style.transform = "scale(1.02)"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = COLORS.border; e.currentTarget.style.transform = "scale(1)"; }}
    >
        <div style={{ height: 80, background: `linear-gradient(135deg, ${COLORS.surfaceHover}, ${COLORS.bg})`, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.2s" }}>
                <span style={{ color: "#fff", fontSize: 14, marginLeft: 2 }}>▶</span>
            </div>
            <span style={{ position: "absolute", bottom: 4, right: 6, fontSize: 9, color: "#fff", background: "rgba(0,0,0,0.7)", padding: "1px 5px", borderRadius: 3 }}>{duration}</span>
            {hasAI && <span style={{ position: "absolute", top: 4, left: 6, fontSize: 8, color: COLORS.accent, background: COLORS.accentDim, padding: "1px 6px", borderRadius: 3, fontWeight: 700 }}>AI TRACKED</span>}
        </div>
        <div style={{ padding: "6px 8px" }}>
            <div style={{ fontSize: 10, color: COLORS.text, fontWeight: 500 }}>{label}</div>
        </div>
    </div>
);
