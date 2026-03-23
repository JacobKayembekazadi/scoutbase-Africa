# ScoutBase Africa — User Personas & Interface Strategy

## 1. Primary Users (The "Field Force")
**Objective:** High volume data collection, low friction, mobile-first.
**Context:** Pitch-side, inconsistent internet, Android devices.

### 🟡 Persona A: The Field Scout ("Didier")
- **Role:** Independent scout or agency runner. Travels to academies/matches.
- **Pain Point:** Can't upload 4GB video files easily. Needs quick "Yes/No" on players.
- **User Story:** "As Didier, I want to send a match link or short clip and get an instant report on the #10 player so I can decide if I should stay for the second half."
- **Interface:** **WhatsApp (via Sloe OS)**
  - **Input:** Video link (YouTube/Drive) or raw file upload. Voice note: "Check the number 10, blue jersey."
  - **Output:** PDF Summary Card + highlight clip link.
  - **UI Elements:** Chat bot, simple buttons ("Analyze", "Next Player").

### 🟡 Persona B: The Academy Coach ("Coach Musa")
- **Role:** Head coach of a local academy (e.g., in Kigali).
- **Pain Point:** Has 30 kids, no time for data entry. Wants exposure for his best talent.
- **User Story:** "As Coach Musa, I want to upload my full match footage once and have the system auto-tag all my players so I can send profiles to European clubs."
- **Interface:** **Mobile Web / WhatsApp Web**
  - **Input:** Bulk upload via simple web form (drag & drop). Team roster photo (OCR).
  - **Output:** Team Performance Report (Who ran furthest? Who lost possession?).
  - **UI Elements:** "My Team" dashboard, Roster verification list.

---

## 2. Secondary Users (The "Decision Makers")
**Objective:** Deep analysis, comparison, investment decisions.
**Context:** Office/Hotel, laptop/tablet, stable wifi.

### 🔵 Persona C: The Club Analyst ("Sarah")
- **Role:** Recruitment analyst for a mid-tier European/MLS club.
- **Pain Point:** Too much video to watch. Needs filtered data (e.g., "Left-footed CBs under 21 with high interception rate").
- **User Story:** "As Sarah, I want to filter the entire African database for specific metrics and watch *only* their defensive duels."
- **Interface:** **Web Dashboard (Current React App)**
  - **Input:** Complex search queries, comparison tools.
  - **Output:** Video playlists, scatter plots, side-by-side player comparisons.
  - **UI Elements:** `SAM3Panel` (scrubbing), `ComparisonView`, Data Tables.

### 🔵 Persona D: The Agency Director ("Chief")
- **Role:** Head of scouting agency. Manages 20 field scouts (Didiers).
- **Pain Point:** managing the fleet. Who is sending good data? Who is lazy?
- **User Story:** "As Chief, I want to see a map of where my scouts are active and which regions are producing the best rated players."
- **Interface:** **Admin Dashboard (Web)**
  - **Input:** Region selection, scout assignment.
  - **Output:** Heatmap of talent, Scout Performance Leaderboard.
  - **UI Elements:** Map view, Activity Logs, Financials (if applicable).

---

## 3. Tertiary Users (The "Operators")
**Objective:** System health, model training, infrastructure cost.
**Context:** Technical command center.

### 🔴 Persona E: The Operator ("You/Sloe")
- **Role:** System Architect & Administrator.
- **Pain Point:** Server costs, GPU crashes, model hallucinations.
- **User Story:** "As Operator, I want to know immediately if the GPU server is down so I don't lose trust with clients."
- **Interface:** **Command Line / WhatsApp (Sloe OS)**
  - **Input:** `!status`, `!restart`, `!deploy`.
  - **Output:** System health alerts, cost reports.
  - **UI Elements:** Terminal, Code Editor, WhatsApp Alerts.

---

## Summary of Optimization Strategy

| User Tier | Persona | Primary Interface | Why? |
|-----------|---------|-------------------|------|
| **Primary** | The Scout | **WhatsApp** | Zero friction. They already use it. No login/password needed. |
| **Primary** | The Coach | **Mobile Web** | Needs slightly more screen space for rosters, but keeping it simple. |
| **Secondary** | The Analyst | **Desktop Web** | Deep work requires screen real estate and keyboard shortcuts. |
| **Secondary** | Agency Dir | **Desktop Web** | Management view requires tables/maps. |
| **Tertiary** | Operator | **CLI / WhatsApp** | Ops needs speed and "push" notifications. |

