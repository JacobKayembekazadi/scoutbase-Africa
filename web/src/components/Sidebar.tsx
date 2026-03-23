import React from 'react';
import { signOut } from '@/lib/firebase';
import { useAuth } from '@/components/auth/AuthProvider';
import { COLORS } from '@/lib/constants';

interface SidebarProps {
    activeSection: string;
    onSectionChange: (section: string) => void;
    shortlistCount: number;
    compareCount?: number;
    isOpen?: boolean;
    onClose?: () => void;
}

export const Sidebar = ({ activeSection, onSectionChange, shortlistCount, compareCount = 0, isOpen = true, onClose }: SidebarProps) => {
    const { user } = useAuth();
    const items = [
        { key: "database", label: "Player Database", icon: "👤" },
        { key: "upload", label: "Upload Match", icon: "🎬" },
        { key: "sam3", label: "SAM3 Analysis", icon: "🎯" },
        { key: "shortlist", label: "My Shortlist", icon: "⭐", count: shortlistCount },
        { key: "compare", label: "Comparison", icon: "⚖️", count: compareCount },
        { key: "leagues", label: "League Intel", icon: "🌍" },
    ];

    const handleItemClick = (key: string) => {
        onSectionChange(key);
        if (onClose) onClose(); // Close sidebar on mobile after selection
    };

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && onClose && (
                <div
                    onClick={onClose}
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0,0,0,0.5)',
                        zIndex: 998,
                        display: 'none',
                    }}
                    className="sidebar-overlay"
                />
            )}
            <nav
                className="sidebar"
                style={{
                    width: 220,
                    background: COLORS.surface,
                    borderRight: `1px solid ${COLORS.border}`,
                    padding: "20px 10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    flexShrink: 0,
                    height: '100vh',
                    position: 'relative',
                    zIndex: 999,
                    transition: 'transform 0.3s ease',
                }}
            >
                <div style={{ padding: "0 10px 20px", display: "flex", alignItems: "center", gap: 10, justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ width: 32, height: 32, background: COLORS.accent, borderRadius: 8, color: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800 }}>SB</div>
                        <div style={{ fontWeight: 700, fontSize: 16 }}>ScoutBase</div>
                    </div>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="close-sidebar-btn"
                            style={{
                                background: 'none',
                                border: 'none',
                                color: COLORS.textDim,
                                fontSize: 20,
                                cursor: 'pointer',
                                padding: 4,
                                display: 'none', // Hidden by default, shown on mobile via CSS
                            }}
                        >
                            ✕
                        </button>
                    )}
                </div>

                {items.map(item => (
                    <button
                        key={item.key}
                        onClick={() => handleItemClick(item.key)}
                        style={{
                            display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", border: "none", borderRadius: 8, cursor: "pointer", fontSize: 13, fontWeight: 500,
                            background: activeSection === item.key ? COLORS.accentDim : "transparent",
                            color: activeSection === item.key ? COLORS.accent : COLORS.textDim,
                            textAlign: "left",
                            width: '100%'
                        }}
                    >
                        <span>{item.icon}</span> {item.label}
                        {item.count !== undefined && item.count > 0 && (
                            <span style={{ marginLeft: "auto", fontSize: 10, background: COLORS.accent, color: COLORS.bg, padding: "1px 6px", borderRadius: 10, fontWeight: 700 }}>{item.count}</span>
                        )}
                    </button>
                ))}

                <div style={{ marginTop: "auto", padding: "12px 0", borderTop: `1px solid ${COLORS.border}`, display: "flex", flexDirection: "column", gap: 2 }}>
                    <div style={{ padding: "0 8px" }}>
                        <div style={{ fontSize: 10, color: COLORS.textMuted, marginBottom: 2 }}>SIGNED IN AS</div>
                        <div style={{ fontSize: 11, color: COLORS.textDim, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user?.displayName || user?.email || 'User'}</div>
                    </div>
                    <button
                        onClick={() => signOut()}
                        style={{
                            marginTop: 8,
                            width: "100%",
                            padding: "6px 8px",
                            background: "transparent",
                            border: `1px solid ${COLORS.border}`,
                            borderRadius: 6,
                            color: COLORS.danger,
                            fontSize: 11,
                            fontWeight: 600,
                            cursor: "pointer",
                            textAlign: "left",
                            display: "flex", alignItems: "center", gap: 6
                        }}
                    >
                        <span>🚪</span> Sign Out
                    </button>
                </div>
            </nav>

            {/* Mobile responsive styles */}
            <style>{`
                @media (max-width: 768px) {
                    .sidebar {
                        position: fixed !important;
                        top: 0;
                        left: 0;
                        transform: ${isOpen ? 'translateX(0)' : 'translateX(-100%)'};
                    }
                    .sidebar-overlay {
                        display: ${isOpen ? 'block' : 'none'} !important;
                    }
                    .close-sidebar-btn {
                        display: block !important;
                    }
                }
            `}</style>
        </>
    );
};
