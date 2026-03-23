"use client";

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { COLORS } from '@/lib/constants';
import { Player, LeagueIntel } from '@/lib/types';
import { Sidebar } from '@/components/Sidebar';
import { PlayerRow } from '@/components/PlayerRow';
import { PlayerProfile } from '@/components/PlayerProfile';
import { VideoUpload } from '@/components/VideoUpload';
import { ComparisonView } from '@/components/ComparisonView';
import { SAM3Panel } from '@/components/SAM3Panel';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import {
  getPlayers,
  getLeagues,
  getShortlist,
  addToShortlist,
  removeFromShortlist,
  API_BASE,
} from '@/lib/api';

export default function Home() {
  // Data state - fetched from API
  const [players, setPlayers] = useState<Player[]>([]);
  const [leagueIntel, setLeagueIntel] = useState<LeagueIntel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterNation, setFilterNation] = useState("All");
  const [sidebarSection, setSidebarSection] = useState("database");
  const [shortlist, setShortlist] = useState<string[]>([]);
  const [compareList, setCompareList] = useState<string[]>(() => {
    // RL4-7: Restore compareList from sessionStorage
    if (typeof window !== 'undefined') {
      try {
        const saved = sessionStorage.getItem('scoutbase_compareList');
        return saved ? JSON.parse(saved) : [];
      } catch { /* ignore parse errors */ }
    }
    return [];
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Fetch initial data on mount + periodic refresh
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [playersRes, leaguesRes, shortlistRes] = await Promise.all([
        getPlayers(),
        getLeagues(),
        getShortlist(),
      ]);
      setPlayers(playersRes.players);
      setLeagueIntel(leaguesRes.leagues);
      // Ensure backend returns string IDs. If not, map them here?
      // Since backend is updated, we assume strings.
      setShortlist(shortlistRes.shortlist.map(String));
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  // Silent refresh — updates all data without showing loading spinner (RL3-2)
  const refreshData = useCallback(async () => {
    try {
      const [playersRes, leaguesRes, shortlistRes] = await Promise.all([
        getPlayers(),
        getLeagues(),
        getShortlist(),
      ]);
      setPlayers(playersRes.players);
      setLeagueIntel(leaguesRes.leagues);
      setShortlist(shortlistRes.shortlist.map(String));
    } catch { /* silently retry next interval */ }
  }, []);

  useEffect(() => {
    fetchData();
    // Refresh ALL data every 30s to catch mutations from TrackAssignment etc (RL3-2)
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, [fetchData, refreshData]);

  // Shortlist toggle with API persistence
  const toggleShortlist = useCallback(async (playerId: string) => {
    const isInShortlist = shortlist.includes(playerId);

    // Optimistic update
    setShortlist(prev =>
      isInShortlist
        ? prev.filter(id => id !== playerId)
        : [...prev, playerId]
    );

    try {
      if (isInShortlist) {
        await removeFromShortlist(playerId);
      } else {
        await addToShortlist(playerId);
      }
    } catch (err) {
      // Revert on error
      console.error('Failed to update shortlist:', err);
      setShortlist(prev =>
        isInShortlist
          ? [...prev, playerId]
          : prev.filter(id => id !== playerId)
      );
    }
  }, [shortlist]);

  const toggleCompare = (playerId: string) => {
    setCompareList(prev => {
      const next = prev.includes(playerId)
        ? prev.filter(id => id !== playerId)
        : prev.length < 4 ? [...prev, playerId] : prev;
      // RL4-7: Persist to sessionStorage
      if (typeof window !== 'undefined') {
        try { sessionStorage.setItem('scoutbase_compareList', JSON.stringify(next)); } catch { /* ignore */ }
      }
      return next;
    });
  };

  const handleRequestReport = (player: Player) => {
    alert(`Report request submitted for ${player.name}. Full scouting reports are available on Pro plans. We'll notify you when ready.`);
  };

  const filteredPlayers = useMemo(() => {
    return players.filter(p => {
      const matchSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.club.toLowerCase().includes(searchQuery.toLowerCase());
      const matchNation = filterNation === "All" || p.nation === filterNation;
      return matchSearch && matchNation;
    });
  }, [players, searchQuery, filterNation]);

  const nations = useMemo(() => {
    return ["All", ...Array.from(new Set(players.map(p => p.nation)))];
  }, [players]);

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: COLORS.bg, color: COLORS.text, height: "100vh", display: "flex", overflow: "hidden" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet" />

      {/* Mobile Header with Hamburger Menu */}
      <div className="mobile-header" style={{
        display: 'none',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        background: COLORS.surface,
        borderBottom: `1px solid ${COLORS.border}`,
        padding: '0 16px',
        alignItems: 'center',
        gap: 12,
        zIndex: 997,
      }}>
        <button
          onClick={() => setSidebarOpen(true)}
          style={{
            background: 'none',
            border: 'none',
            color: COLORS.text,
            fontSize: 24,
            cursor: 'pointer',
            padding: 4,
          }}
        >
          ☰
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, background: COLORS.accent, borderRadius: 6, color: COLORS.bg, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 12 }}>SB</div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>ScoutBase</div>
        </div>
      </div>

      {/* Sidebar */}
      <Sidebar
        activeSection={sidebarSection}
        onSectionChange={(s) => { setSidebarSection(s); setSelectedPlayer(null); }}
        shortlistCount={shortlist.length}
        compareCount={compareList.length}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Content */}
      <main style={{ flex: 1, padding: 20, overflowY: "auto", position: 'relative' }}>
        {/* Top Bar for Search when not in profile */}
        {!selectedPlayer && sidebarSection === 'database' && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>Player Database</h1>
              <div style={{ fontSize: 13, color: COLORS.textDim }}>Centralized intelligence on East & South African talent</div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                placeholder="Search players or clubs..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, padding: "10px 16px", color: COLORS.text, fontSize: 13, width: 240, outline: "none" }}
              />
              <select value={filterNation} onChange={e => setFilterNation(e.target.value)}
                style={{ padding: "10px", borderRadius: 8, border: `1px solid ${COLORS.border}`, background: COLORS.card, color: COLORS.text, fontSize: 13, outline: "none" }}>
                {nations.map(n => <option key={n} value={n}>{n === "All" ? "All Nations" : n}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 16 }}>⏳</div>
            <div style={{ color: COLORS.textDim }}>Loading data...</div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div style={{ padding: 40 }}>
            <div style={{
              padding: 20,
              background: COLORS.dangerDim,
              borderRadius: 12,
              border: `1px solid ${COLORS.danger}`,
              color: COLORS.danger,
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Failed to load data</div>
              <div style={{ fontSize: 13, opacity: 0.8 }}>{error}</div>
              <div style={{ fontSize: 12, marginTop: 12, color: COLORS.textDim }}>
                Make sure the backend server is running at {API_BASE}
              </div>
            </div>
          </div>
        )}

        {/* Main Content - only show when not loading and no error */}
        <ErrorBoundary fallbackTitle="Failed to render content">
          {!loading && !error && selectedPlayer ? (
            <PlayerProfile
              player={selectedPlayer}
              onBack={() => setSelectedPlayer(null)}
              onCompare={(p) => toggleCompare(p.id)}
              isInCompare={compareList.includes(selectedPlayer.id)}
              onToggleShortlist={toggleShortlist}
              isInShortlist={shortlist.includes(selectedPlayer.id)}
              onRequestReport={handleRequestReport}
            />
          ) : !loading && !error && sidebarSection === "database" ? (
            <div>
              {filteredPlayers.map(p => (
                <PlayerRow
                  key={p.id}
                  player={p}
                  onClick={() => setSelectedPlayer(p)}
                  onCompare={() => toggleCompare(p.id)}
                  isInCompare={compareList.includes(p.id)}
                />
              ))}
              {filteredPlayers.length === 0 && (
                <div style={{ padding: 40, textAlign: 'center', color: COLORS.textDim }}>No players found</div>
              )}
            </div>
          ) : !loading && !error && sidebarSection === "shortlist" ? (
            <div>
              <h1 style={{ margin: "0 0 24px", fontSize: 24, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>My Shortlist</h1>
              {shortlist.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: COLORS.textDim }}>
                  No players in shortlist. Add players from the database.
                </div>
              ) : (
                players.filter(p => shortlist.includes(p.id)).map(p => (
                  <PlayerRow
                    key={p.id}
                    player={p}
                    onClick={() => setSelectedPlayer(p)}
                    onCompare={() => toggleCompare(p.id)}
                    isInCompare={compareList.includes(p.id)}
                  />
                ))
              )}
            </div>
          ) : !loading && !error && sidebarSection === "leagues" ? (
            <div>
              <h1 style={{ margin: "0 0 24px", fontSize: 24, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>League Intelligence</h1>
              {leagueIntel.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: COLORS.textDim }}>No league data available</div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
                  {leagueIntel.map((l, i) => (
                    <div key={i} style={{ background: COLORS.card, padding: 24, borderRadius: 16, border: `1px solid ${COLORS.border}` }}>
                      <div style={{ fontSize: 20, fontWeight: 700, display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                        {l.country} {l.name}
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                        <div>
                          <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.accent }}>{l.strength}/10</div>
                          <div style={{ fontSize: 10, color: COLORS.textDim }}>STRENGTH SCORE</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 24, fontWeight: 700, color: COLORS.blue }}>{l.reliability}%</div>
                          <div style={{ fontSize: 10, color: COLORS.textDim }}>DATA ACCURACY</div>
                        </div>
                      </div>
                      <div style={{ marginTop: 20, fontSize: 11, padding: "6px 12px", borderRadius: 6, background: l.risk === "Low" ? COLORS.accentDim : COLORS.warningDim, color: l.risk === "Low" ? COLORS.accent : COLORS.warning, display: "inline-block", fontWeight: 700 }}>
                        {l.risk} COMPLIANCE RISK
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : !loading && !error && sidebarSection === "upload" ? (
            <div>
              <h1 style={{ margin: "0 0 24px", fontSize: 24, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>Upload Match Video</h1>
              <VideoUpload />
            </div>
          ) : !loading && !error && sidebarSection === "sam3" ? (
            <SAM3Panel />
          ) : !loading && !error && sidebarSection === "compare" ? (
            <div>
              <h1 style={{ margin: "0 0 24px", fontSize: 24, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>Player Comparison</h1>
              <ComparisonView
                players={players.filter(p => compareList.includes(p.id))}
                onRemove={(id) => setCompareList(prev => prev.filter(pid => pid !== id))}
                onViewProfile={(player) => setSelectedPlayer(player)}
              />
            </div>
          ) : null}
        </ErrorBoundary>
      </main>

      {/* Mobile responsive styles */}
      <style>{`
        @media (max-width: 768px) {
          .mobile-header {
            display: flex !important;
          }
          main {
            padding-top: 76px !important;
          }
        }
      `}</style>
    </div>
  );
}
