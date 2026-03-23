import React from 'react';
import { Player } from '@/lib/types';
import { COLORS } from '@/lib/constants';
import { VerificationBadge, ScoreRing } from '@/components/ui/Shared';

interface ComparisonViewProps {
    players: Player[];
    onRemove: (playerId: string) => void;
    onViewProfile: (player: Player) => void;
}

const StatRow = ({ label, values, highlight = 'max' }: { label: string; values: (number | null | string)[]; highlight?: 'max' | 'min' | 'none' }) => {
    const numericValues = values.map(v => typeof v === 'number' ? v : null);
    const validNumbers = numericValues.filter((v): v is number => v !== null);
    const best = highlight === 'max' ? Math.max(...validNumbers) : highlight === 'min' ? Math.min(...validNumbers) : null;

    return (
        <div style={{ display: 'flex', borderBottom: `1px solid ${COLORS.border}` }}>
            <div style={{ width: 140, padding: '10px 12px', fontSize: 11, color: COLORS.textDim, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                {label}
            </div>
            {values.map((val, i) => {
                const isBest = highlight !== 'none' && typeof val === 'number' && val === best;
                return (
                    <div
                        key={i}
                        style={{
                            flex: 1,
                            padding: '10px 12px',
                            textAlign: 'center',
                            fontSize: 14,
                            fontWeight: isBest ? 700 : 500,
                            color: isBest ? COLORS.accent : COLORS.text,
                            fontFamily: "'JetBrains Mono', monospace",
                            background: isBest ? COLORS.accentDim : 'transparent'
                        }}
                    >
                        {val ?? '—'}
                    </div>
                );
            })}
        </div>
    );
};

export const ComparisonView = ({ players, onRemove, onViewProfile }: ComparisonViewProps) => {
    if (players.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: 60, color: COLORS.textDim }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>⚖️</div>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>No Players to Compare</div>
                <div style={{ fontSize: 13 }}>
                    Select players from the database using the "Compare" button to see a side-by-side analysis.
                </div>
            </div>
        );
    }

    return (
        <div>
            {/* Player Headers */}
            <div style={{ display: 'flex', marginBottom: 20 }}>
                <div style={{ width: 140 }} /> {/* Spacer for stat labels */}
                {players.map(player => (
                    <div key={player.id} style={{ flex: 1, textAlign: 'center', padding: '0 8px' }}>
                        <div style={{
                            background: COLORS.card,
                            borderRadius: 12,
                            padding: 16,
                            border: `1px solid ${COLORS.border}`,
                            position: 'relative'
                        }}>
                            <button
                                onClick={() => onRemove(player.id)}
                                style={{
                                    position: 'absolute',
                                    top: 8,
                                    right: 8,
                                    background: 'none',
                                    border: 'none',
                                    color: COLORS.textDim,
                                    cursor: 'pointer',
                                    fontSize: 16,
                                    padding: 4
                                }}
                                title="Remove from comparison"
                            >
                                ✕
                            </button>
                            <div style={{
                                width: 56,
                                height: 56,
                                borderRadius: 12,
                                background: `linear-gradient(135deg, ${COLORS.accentDim}, ${COLORS.surfaceHover})`,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: 24,
                                margin: '0 auto 10px'
                            }}>
                                {player.flag}
                            </div>
                            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{player.name}</div>
                            <div style={{ marginBottom: 8 }}>
                                <VerificationBadge status={player.verificationStatus} />
                            </div>
                            <div style={{ fontSize: 11, color: COLORS.textDim, marginBottom: 10 }}>
                                {player.age} yrs · {player.position} · {player.club}
                            </div>
                            <ScoreRing score={player.reliabilityScore} size={48} label="Reliability" />
                            <button
                                onClick={() => onViewProfile(player)}
                                style={{
                                    marginTop: 12,
                                    padding: '6px 12px',
                                    borderRadius: 6,
                                    border: `1px solid ${COLORS.border}`,
                                    background: 'transparent',
                                    color: COLORS.textDim,
                                    fontSize: 10,
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    width: '100%'
                                }}
                            >
                                View Full Profile
                            </button>
                        </div>
                    </div>
                ))}
                {/* Add placeholder slots */}
                {Array.from({ length: Math.max(0, 2 - players.length) }).map((_, i) => (
                    <div key={`empty-${i}`} style={{ flex: 1, textAlign: 'center', padding: '0 8px' }}>
                        <div style={{
                            background: COLORS.surface,
                            borderRadius: 12,
                            padding: 16,
                            border: `1px dashed ${COLORS.border}`,
                            minHeight: 200,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: COLORS.textMuted,
                            fontSize: 12
                        }}>
                            Add player to compare
                        </div>
                    </div>
                ))}
            </div>

            {/* Comparison Table */}
            <div style={{
                background: COLORS.card,
                borderRadius: 12,
                border: `1px solid ${COLORS.border}`,
                overflow: 'hidden'
            }}>
                <div style={{
                    padding: '12px 16px',
                    background: COLORS.surface,
                    borderBottom: `1px solid ${COLORS.border}`,
                    fontSize: 11,
                    fontWeight: 700,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1
                }}>
                    Performance Stats
                </div>
                <StatRow label="Appearances" values={players.map(p => p.stats.appearances)} />
                <StatRow label="Goals" values={players.map(p => p.stats.goals)} />
                <StatRow label="Assists" values={players.map(p => p.stats.assists)} />
                <StatRow label="Minutes" values={players.map(p => p.stats.minutes)} />
                <StatRow label="Yellow Cards" values={players.map(p => p.stats.cards.yellow)} highlight="min" />
                <StatRow label="Red Cards" values={players.map(p => p.stats.cards.red)} highlight="min" />

                <div style={{
                    padding: '12px 16px',
                    background: COLORS.surface,
                    borderBottom: `1px solid ${COLORS.border}`,
                    borderTop: `1px solid ${COLORS.border}`,
                    fontSize: 11,
                    fontWeight: 700,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    marginTop: 8
                }}>
                    Profile & Reliability
                </div>
                <StatRow label="Reliability" values={players.map(p => p.reliabilityScore)} />
                <StatRow label="Data Confidence" values={players.map(p => p.dataConfidence)} />
                <StatRow label="Fitness Score" values={players.map(p => p.medical.fitnessScore)} />
                <StatRow label="Training %" values={players.map(p => p.behavioral.training)} />
                <StatRow label="Video Clips" values={players.map(p => p.matchClips)} />
                <StatRow label="Full Matches" values={players.map(p => p.fullMatches)} />

                <div style={{
                    padding: '12px 16px',
                    background: COLORS.surface,
                    borderBottom: `1px solid ${COLORS.border}`,
                    borderTop: `1px solid ${COLORS.border}`,
                    fontSize: 11,
                    fontWeight: 700,
                    color: COLORS.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    marginTop: 8
                }}>
                    Contract
                </div>
                <StatRow label="Status" values={players.map(p => p.contract.status)} highlight="none" />
                <StatRow label="Expiry" values={players.map(p => p.contract.expiry)} highlight="none" />
                <StatRow label="TMS Status" values={players.map(p => p.contract.tms)} highlight="none" />
            </div>

            {/* Summary */}
            <div style={{
                marginTop: 20,
                padding: 16,
                background: COLORS.accentDim,
                borderRadius: 10,
                border: `1px solid rgba(0,212,170,0.2)`
            }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: COLORS.accent, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>
                    AI Comparison Summary
                </div>
                <div style={{ fontSize: 13, color: COLORS.text, lineHeight: 1.6 }}>
                    Comparing {players.length} player{players.length > 1 ? 's' : ''}.
                    {players.length >= 2 && (
                        <> The highest reliability score belongs to <strong>{players.reduce((a, b) => a.reliabilityScore > b.reliabilityScore ? a : b).name}</strong>.
                            {players.some(p => p.verificationStatus !== 'verified') && (
                                <> Note: Some players have incomplete verification — review profiles for data gaps.</>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};
