import { useState, useEffect, useRef } from "react";

const COLORS = {
  bg: "#0a0e17",
  surface: "#111827",
  surfaceHover: "#1a2234",
  card: "#151d2e",
  border: "#1e2a3a",
  accent: "#00d4aa",
  accentDim: "rgba(0,212,170,0.12)",
  accentGlow: "rgba(0,212,170,0.3)",
  warning: "#f59e0b",
  warningDim: "rgba(245,158,11,0.12)",
  danger: "#ef4444",
  dangerDim: "rgba(239,68,68,0.12)",
  text: "#e2e8f0",
  textDim: "#7a8ba3",
  textMuted: "#4a5568",
  gold: "#fbbf24",
  blue: "#3b82f6",
  purple: "#8b5cf6",
};

const players = [
  {
    id: 1, name: "Jean-Baptiste Mugisha", age: 22, nation: "Rwanda", flag: "🇷🇼",
    club: "APR FC", league: "Rwanda Premier League", position: "CM",
    photo: null, verificationStatus: "verified",
    reliabilityScore: 87, dataConfidence: 92,
    stats: { appearances: 68, goals: 12, assists: 19, minutes: 5840, cards: { yellow: 6, red: 0 } },
    career: [
      { club: "APR FC", period: "2023–Present", level: "1st Division", apps: 68 },
      { club: "Rayon Sports Academy", period: "2020–2023", level: "Academy", apps: 45 },
    ],
    medical: { injuries: 1, lastInjury: "Minor hamstring strain", clearance: "Full", fitnessScore: 91 },
    behavioral: { training: 96, discipline: "Excellent", languages: ["Kinyarwanda", "French", "English"], leadership: "Emerging captain" },
    contract: { status: "Active", expiry: "June 2027", compensation: "Eligible", tms: "Registered" },
    matchClips: 14, fullMatches: 6,
    scoutNotes: "Exceptional work rate, intelligent off-ball movement. Strong in tight spaces. Ready for European 2nd tier.",
  },
  {
    id: 2, name: "Thabo Molefe", age: 20, nation: "South Africa", flag: "🇿🇦",
    club: "Orlando Pirates", league: "PSL", position: "LW",
    photo: null, verificationStatus: "verified",
    reliabilityScore: 91, dataConfidence: 95,
    stats: { appearances: 42, goals: 15, assists: 8, minutes: 3200, cards: { yellow: 3, red: 0 } },
    career: [
      { club: "Orlando Pirates", period: "2024–Present", level: "1st Division", apps: 42 },
      { club: "Pirates Academy", period: "2021–2024", level: "Academy", apps: 60 },
    ],
    medical: { injuries: 0, lastInjury: "None", clearance: "Full", fitnessScore: 95 },
    behavioral: { training: 98, discipline: "Excellent", languages: ["English", "Zulu", "Sotho"], leadership: "Vocal in training" },
    contract: { status: "Active", expiry: "Dec 2026", compensation: "Eligible", tms: "Registered" },
    matchClips: 22, fullMatches: 10,
    scoutNotes: "Electric pace, direct runner. Decision-making improving. High ceiling. MLS or Championship level.",
  },
  {
    id: 3, name: "Emmanuel Habimana", age: 24, nation: "Rwanda", flag: "🇷🇼",
    club: "Kiyovu Sports", league: "Rwanda Premier League", position: "CB",
    photo: null, verificationStatus: "partial",
    reliabilityScore: 64, dataConfidence: 58,
    stats: { appearances: 55, goals: 3, assists: 2, minutes: 4700, cards: { yellow: 11, red: 1 } },
    career: [
      { club: "Kiyovu Sports", period: "2022–Present", level: "1st Division", apps: 55 },
      { club: "Musanze FC", period: "2020–2022", level: "2nd Division", apps: 38 },
      { club: "Unknown Academy", period: "2018–2020", level: "Academy", apps: null },
    ],
    medical: { injuries: 3, lastInjury: "ACL reconstruction (2023)", clearance: "Full - monitored", fitnessScore: 78 },
    behavioral: { training: 82, discipline: "Good", languages: ["Kinyarwanda", "French"], leadership: "N/A" },
    contract: { status: "Active", expiry: "June 2026", compensation: "Disputed", tms: "Pending" },
    matchClips: 5, fullMatches: 2,
    scoutNotes: "Strong aerial presence, good reading of the game. ACL recovery looks good but needs monitoring. Career gap 2018-2020 unverified.",
  },
  {
    id: 4, name: "Sipho Ndlovu", age: 19, nation: "South Africa", flag: "🇿🇦",
    club: "Stellenbosch FC", league: "PSL", position: "ST",
    photo: null, verificationStatus: "verified",
    reliabilityScore: 78, dataConfidence: 85,
    stats: { appearances: 28, goals: 11, assists: 3, minutes: 1900, cards: { yellow: 2, red: 0 } },
    career: [
      { club: "Stellenbosch FC", period: "2025–Present", level: "1st Division", apps: 28 },
      { club: "Stellenbosch Academy", period: "2022–2025", level: "Academy", apps: 52 },
    ],
    medical: { injuries: 0, lastInjury: "None", clearance: "Full", fitnessScore: 93 },
    behavioral: { training: 90, discipline: "Very Good", languages: ["English", "Afrikaans", "Xhosa"], leadership: "Quiet but focused" },
    contract: { status: "Active", expiry: "June 2028", compensation: "Eligible", tms: "Registered" },
    matchClips: 18, fullMatches: 8,
    scoutNotes: "Natural finisher, good movement in the box. Strong for his age. NCAA D1 programs already inquiring. Could go Europe or USA.",
  },
  {
    id: 5, name: "Patrick Irakoze", age: 21, nation: "Burundi", flag: "🇧🇮",
    club: "AS Kigali", league: "Rwanda Premier League", position: "RB",
    photo: null, verificationStatus: "unverified",
    reliabilityScore: 38, dataConfidence: 29,
    stats: { appearances: 30, goals: 1, assists: 7, minutes: 2400, cards: { yellow: 8, red: 2 } },
    career: [
      { club: "AS Kigali", period: "2024–Present", level: "1st Division", apps: 30 },
      { club: "Unknown (Burundi)", period: "2021–2024", level: "Unknown", apps: null },
    ],
    medical: { injuries: null, lastInjury: "No records", clearance: "Unknown", fitnessScore: null },
    behavioral: { training: null, discipline: "Unknown", languages: ["Kirundi", "French"], leadership: "N/A" },
    contract: { status: "Active", expiry: "Dec 2025", compensation: "Unknown", tms: "Not registered" },
    matchClips: 2, fullMatches: 0,
    scoutNotes: "Athletically gifted, aggressive in duels. Significant data gaps — Burundi career unverified. High ceiling but high risk profile.",
  },
];

const leagueIntel = [
  { name: "Rwanda Premier League", country: "🇷🇼", strength: 3.2, reliability: 78, clubs: 16, risk: "Low" },
  { name: "South Africa PSL", country: "🇿🇦", strength: 5.8, reliability: 91, clubs: 16, risk: "Low" },
  { name: "Burundi Primus League", country: "🇧🇮", strength: 1.8, reliability: 34, clubs: 16, risk: "Medium" },
];

const VerificationBadge = ({ status }) => {
  const config = {
    verified: { label: "Verified", color: COLORS.accent, bg: COLORS.accentDim, icon: "✓" },
    partial: { label: "Partially Verified", color: COLORS.warning, bg: COLORS.warningDim, icon: "⚠" },
    unverified: { label: "Unverified", color: COLORS.danger, bg: COLORS.dangerDim, icon: "✕" },
  };
  const c = config[status];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600, color: c.color, background: c.bg, letterSpacing: 0.5, textTransform: "uppercase" }}>
      <span style={{ fontSize: 10 }}>{c.icon}</span> {c.label}
    </span>
  );
};

const ScoreRing = ({ score, size = 56, label, color }) => {
  const radius = (size - 8) / 2;
  const circ = 2 * Math.PI * radius;
  const offset = score != null ? circ - (score / 100) * circ : circ;
  const c = color || (score >= 75 ? COLORS.accent : score >= 50 ? COLORS.warning : score != null ? COLORS.danger : COLORS.textMuted);
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={COLORS.border} strokeWidth={3} />
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={c} strokeWidth={3}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 1s ease" }} />
      </svg>
      <div style={{ position: "relative", marginTop: -size + 4, height: size - 4, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: size * 0.32, fontWeight: 700, color: c, fontFamily: "'JetBrains Mono', monospace" }}>
          {score != null ? score : "—"}
        </span>
      </div>
      {label && <span style={{ fontSize: 9, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 1, fontWeight: 600, marginTop: 2 }}>{label}</span>}
    </div>
  );
};

const StatBlock = ({ label, value, sub }) => (
  <div style={{ textAlign: "center", padding: "10px 6px" }}>
    <div style={{ fontSize: 22, fontWeight: 700, color: COLORS.text, fontFamily: "'JetBrains Mono', monospace" }}>{value ?? "—"}</div>
    <div style={{ fontSize: 10, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 0.8, marginTop: 2 }}>{label}</div>
    {sub && <div style={{ fontSize: 9, color: COLORS.textMuted, marginTop: 2 }}>{sub}</div>}
  </div>
);

const Tab = ({ label, active, onClick, count }) => (
  <button onClick={onClick} style={{
    padding: "8px 16px", border: "none", cursor: "pointer", fontSize: 12, fontWeight: 600,
    color: active ? COLORS.accent : COLORS.textDim,
    background: active ? COLORS.accentDim : "transparent",
    borderRadius: 6, display: "flex", alignItems: "center", gap: 6,
    transition: "all 0.2s",
    letterSpacing: 0.3,
  }}>
    {label}
    {count != null && <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 10, background: active ? COLORS.accent : COLORS.textMuted, color: active ? COLORS.bg : COLORS.text }}>{count}</span>}
  </button>
);

const SectionTitle = ({ children, icon }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
    {icon && <span style={{ fontSize: 14 }}>{icon}</span>}
    <span style={{ fontSize: 11, fontWeight: 700, color: COLORS.textDim, textTransform: "uppercase", letterSpacing: 1.5 }}>{children}</span>
    <div style={{ flex: 1, height: 1, background: COLORS.border }} />
  </div>
);

const VideoThumb = ({ label, duration, hasAI }) => (
  <div style={{ background: COLORS.surface, borderRadius: 8, overflow: "hidden", cursor: "pointer", border: `1px solid ${COLORS.border}`, transition: "all 0.2s" }}>
    <div style={{ height: 80, background: `linear-gradient(135deg, ${COLORS.surfaceHover}, ${COLORS.bg})`, display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
      <div style={{ width: 32, height: 32, borderRadius: "50%", background: "rgba(255,255,255,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
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

const PlayerProfile = ({ player, onBack }) => {
  const [activeTab, setActiveTab] = useState("overview");

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
            <button style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: COLORS.accent, color: COLORS.bg, fontSize: 11, fontWeight: 700, cursor: "pointer", letterSpacing: 0.3 }}>+ Add to Shortlist</button>
            <button style={{ padding: "6px 14px", borderRadius: 6, border: `1px solid ${COLORS.border}`, background: "transparent", color: COLORS.textDim, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>Request Full Report</button>
            <button style={{ padding: "6px 14px", borderRadius: 6, border: `1px solid ${COLORS.border}`, background: "transparent", color: COLORS.textDim, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>Compare</button>
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
            <StatBlock label="Apps" value={player.stats.appearances} />
            <StatBlock label="Goals" value={player.stats.goals} />
            <StatBlock label="Assists" value={player.stats.assists} />
            <StatBlock label="Minutes" value={player.stats.minutes?.toLocaleString()} />
            <StatBlock label="Yellows" value={player.stats.cards.yellow} />
            <StatBlock label="Reds" value={player.stats.cards.red} />
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
                  <div style={{ width: "100%", height: v * 0.6, background: `linear-gradient(to top, ${COLORS.accent}, ${COLORS.accentDim})`, borderRadius: "3px 3px 0 0", transition: "height 0.5s ease", transitionDelay: `${i * 50}ms` }} />
                  <span style={{ fontSize: 8, color: COLORS.textMuted }}>{["A","S","O","N","D","J","F","M","A","M"][i]}</span>
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
            <VideoThumb label="vs Rayon Sports (Full)" duration="90:00" hasAI={true} />
            <VideoThumb label="vs Police FC (Full)" duration="87:23" hasAI={true} />
            <VideoThumb label="Training Session #14" duration="22:45" hasAI={false} />
            <VideoThumb label="vs Mukura (Highlights)" duration="4:30" hasAI={true} />
            {player.matchClips > 4 && <div style={{ display: "flex", alignItems: "center", justifyContent: "center", background: COLORS.surface, borderRadius: 8, border: `1px dashed ${COLORS.border}`, minHeight: 110, cursor: "pointer" }}>
              <span style={{ fontSize: 12, color: COLORS.textDim }}>+{player.matchClips - 3} more clips</span>
            </div>}
          </div>
          <div style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}`, fontSize: 12, color: COLORS.textDim, lineHeight: 1.6 }}>
            <strong style={{ color: COLORS.accent }}>AI Vision Pipeline:</strong> Full matches are processed through YOLO + ByteTrack for persistent player tracking. Automated extraction of: minutes played, distance covered, sprint count, heat maps, and key moments. Raw unedited footage — no highlight manipulation.
          </div>
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

const PlayerRow = ({ player, onClick }) => (
  <div onClick={onClick} style={{
    display: "flex", alignItems: "center", gap: 12, padding: "12px 16px",
    background: COLORS.card, borderRadius: 10, cursor: "pointer",
    border: `1px solid ${COLORS.border}`, transition: "all 0.15s",
    marginBottom: 6,
  }}
    onMouseEnter={e => { e.currentTarget.style.borderColor = COLORS.accent; e.currentTarget.style.background = COLORS.surfaceHover; }}
    onMouseLeave={e => { e.currentTarget.style.borderColor = COLORS.border; e.currentTarget.style.background = COLORS.card; }}>
    <div style={{ width: 40, height: 40, borderRadius: 8, background: COLORS.accentDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0 }}>
      {player.flag}
    </div>
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{player.name}</span>
        <VerificationBadge status={player.verificationStatus} />
      </div>
      <div style={{ fontSize: 11, color: COLORS.textDim, marginTop: 2 }}>{player.age} · {player.position} · {player.club}</div>
    </div>
    <div style={{ display: "flex", gap: 12, alignItems: "center", flexShrink: 0 }}>
      <ScoreRing score={player.reliabilityScore} size={40} />
      <div style={{ fontSize: 11, color: COLORS.textDim, width: 50, textAlign: "center" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: COLORS.text }}>{player.stats.appearances}</div>
        <div style={{ fontSize: 9 }}>Apps</div>
      </div>
      <div style={{ fontSize: 11, color: COLORS.textDim, width: 40, textAlign: "center" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: COLORS.text }}>{player.stats.goals}</div>
        <div style={{ fontSize: 9 }}>Goals</div>
      </div>
    </div>
  </div>
);

export default function App() {
  const [view, setView] = useState("dashboard");
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterNation, setFilterNation] = useState("All");
  const [sidebarSection, setSidebarSection] = useState("players");
  const [shortlist, setShortlist] = useState([1, 2, 4]);

  const filteredPlayers = players.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.club.toLowerCase().includes(searchQuery.toLowerCase());
    const matchNation = filterNation === "All" || p.nation === filterNation;
    return matchSearch && matchNation;
  });

  const nations = ["All", ...new Set(players.map(p => p.nation))];

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: COLORS.bg, color: COLORS.text, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet" />

      {/* Top Bar */}
      <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", borderBottom: `1px solid ${COLORS.border}`, background: COLORS.surface, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: `linear-gradient(135deg, ${COLORS.accent}, #0891b2)`, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 14, color: COLORS.bg }}>SB</div>
          <div>
            <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: -0.3, color: COLORS.text }}>ScoutBase</span>
            <span style={{ fontSize: 9, marginLeft: 6, padding: "2px 6px", borderRadius: 4, background: COLORS.accentDim, color: COLORS.accent, fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>Africa</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <div style={{ padding: "6px 12px", background: COLORS.bg, borderRadius: 6, fontSize: 11, color: COLORS.textDim, border: `1px solid ${COLORS.border}` }}>
            🔍 Search players, clubs, leagues...
          </div>
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: COLORS.accentDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, color: COLORS.accent, fontWeight: 700, cursor: "pointer" }}>ST</div>
        </div>
      </header>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <nav style={{ width: 200, borderRight: `1px solid ${COLORS.border}`, padding: "16px 10px", display: "flex", flexDirection: "column", gap: 4, background: COLORS.surface, flexShrink: 0 }}>
          {[
            { key: "players", label: "Player Database", icon: "👤" },
            { key: "shortlist", label: "My Shortlist", icon: "⭐", count: shortlist.length },
            { key: "leagues", label: "League Intel", icon: "🌍" },
            { key: "tracking", label: "AI Tracking", icon: "🎯" },
            { key: "reports", label: "Reports", icon: "📊" },
          ].map(item => (
            <button key={item.key} onClick={() => { setSidebarSection(item.key); setSelectedPlayer(null); setView("dashboard"); }}
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 12px",
                background: sidebarSection === item.key ? COLORS.accentDim : "transparent",
                color: sidebarSection === item.key ? COLORS.accent : COLORS.textDim,
                border: "none", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 500,
                width: "100%", textAlign: "left",
              }}>
              <span>{item.icon}</span> {item.label}
              {item.count && <span style={{ marginLeft: "auto", fontSize: 10, padding: "1px 6px", borderRadius: 8, background: COLORS.accent, color: COLORS.bg }}>{item.count}</span>}
            </button>
          ))}

          <div style={{ marginTop: "auto", padding: "12px 8px", borderTop: `1px solid ${COLORS.border}` }}>
            <div style={{ fontSize: 10, color: COLORS.textMuted, marginBottom: 4 }}>DEMO ACCOUNT</div>
            <div style={{ fontSize: 11, color: COLORS.textDim }}>Sloe Labs</div>
            <div style={{ fontSize: 9, color: COLORS.textMuted }}>Pro Plan · 5 users</div>
          </div>
        </nav>

        {/* Main Content */}
        <main style={{ flex: 1, padding: 20, overflowY: "auto", maxHeight: "calc(100vh - 57px)" }}>
          {selectedPlayer ? (
            <PlayerProfile player={selectedPlayer} onBack={() => setSelectedPlayer(null)} />
          ) : sidebarSection === "players" ? (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
                <div>
                  <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>Player Intelligence</h1>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: COLORS.textDim }}>{filteredPlayers.length} players · Rwanda & South Africa</p>
                </div>
                <div style={{ display: "flex", gap: 6 }}>
                  <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search name or club..."
                    style={{ padding: "7px 12px", borderRadius: 6, border: `1px solid ${COLORS.border}`, background: COLORS.surface, color: COLORS.text, fontSize: 12, outline: "none", width: 180 }} />
                  <select value={filterNation} onChange={e => setFilterNation(e.target.value)}
                    style={{ padding: "7px 10px", borderRadius: 6, border: `1px solid ${COLORS.border}`, background: COLORS.surface, color: COLORS.text, fontSize: 12, outline: "none" }}>
                    {nations.map(n => <option key={n} value={n}>{n === "All" ? "All Nations" : n}</option>)}
                  </select>
                </div>
              </div>

              {filteredPlayers.map(p => (
                <PlayerRow key={p.id} player={p} onClick={() => setSelectedPlayer(p)} />
              ))}
            </div>
          ) : sidebarSection === "shortlist" ? (
            <div>
              <h1 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>My Shortlist</h1>
              <p style={{ margin: "0 0 16px", fontSize: 12, color: COLORS.textDim }}>{shortlist.length} players saved</p>
              {players.filter(p => shortlist.includes(p.id)).map(p => (
                <PlayerRow key={p.id} player={p} onClick={() => setSelectedPlayer(p)} />
              ))}
            </div>
          ) : sidebarSection === "leagues" ? (
            <div>
              <h1 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>League Intelligence</h1>
              <p style={{ margin: "0 0 16px", fontSize: 12, color: COLORS.textDim }}>Contextual data for African leagues</p>
              {leagueIntel.map((l, i) => (
                <div key={i} style={{ padding: 16, background: COLORS.card, borderRadius: 10, border: `1px solid ${COLORS.border}`, marginBottom: 8 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <div>
                      <span style={{ fontSize: 16, marginRight: 8 }}>{l.country}</span>
                      <span style={{ fontSize: 15, fontWeight: 600 }}>{l.name}</span>
                    </div>
                    <span style={{ fontSize: 11, padding: "3px 10px", borderRadius: 20, fontWeight: 600,
                      background: l.risk === "Low" ? COLORS.accentDim : COLORS.warningDim,
                      color: l.risk === "Low" ? COLORS.accent : COLORS.warning
                    }}>{l.risk} Risk</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.accent, fontFamily: "'JetBrains Mono', monospace" }}>{l.strength}/10</div>
                      <div style={{ fontSize: 10, color: COLORS.textDim }}>League Strength</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.blue, fontFamily: "'JetBrains Mono', monospace" }}>{l.reliability}%</div>
                      <div style={{ fontSize: 10, color: COLORS.textDim }}>Data Reliability</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.text, fontFamily: "'JetBrains Mono', monospace" }}>{l.clubs}</div>
                      <div style={{ fontSize: 10, color: COLORS.textDim }}>Active Clubs</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : sidebarSection === "tracking" ? (
            <div>
              <h1 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>AI Vision Tracking</h1>
              <p style={{ margin: "0 0 16px", fontSize: 12, color: COLORS.textDim }}>Automated match analysis powered by computer vision</p>
              <div style={{ padding: 24, background: COLORS.card, borderRadius: 12, border: `1px solid ${COLORS.border}`, marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 10, background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.blue})`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22 }}>🎯</div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>Vision Pipeline</div>
                    <div style={{ fontSize: 12, color: COLORS.textDim }}>YOLO Detection + ByteTrack Persistence + LLM Analysis</div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                  {[
                    { step: "01", title: "Upload Match Footage", desc: "Raw camera footage from any device — phone, broadcast, fixed cam" },
                    { step: "02", title: "Player Detection", desc: "YOLO identifies every player, referee, and ball in each frame" },
                    { step: "03", title: "Persistent Tracking", desc: "ByteTrack assigns IDs — Player #7 stays Player #7 for 90 minutes" },
                    { step: "04", title: "AI Match Report", desc: "LLM generates minutes, sprints, positions, key moments per player" },
                  ].map((s, i) => (
                    <div key={i} style={{ padding: 14, background: COLORS.surface, borderRadius: 8, border: `1px solid ${COLORS.border}` }}>
                      <div style={{ fontSize: 20, fontWeight: 800, color: COLORS.accentDim, fontFamily: "'JetBrains Mono', monospace", marginBottom: 6 }}>{s.step}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text, marginBottom: 4 }}>{s.title}</div>
                      <div style={{ fontSize: 11, color: COLORS.textDim, lineHeight: 1.5 }}>{s.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8 }}>
                {[
                  { label: "Matches Processed", value: "24", icon: "🎬" },
                  { label: "Players Tracked", value: "312", icon: "👤" },
                  { label: "Auto Reports", value: "18", icon: "📊" },
                  { label: "Avg Processing", value: "4.2 min", icon: "⚡" },
                ].map((m, i) => (
                  <div key={i} style={{ padding: 14, background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}`, textAlign: "center" }}>
                    <div style={{ fontSize: 20, marginBottom: 4 }}>{m.icon}</div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: COLORS.accent, fontFamily: "'JetBrains Mono', monospace" }}>{m.value}</div>
                    <div style={{ fontSize: 10, color: COLORS.textDim }}>{m.label}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : sidebarSection === "reports" ? (
            <div>
              <h1 style={{ margin: "0 0 4px", fontSize: 20, fontWeight: 700, fontFamily: "'Playfair Display', serif" }}>Reports</h1>
              <p style={{ margin: "0 0 16px", fontSize: 12, color: COLORS.textDim }}>Generated intelligence reports</p>
              {[
                { title: "Player Comparison: Mugisha vs Ndlovu", type: "Comparison", date: "Feb 3, 2026", status: "Ready" },
                { title: "Rwanda Premier League Q4 Report", type: "League Intel", date: "Jan 28, 2026", status: "Ready" },
                { title: "Molefe — Full Scouting Report", type: "Player Report", date: "Jan 15, 2026", status: "Ready" },
              ].map((r, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: COLORS.card, borderRadius: 8, border: `1px solid ${COLORS.border}`, marginBottom: 6, cursor: "pointer" }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text }}>{r.title}</div>
                    <div style={{ fontSize: 11, color: COLORS.textDim }}>{r.type} · {r.date}</div>
                  </div>
                  <span style={{ fontSize: 10, padding: "3px 10px", borderRadius: 20, background: COLORS.accentDim, color: COLORS.accent, fontWeight: 600 }}>{r.status}</span>
                </div>
              ))}
            </div>
          ) : null}
        </main>
      </div>
    </div>
  );
}
