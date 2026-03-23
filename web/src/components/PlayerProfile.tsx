import React, { useState } from 'react';
import { Player } from '@/lib/types';
import { COLORS } from '@/lib/constants';
import { VerificationBadge, ScoreRing, SectionTitle, VideoThumb } from '@/components/ui/Shared';
import { VideoModal } from '@/components/ui/VideoModal';

interface PlayerProfileProps {
    player: Player;
    onBack: () => void;
    onCompare: (player: Player) => void;
    isInCompare: boolean;
    onToggleShortlist: (playerId: string) => void;
    isInShortlist: boolean;
    onRequestReport: (player: Player) => void;
}

const StatBlock = ({ label, value, sub }: { label: string, value: string | number | null, sub?: string }) => (
    <div style={{ textAlign: "center", padding: "10px 6px" }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.text, fontFamily: "'JetBrains Mono', monospace" }}>{value ?? "—"}</div>
        <div style={{ fontSize: 10, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.8, marginTop: 2 }}>{label}</div>
        {sub && <div style={{ fontSize: 9, color: COLORS.textMuted, marginTop: 2 }}>{sub}</div>}
    </div>
);

const Tab = ({ label, active, onClick, count }: { label: string, active: boolean, onClick: () => void, count?: number }) => (
    <button onClick={onClick} style={{
        padding: "8px 16px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
        color: active ? COLORS.accent : COLORS.textDim,
        background: active ? COLORS.accentDim : "transparent",
        borderRadius: 6, display: "flex", alignItems: "center", gap: 6,
        transition: "all 0.2s",
        letterSpacing: 0.3,
    }}>
        {label}
        {count != undefined && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 10, background: active ? COLORS.accent : COLORS.textMuted, color: active ? COLORS.bg : COLORS.text }}>{count}</span>}
    </button>
);

export const PlayerProfile = ({ player, onBack, onCompare, isInCompare, onToggleShortlist, isInShortlist, onRequestReport }: PlayerProfileProps) => {
    const [activeTab, setActiveTab] = useState("overview");
    const [videoModal, setVideoModal] = useState<{ isOpen: boolean; label: string; duration: string; hasAI: boolean }>({
        isOpen: false,
        label: '',
        duration: '',
        hasAI: false
    });

    const openVideoModal = (label: string, duration: string, hasAI: boolean) => {
        setVideoModal({ isOpen: true, label, duration, hasAI });
    };

    const tabs = [
        { key: "overview", label: "Overview" },
        { key: "performance", label: "Performance" },
        { key: "medical", label: "Medical" },
        { key: "video", label: "Video Evidence", count: player.matchClips + player.fullMatches },
        { key: "behavioral", label: "Profile" },
        { key: "contract", label: "Contract" },
    ];

    return (
        <div>
            <button onClick={onBack} style={{ background: "none", border: "none", color: COLORS.textDim, cursor: "pointer", fontSize: 12, marginBottom: 16, padding: 0, display: "flex", alignItems: "center", gap: 4 }}>
                ← Back to Players
            </button>

            {/* Header */}
            <div style={{ display: "flex", gap: 20, alignItems: "flex-start", marginBottom: 20, flexWrap: "wrap" }}>
                <div style={{ width: 80, height: 80, borderRadius: 12, background: `linear-gradient(135deg, ${COLORS.accentDim}, ${COLORS.surfaceHover})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, border: `2px solid ${COLORS.border}`, flexShrink: 0 }}>
                    {player.flag}
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        <h2 style={{ margin: 0, fontSize: 22, color: COLORS.text, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>{player.name}</h2>
                        <VerificationBadge status={player.verificationStatus} />
                    </div>
                    <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 4 }}>
                        {player.age} yrs · {player.position} · {player.club} · {player.league}
                    </div>
                    <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
                        <button
                            onClick={() => onToggleShortlist(player.id)}
                            style={{
                                padding: "6px 14px",
                                borderRadius: 6,
                                border: isInShortlist ? `1px solid ${COLORS.accent}` : "none",
                                background: isInShortlist ? COLORS.accentDim : COLORS.accent,
                                color: isInShortlist ? COLORS.accent : COLORS.bg,
                                fontSize: 11,
                                fontWeight: 700,
                                cursor: "pointer",
                                letterSpacing: 0.3
                            }}
                        >
                            {isInShortlist ? "★ In Shortlist" : "+ Add to Shortlist"}
                        </button>
                        <button
                            onClick={() => onRequestReport(player)}
                            style={{ padding: "6px 14px", borderRadius: 6, border: `1px solid ${COLORS.border}`, background: "transparent", color: COLORS.textDim, fontSize: 11, fontWeight: 600, cursor: "pointer" }}
                        >
                            Request Full Report
                        </button>
                        <button
                            onClick={() => onCompare(player)}
                            disabled={isInCompare}
                            style={{ padding: "6px 14px", borderRadius: 6, border: `1px solid ${isInCompare ? COLORS.accent : COLORS.border}`, background: isInCompare ? COLORS.accentDim : "transparent", color: isInCompare ? COLORS.accent : COLORS.textDim, fontSize: 11, fontWeight: 600, cursor: isInCompare ? "default" : "pointer" }}
                        >
                            {isInCompare ? "Comparing..." : "Compare"}
                        </button>
                    </div>
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                    <ScoreRing score={player.reliabilityScore} label="Reliability" size={64} />
                    <ScoreRing score={player.dataConfidence} label="Data Confidence" size={64} color={COLORS.blue} />
                </div>
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", gap: 4, marginBottom: 20, flexWrap: "wrap", borderBottom: `1px solid ${COLORS.border}`, paddingBottom: 8 }}>
                {tabs.map(t => <Tab key={t.key} label={t.label} active={activeTab === t.key} onClick={() => setActiveTab(t.key)} count={t.count} />)}
            </div>

            {/* Tab Content */}
            {activeTab === "overview" && (
                <div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: 8, background: COLORS.card, borderRadius: 10, padding: 12, marginBottom: 16, border: `1px solid ${COLORS.border}` }}>
                        <StatBlock label="Apps" value={player.stats?.appearances ?? 0} />
                        <StatBlock label="Goals" value={player.stats?.goals ?? 0} />
                        <StatBlock label="Assists" value={player.stats?.assists ?? 0} />
                        <StatBlock label="Minutes" value={player.stats?.minutes?.toLocaleString() ?? '0'} />
                        <StatBlock label="Yellows" value={player.stats?.cards?.yellow ?? 0} />
                        <StatBlock label="Reds" value={player.stats?.cards?.red ?? 0} />
                    </div>

                    <SectionTitle icon="📋">Career History</SectionTitle>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 20 }}>
                        {player.career.map((c, i) => (
                            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
                                <div style={{ width: 3, height: 32, borderRadius: 2, background: i === 0 ? COLORS.accent : COLORS.textMuted }} />
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text }}>{c.club}</div>
                                    <div style={{ fontSize: 11, color: COLORS.textDim }}>{c.period} · {c.level}</div>
                                </div>
                                <div style={{ fontSize: 12, color: c.apps ? COLORS.text : COLORS.danger, fontFamily: "'JetBrains Mono', monospace" }}>
                                    {c.apps ?? "No data"} {c.apps && "apps"}
                                </div>
                            </div>
                        ))}
                    </div>

                    <SectionTitle icon="🎯">Scout Notes</SectionTitle>
                    <div style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}`, fontSize: 13, color: COLORS.textDim, lineHeight: 1.6, fontStyle: "italic" }}>
                        "{player.scoutNotes}"
                    </div>
                </div>
            )}

            {activeTab === "performance" && (
                <div>
                    <SectionTitle icon="📊">Season Performance</SectionTitle>
                    <div style={{ background: COLORS.card, borderRadius: 10, padding: 20, border: `1px solid ${COLORS.border}`, marginBottom: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                            {[
                                { label: "Goal Rate", val: (player.stats.goals / player.stats.appearances * 100).toFixed(0) + "%", sub: "per appearance" },
                                { label: "Mins/Goal", val: player.stats.goals > 0 ? Math.round(player.stats.minutes / player.stats.goals) : "—" },
                                { label: "Involvement", val: ((player.stats.goals + player.stats.assists) / player.stats.appearances).toFixed(2), sub: "G+A per app" },
                                { label: "Availability", val: Math.round(player.stats.minutes / (player.stats.appearances * 90) * 100) + "%", sub: "of possible mins" },
                            ].map((s, i) => (
                                <div key={i} style={{ textAlign: "center", flex: 1, minWidth: 80 }}>
                                    <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.accent, fontFamily: "'JetBrains Mono', monospace" }}>{s.val}</div>
                                    <div style={{ fontSize: 10, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.5 }}>{s.label}</div>
                                    {s.sub && <div style={{ fontSize: 9, color: COLORS.textMuted }}>{s.sub}</div>}
                                </div>
                            ))}
                        </div>

                        {/* Visual bar chart */}
                        <div style={{ fontSize: 10, color: COLORS.textDim, marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Minutes by Month (Simulated)</div>
                        <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 60 }}>
                            {[65, 90, 78, 90, 85, 70, 90, 60, 88, 90].map((v, i) => (
                                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                                    <div style={{ width: "100%", height: v * 0.6, background: `linear-gradient(to top, ${COLORS.accent}, ${COLORS.accentDim})`, borderRadius: "3px 3px 0 0", transition: "height 0.5s ease" }} />
                                    <span style={{ fontSize: 8, color: COLORS.textMuted }}>{["A", "S", "O", "N", "D", "J", "F", "M", "A", "M"][i]}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div style={{ padding: 14, background: COLORS.accentDim, borderRadius: 8, border: `1px solid rgba(0,212,170,0.2)`, fontSize: 12, color: COLORS.accent }}>
                        ⚡ AI Analysis Available — Performance data includes AI-tracked metrics from {player.fullMatches} full matches processed through our vision pipeline.
                    </div>
                </div>
            )}

            {activeTab === "medical" && (
                <div>
                    <SectionTitle icon="🏥">Medical Summary</SectionTitle>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, marginBottom: 16 }}>
                        {[
                            { label: "Injury Count", value: player.medical.injuries ?? "No data", icon: "🩹" },
                            { label: "Last Injury", value: player.medical.lastInjury, icon: "📅" },
                            { label: "Clearance", value: player.medical.clearance, icon: "✅" },
                            { label: "Fitness Score", value: player.medical.fitnessScore ?? "No data", icon: "💪" },
                        ].map((m, i) => (
                            <div key={i} style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
                                <div style={{ fontSize: 16, marginBottom: 6 }}>{m.icon}</div>
                                <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{m.value}</div>
                                <div style={{ fontSize: 10, color: COLORS.textDim, marginTop: 2 }}>{m.label}</div>
                            </div>
                        ))}
                    </div>
                    {player.medical.injuries === null && (
                        <div style={{ padding: 14, background: COLORS.dangerDim, borderRadius: 8, border: "1px solid rgba(239,68,68,0.2)", fontSize: 12, color: COLORS.danger }}>
                            ⚠ No medical records available for this player. This significantly impacts the reliability score.
                        </div>
                    )}
                    {player.medical.clearance?.includes("monitored") && (
                        <div style={{ padding: 14, background: COLORS.warningDim, borderRadius: 8, border: "1px solid rgba(245,158,11,0.2)", fontSize: 12, color: COLORS.warning }}>
                            ⚠ Player has cleared medical but is flagged for ongoing monitoring following ACL reconstruction. Full surgical records available upon player consent.
                        </div>
                    )}
                </div>
            )}

            {activeTab === "video" && (
                <div>
                    <SectionTitle icon="🎬">Match Footage & Evidence</SectionTitle>
                    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                        <div style={{ padding: "8px 14px", background: COLORS.accentDim, borderRadius: 6, fontSize: 11, color: COLORS.accent, fontWeight: 600 }}>{player.fullMatches} Full Matches</div>
                        <div style={{ padding: "8px 14px", background: COLORS.surface, borderRadius: 6, fontSize: 11, color: COLORS.textDim, fontWeight: 600 }}>{player.matchClips} Clips</div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10, marginBottom: 16 }}>
                        <VideoThumb label="vs Rayon Sports (Full)" duration="90:00" hasAI={true} onClick={() => openVideoModal("vs Rayon Sports (Full)", "90:00", true)} />
                        <VideoThumb label="vs Police FC (Full)" duration="87:23" hasAI={true} onClick={() => openVideoModal("vs Police FC (Full)", "87:23", true)} />
                        <VideoThumb label="Training Session #14" duration="22:45" hasAI={false} onClick={() => openVideoModal("Training Session #14", "22:45", false)} />
                        <VideoThumb label="vs Mukura (Highlights)" duration="4:30" hasAI={true} onClick={() => openVideoModal("vs Mukura (Highlights)", "4:30", true)} />
                        {player.matchClips > 4 && (
                            <div
                                onClick={() => alert(`Viewing all ${player.matchClips} clips — feature coming soon!`)}
                                style={{ display: "flex", alignItems: "center", justifyContent: "center", background: COLORS.surface, borderRadius: 8, border: `1px dashed ${COLORS.border}`, minHeight: 110, cursor: "pointer", transition: "all 0.2s" }}
                                onMouseEnter={e => { e.currentTarget.style.borderColor = COLORS.accent; }}
                                onMouseLeave={e => { e.currentTarget.style.borderColor = COLORS.border; }}
                            >
                                <span style={{ fontSize: 12, color: COLORS.textDim }}>+{player.matchClips - 3} more clips</span>
                            </div>
                        )}
                    </div>
                    <div style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}`, fontSize: 12, color: COLORS.textDim, lineHeight: 1.6 }}>
                        <strong style={{ color: COLORS.accent }}>AI Vision Pipeline:</strong> Full matches are processed through YOLO + ByteTrack for persistent player tracking. Automated extraction of: minutes played, distance covered, sprint count, heat maps, and key moments. Raw unedited footage — no highlight manipulation.
                    </div>

                    {/* Video Modal */}
                    <VideoModal
                        isOpen={videoModal.isOpen}
                        onClose={() => setVideoModal(prev => ({ ...prev, isOpen: false }))}
                        videoLabel={videoModal.label}
                        duration={videoModal.duration}
                        hasAI={videoModal.hasAI}
                    />
                </div>
            )}

            {activeTab === "behavioral" && (
                <div>
                    <SectionTitle icon="👤">Professional Profile</SectionTitle>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, marginBottom: 16 }}>
                        {[
                            { label: "Training Attendance", value: player.behavioral.training ? player.behavioral.training + "%" : "No data", icon: "📊" },
                            { label: "Discipline Record", value: player.behavioral.discipline ?? "No data", icon: "⚖️" },
                            { label: "Languages", value: player.behavioral.languages?.join(", ") ?? "Unknown", icon: "🗣" },
                            { label: "Leadership", value: player.behavioral.leadership ?? "No data", icon: "🏅" },
                        ].map((b, i) => (
                            <div key={i} style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                                    <span>{b.icon}</span>
                                    <span style={{ fontSize: 10, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.5 }}>{b.label}</span>
                                </div>
                                <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{b.value}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {activeTab === "contract" && (
                <div>
                    <SectionTitle icon="📝">Contract & Legal</SectionTitle>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
                        {[
                            { label: "Contract Status", value: player.contract.status },
                            { label: "Expiry", value: player.contract.expiry },
                            { label: "Training Compensation", value: player.contract.compensation },
                            { label: "FIFA TMS", value: player.contract.tms },
                        ].map((c, i) => (
                            <div key={i} style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
                                <div style={{ fontSize: 10, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>{c.label}</div>
                                <div style={{ fontSize: 14, fontWeight: 600, color: c.value === "Disputed" || c.value === "Not registered" || c.value === "Unknown" ? COLORS.warning : COLORS.text }}>{c.value}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
