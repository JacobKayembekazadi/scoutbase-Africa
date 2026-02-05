import React from 'react';
import { Player } from '@/lib/types';
import { COLORS } from '@/lib/constants';
import { VerificationBadge, ScoreRing } from '@/components/ui/Shared';

interface PlayerRowProps {
    player: Player;
    onClick: () => void;
    onCompare?: (player: Player) => void;
    isInCompare?: boolean;
}

export const PlayerRow = ({ player, onClick, onCompare, isInCompare }: PlayerRowProps) => {
    return (
        <div
            onClick={onClick}
            style={{
                display: "flex", alignItems: "center", gap: 16, padding: "12px 20px",
                background: COLORS.card, borderRadius: 12,
                border: `1px solid ${isInCompare ? COLORS.accent : COLORS.border}`,
                marginBottom: 8, transition: "transform 0.2s, background 0.2s"
            }}
            onMouseEnter={e => {
                e.currentTarget.style.borderColor = isInCompare ? COLORS.accent : COLORS.accentDim;
                e.currentTarget.style.background = COLORS.surfaceHover;
            }}
            onMouseLeave={e => {
                e.currentTarget.style.borderColor = isInCompare ? COLORS.accent : COLORS.border;
                e.currentTarget.style.background = COLORS.card;
            }}
        >
            <div style={{ width: 44, height: 44, borderRadius: 10, background: COLORS.accentDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>
                {player.flag}
            </div>
            <div style={{ flex: 1, cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontWeight: 700, color: COLORS.text }}>{player.name}</span>
                    <VerificationBadge status={player.verificationStatus} />
                </div>
                <div style={{ fontSize: 12, color: COLORS.textDim }}>{player.position} · {player.club} · {player.age} yrs</div>
            </div>
            <ScoreRing score={player.reliabilityScore} size={44} />
            <div style={{ display: "flex", gap: 4 }}>
                {onCompare && (
                    <button
                        onClick={(e) => { e.stopPropagation(); onCompare(player); }}
                        disabled={isInCompare}
                        style={{ padding: "6px 12px", borderRadius: 6, border: `1px solid ${isInCompare ? COLORS.accent : COLORS.border}`, background: isInCompare ? COLORS.accentDim : "transparent", color: isInCompare ? COLORS.accent : COLORS.text, fontSize: 11, fontWeight: 600, cursor: isInCompare ? "default" : "pointer" }}
                    >
                        {isInCompare ? "Selected" : "Compare"}
                    </button>
                )}
                <button
                    onClick={(e) => { e.stopPropagation(); onClick(); }}
                    style={{
                        padding: "6px 12px",
                        borderRadius: 6,
                        border: "none",
                        background: COLORS.accent,
                        color: COLORS.bg,
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: "pointer"
                    }}
                >
                    View Profile
                </button>
            </div>
        </div>
    );
};
