# SCOUTBASE AFRICA — PROJECT CONTEXT

> Paste this document into any LLM context window, system prompt, or project knowledge base to give the AI full understanding of this project. Last updated: February 2026.

---

## ⚠️ MANDATORY PROTOCOL FOR ALL AI AGENTS ⚠️

> **THIS SECTION IS NON-NEGOTIABLE. EVERY AI AGENT MUST COMPLY.**

### Before Starting Work:
1. **READ `CURRENT_STATE.md`** to understand what's been done
2. **CHECK "Known Issues"** to avoid duplicate work
3. **CHECK "What's In Progress"** to see active tasks
4. **FOLLOW BMAD methodology** in `docs/BMAD.md`

### After EVERY Session (NO EXCEPTIONS):
1. **UPDATE `CURRENT_STATE.md`** with:
   - New "Last Updated" date
   - Your model name in "Updated By"
   - Entry in "Recent Changes" section
   - Any status changes to components
   - Any new issues discovered
   - Any technical debt added/resolved

### Update Format Required:
```markdown
### YYYY-MM-DD - [Brief Description]
**By**: [Your Model Name]

**Added**: [list items]
**Modified**: [list items]
**Removed**: [list items]
**Files Changed**: [count]
```

### Why This Is Mandatory:
- **Prevents duplicate work** across sessions
- **Maintains continuity** between different AI agents
- **Tracks decisions** for future reference
- **Documents technical debt** before it's forgotten
- **Enables efficient handoffs** between sessions

### Failure to Update:
If you complete work without updating `CURRENT_STATE.md`, you are:
- Creating confusion for the next agent
- Potentially causing duplicate work
- Violating project protocol
- Reducing project quality

**UPDATE THE FILE. EVERY. SINGLE. TIME.**

---

## WHAT IS SCOUTBASE

ScoutBase Africa is a **Player Intelligence & Risk Assessment Platform** for football (soccer) recruitment in emerging markets, primarily Africa. It uses computer vision (YOLO object detection + ByteTrack multi-object tracking) to automatically extract verified player performance data from raw match footage, replacing the unreliable highlight reels, scattered WhatsApp PDFs, and agent-curated narratives that currently dominate African football recruitment.

ScoutBase is NOT a database. It is data infrastructure for the globalization of African football — built on verifiable evidence, powered by computer vision, designed to turn uncertainty into confidence.

**One-liner:** "We point a camera at an African league match and automatically generate the same quality of player data that European leagues produce with million-dollar stadium systems."

---

## THE PROBLEM

African football recruitment is broken by a systemic trust deficit:

- No verified identity or age confirmation (age fraud is common)
- Highlight reels are selectively edited and misleading
- No centralized playing-time or career history records
- Medical records are absent, scattered, or fabricated
- Contract ownership is often disputed
- Player history lives across WhatsApp messages and PDFs
- Foreign scouts cannot assess African league competition levels
- Due diligence on an African prospect takes 3-6 months vs 2-4 weeks for Europeans
- Fewer than 10% of African league matches have structured statistical coverage
- Result: clubs pass on talented players because "unknown risk" outweighs potential reward

The global football transfer market is $8B+ annually. African players are an increasing share, but the data gap means talent is systematically undervalued.

---

## FIRST PRINCIPLES

Every design decision flows from these:

1. **Trust is the product.** Every feature must measurably reduce signing risk or increase data confidence. If it doesn't, it doesn't belong.
2. **The camera is the data entry system.** Any camera that can record a match is a data collection device. A smartphone on a tripod at a Rwandan league match produces usable raw material. No dependency on league infrastructure.
3. **Two scores, not one.** Reliability Score (player quality) and Data Confidence Score (how much we know) are independent. A talented player from a poorly documented league shouldn't be penalized for infrastructure failures.
4. **Raw evidence over edited narratives.** Unedited match footage with AI annotations, not manipulated highlights. Scouts see full context.
5. **Consent is non-negotiable.** Players control access to sensitive data. Medical records require explicit authorization. Behavioral profiles are framed as professional portfolios, not surveillance.
6. **Infrastructure before features.** Build the data layer right first. Comparison tools and social features are trivial once the underlying data is reliable.

---

## SEVEN-LAYER DATA ARCHITECTURE

Every player profile is composed of seven independently verifiable layers:

### Layer A: Identity & Verification
Legal name, DOB (verified vs claimed), nationality, national ID (hashed), biometric confirmation, agent licensing status. Verification badges: ✅ Verified | ⚠️ Partial | ❌ Unverified. Each field has a data source tag.

### Layer B: Career & Playing History
Structured timeline: clubs (youth + senior), league levels, appearances, minutes, positions, loan spells. Career gaps are explicitly flagged. Every entry is time-stamped and source-attributed (club, league, federation, scout, or self-reported).

### Layer C: Performance & Match Data (AI-Generated)
This is where the vision pipeline delivers value. From processed match footage:
- Minutes played (from frame-level tracking)
- Position/zone presence (heat maps from pixel coordinates)
- Sprint count and movement intensity
- Speed estimates (pixel displacement between frames)
- Match involvement patterns
- Starts vs substitute appearances

### Layer D: Medical & Physical History
Injury history, surgery records, fitness tests, medical clearance. Access-tiered: clubs see summary (injury count, clearance status, fitness score), full records require player consent. Consent-gated architecture for ethics and regulatory compliance.

### Layer E: Video Evidence
Raw, unedited match footage with AI tracking overlays. Tagged with match context (opponent, competition, date). Explicitly distinguishes: AI-tracked full matches, raw clips, training footage, traditional highlights. Scouts verify AI data against visual evidence.

### Layer F: Behavioral & Professional Profile
Training attendance, discipline record, coach feedback, languages, leadership indicators, travel readiness. Framed as a professional portfolio players actively contribute to — not a surveillance report.

### Layer G: Contract, Transfer & Legal
Contract status, expiry, ownership rights, training compensation eligibility, FIFA TMS status, transfer history, release clauses. Enables cross-border transfer facilitation.

---

## AI VISION PIPELINE (Core Technical IP)

### Stage 1: Object Detection — YOLO v11
Each video frame → Ultralytics YOLO v11 → bounding boxes for every person detected. Filter to COCO class 0 (person). Configurable models: yolo11n (nano/fast/CPU), yolo11s (small), yolo11m (medium/accurate/GPU). Confidence threshold: 0.3 default.

### Stage 2: Multi-Object Tracking — ByteTrack
Roboflow `trackers` library (ByteTrack algorithm). Assigns persistent track_id to each detected person across all frames. Player #7 at kickoff = Player #7 at final whistle. ByteTrack handles occlusion recovery (players temporarily hidden behind others).

### Stage 3: SAM3 Enhancement Layer (NEW - Optional)
Meta's Segment Anything Model 3 provides **text-prompted segmentation**:

| Capability | Example Prompt | Output |
|-----------|----------------|--------|
| Team Segmentation | "players in blue jerseys" | Segmentation masks per team |
| Specific Tracking | "goalkeeper" | Track specific player by role |
| Ball Detection | "football soccer ball" | Ball position + possession |
| Referee Identification | "referee in black" | Exclude referees from player stats |

**SAM3 Architecture:**
```
YOLO+ByteTrack Results
         │
         ▼
    SAM3 Module
    ├── config.py          # HF auth, model settings
    ├── model_loader.py    # Lazy loading, GPU/CPU
    ├── processor.py       # Segmentation logic
    └── types.py           # Pydantic models
         │
         ▼
  Enhanced Track Data
  ├── team_label: "home" | "away" | "referee"
  ├── dominant_color: [R, G, B]
  ├── segmentation_mask: RLE encoded
  └── confidence: 0.0-1.0
```

**SAM3 API Endpoints:**
| Endpoint | Purpose |
|----------|---------|
| `GET /sam3/status` | Check availability, GPU, model loaded |
| `POST /sam3/segment` | Text-prompted frame segmentation |
| `POST /sam3/track` | Video object tracking with prompts |
| `POST /sam3/teams` | Segment by team (jersey color) |
| `POST /sam3/enhance/{job_id}/tracks` | Add SAM3 data to ByteTrack results |

**Why SAM3?**
- YOLO detects "person" generically → SAM3 enables "player in blue jersey #10"
- ByteTrack assigns arbitrary IDs → SAM3 enables team-filtered tracking
- No team differentiation → SAM3 segments by jersey color
- No ball tracking → SAM3 enables ball detection and possession analysis

### Stage 4: Metrics Extraction
Per-player from coordinate data:
- **Estimated minutes**: first/last frame visible → converted via FPS
- **Pitch zone heat maps**: frame divided into thirds (defensive/middle/attacking), percentage time in each
- **Sprint detection**: frame-to-frame pixel displacement above threshold = sprint
- **Speed**: average and max pixel displacement per frame (relative speed within match)
- **Visibility %**: proportion of total frames where track is active
- **Team affiliation** (with SAM3): home/away/referee classification
- **Jersey color** (with SAM3): dominant RGB for identification

### Stage 5: AI Report Generation
Tracking data → LLM (Gemini or Claude) → natural language scout report. LLM interprets zones as positional indicators, sprint count as work rate, visibility as substitution patterns. Data-driven, cites specific metrics.

### Pipeline Output
- `tracking_results.json` — full per-player tracking data
- `player_summary.csv` — stats table
- `annotated_output.mp4` — video with bounding boxes + track IDs overlaid
- `scout_report.txt` — AI-generated natural language report
- (Optional) SAM3 enhanced data with team labels and masks

### Processing Time
- GPU: ~15-25 min for 90-min match
- CPU: ~60-90 min for 90-min match
- SAM3 per frame: ~50-100ms (GPU), ~500ms (CPU)
- Runs async — users upload and continue working

---

## SCORING SYSTEM

### Reliability Score (0-100) — "How good is this player?"
| Component | Weight | Measures |
|-----------|--------|----------|
| Identity Verification | 20% | Documents confirmed, biometrics, age verification |
| Career Continuity | 20% | Unbroken timeline, no unexplained gaps, source-verified |
| Medical Transparency | 15% | Injury history documented, clearance current, fitness tests |
| Match Evidence | 25% | AI-tracked footage available, minutes verified, data consistent |
| Source Credibility | 10% | Official sources (federation/club) vs self-reported |
| Professional Conduct | 10% | Training attendance, discipline, coach feedback |

### Data Confidence Score (0-100) — "How much do we actually know?"
| Component | Weight | Measures |
|-----------|--------|----------|
| Identity Documents | 20% | How many documents on file and verified |
| Career Records | 20% | Completeness of timeline, source-verified entries |
| Match Footage | 25% | Number of AI-processed matches, total tracked minutes |
| Medical Records | 15% | Whether history exists and is current |
| External Sources | 20% | Independent sources confirming data |

These two scores are **independent**. High Reliability + Low Confidence = "looks good, needs more info." Low Reliability + High Confidence = "well-documented but concerning."

---

## AFRICAN LEAGUE INTELLIGENCE (Proprietary Moat)

Contextual data that no global platform provides:

| Metric | Purpose |
|--------|---------|
| League Strength Rating (1-10) | Calibrate expectations for foreign scouts |
| Club Credibility Score | Administrative reliability, payment history |
| Match Reliability Index | Accounts for data accuracy, match-fixing risk |
| Data Availability Rating | % of matches with structured stats |
| Travel/Logistics Profile | Visa, flights, time zones for transfer planning |
| Political/Operational Risk | Stability indicators for contracts |
| Registration Rules | Country-specific transfer regulations |

This compounds over time — more matches processed = richer contextual data = stronger moat.

---

## TECH STACK

| Component | Technology |
|-----------|-----------|
| Object Detection | Ultralytics YOLO v11 |
| Object Tracking | Roboflow `trackers` (ByteTrack) |
| **Text-Prompted Segmentation** | **Meta SAM3 (SAM2)** |
| Video Annotation | Supervision (`sv`) |
| Processing API | FastAPI (Python) |
| Web Application | Next.js 14 + TypeScript |
| Database | Supabase (PostgreSQL + Auth + Storage + Realtime) |
| File Storage | Supabase Storage (raw-footage, processed, clips buckets) |
| AI Reports | Google Gemini / Anthropic Claude |
| Web Hosting | Vercel |
| Processing Hosting | Railway / Render / GPU VM |
| **Containerization** | **Docker + NVIDIA CUDA** |

### Key Libraries
- `ultralytics` — YOLO model loading and inference
- `trackers` — ByteTrack/SORT multi-object tracking (Roboflow, Apache 2.0)
- **`transformers`** — SAM3 model loading from HuggingFace
- **`huggingface-hub`** — Model downloading and authentication
- `supervision` — Detection utilities, bounding box annotation, trace drawing
- `opencv-python` — Video I/O, frame processing
- `numpy` — Array operations
- `fastapi` + `uvicorn` — Async API server
- `supabase-py` — Python Supabase client

---

## DATABASE SCHEMA (Key Tables)

- `players` — Identity, verification status, scores, current club, position, agent
- `leagues` — Name, country, strength rating, data reliability, operational risk
- `clubs` — Name, league, credibility score, level
- `career_history` — Player career entries with source attribution, gap flagging
- `matches` — Teams, competition, date, processing job, video URLs, tracking stats
- `tracking_data` — Per-player-per-match: track_id, minutes, sprints, speed, heat map, events
- `match_events` — Goals, assists, cards, substitutions with timestamps
- `medical_records` — Injury/surgery/fitness with consent gating
- `videos` — Match footage with AI-tracking status, raw vs edited flag
- `player_profiles` — Behavioral/professional data
- `contracts` — Status, expiry, compensation, FIFA TMS, transfer history
- `organizations` — Clubs/agencies/colleges using ScoutBase
- `users` — Scouts/coaches/admins with Supabase Auth
- `shortlists` — User shortlists with player notes
- `scout_notes` — Private per-user notes on players
- `processing_jobs` — Video analysis pipeline job tracking

Row Level Security enabled on: scout_notes, shortlists, medical_records.

---

## TARGET MARKETS

1. **Rwanda (Launch)** — 16-team Premier League, strong digital infrastructure, government tech investment, compact geography, FERWAFA open to tech partnerships
2. **South Africa (Scale)** — PSL is most commercially developed African league, existing broadcast infrastructure, validates platform alongside existing data sources
3. **US Colleges (Expansion)** — NCAA international student-athlete recruitment has identical verification problems. Compliance officers need verified records. High willingness to pay.
4. **European/Asian Clubs (Buyers)** — Primary purchasers of African talent. Pay for intelligence that reduces signing risk.

---

## REVENUE MODEL

- Club Subscriptions (monthly/annual dashboard access)
- Pay-Per-Report (individual player intelligence reports)
- Transfer Success Fees (commission on facilitated transfers)
- API Access (programmatic data access for club integrations)
- Verification Services (identity/career verification for federations, agents)
- Premium Compliance Tools (contract management, TMS integration)

---

## EXECUTION ROADMAP

**Phase 1 (Weeks 1-4): Working Demo**
- Vision pipeline processing real footage end-to-end
- Annotated video output with tracking overlays
- Per-player tracking reports (JSON, CSV, AI scout report)
- Web dashboard with real processed data
- Milestone: upload a match → see stats + annotated video in dashboard

**Phase 2 (Weeks 5-12): Investor-Ready MVP**
- Full player profiles with 7 data layers
- Identity verification workflow
- Scoring algorithms live
- Shortlist/comparison tools
- Auth + org management
- 3-5 Rwandan clubs onboarded as pilot

**Phase 3 (Months 4-6): Pilot Validation**
- 5-10 clubs active (Rwanda + South Africa)
- 2-3 NCAA programs in paid pilot
- Federation advisory relationship
- Medical records module with consent
- League Intelligence for 5+ leagues

**Phase 4 (Months 7-12): Scale**
- Federation data import partnerships
- Cross-border transfer tools
- AI player comparison/recommendation
- Mobile app for field scouts
- East African league expansion
- Enterprise API

---

## LONG-TERM VISION (20-50 Year)

1. **Football first** → Multi-sport (basketball, athletics, rugby — same infrastructure)
2. **Software first** → Physical infrastructure (camera networks at stadiums become edge computing nodes for agriculture, construction, logistics)
3. **Data compounds** → Proprietary AI training data for African football: player valuation models, injury prediction, career trajectory forecasting
4. **Continental scale** → AI infrastructure for Africa, starting with sports, expanding to broader economic applications
5. **Eventual goal** → Data centers in Congo DRC as part of broader African AI infrastructure vision

Football is the entry point because money is obvious (transfer market), pain is real, and emotional connection in Africa is unmatched. But the underlying platform is much bigger.

---

## PROJECT STRUCTURE

```
africa-vision-os/
├── server.py                    # FastAPI server (all endpoints)
├── process_match.py             # Core: YOLO + ByteTrack → player stats
├── requirements.txt             # Python dependencies
├── Dockerfile                   # GPU-enabled container (CUDA 12.1)
├── docker-compose.yml           # Dev compose with GPU support
├── .env.example                 # Environment template
│
├── sam3/                        # SAM3 Integration Module (NEW)
│   ├── __init__.py              # Module exports
│   ├── config.py                # HF auth, model variant, device
│   ├── model_loader.py          # Lazy loading, checkpoint management
│   ├── processor.py             # Segmentation/tracking logic
│   └── types.py                 # Pydantic request/response models
│
├── web/                         # Next.js web application
│   ├── src/
│   │   ├── app/                 # App router pages
│   │   │   ├── dashboard/       # Main dashboard
│   │   │   └── player/[id]/     # Player profile
│   │   ├── components/          # React components
│   │   └── lib/
│   │       ├── api.ts           # API client functions (incl. SAM3)
│   │       ├── types.ts         # TypeScript definitions
│   │       └── supabase.ts      # Supabase client config
│   └── package.json
│
├── checkpoints/                 # Model checkpoint storage
├── uploads/                     # Uploaded videos
├── results/                     # Processing outputs
│
├── docs/                        # Documentation
│   ├── BMAD.md                  # Development methodology
│   └── CONTEXT_ENGINEERING.md   # AI collaboration guide
│
├── ARCHITECTURE.md              # Technical architecture
├── SCOUTBASE_CONTEXT.md         # Full project context (this file)
├── CURRENT_STATE.md             # Current status (AI agents MUST update)
└── README.md                    # Project overview
```

---

## PROCESSING API ENDPOINTS

### Core Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /process | Upload video + start processing |
| GET | /status/{job_id} | Check processing job status |
| GET | /results/{job_id} | Get tracking results + player stats |
| GET | /results/{job_id}/video | Download annotated video |
| GET | /results/{job_id}/csv | Download player summary CSV |
| GET | /results/{job_id}/tracks | Get all tracks with assignments |
| GET | /jobs | List all processing jobs |
| GET | /health | Health check |

### SAM3 Enhancement (NEW)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /sam3/status | Check SAM3 availability, GPU, model status |
| POST | /sam3/segment | Text-prompted frame segmentation |
| POST | /sam3/track | Video object tracking with text prompts |
| POST | /sam3/teams | Segment players by team (jersey color) |
| POST | /sam3/enhance/{job_id}/tracks | Add SAM3 data to ByteTrack results |

### Player Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /players | List all players with filters |
| POST | /players | Create new player |
| GET | /players/{id} | Get player details |
| PUT | /players/{id} | Update player |
| GET | /shortlist | Get shortlisted players |
| POST | /shortlist/{id} | Add to shortlist |
| DELETE | /shortlist/{id} | Remove from shortlist |

### Track Assignment
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /results/{job_id}/tracks/{track_id}/assign | Assign track to player |
| POST | /results/{job_id}/tracks/{track_id}/create-player | Create player from track |
| DELETE | /results/{job_id}/tracks/{track_id}/unassign | Remove assignment |

---

## KEY DIFFERENTIATORS

1. **AI-generated data from footage** — Not dependent on manual stats or league infrastructure
2. **Two-score system** — Separates player quality from data availability (ethical + useful)
3. **African league context** — Proprietary intelligence layer no global platform has
4. **Raw evidence** — Unedited footage with AI annotations, not curated highlights
5. **Consent-first design** — GDPR-ready, FIFA-compliant, player-controlled sensitive data
6. **Verification provenance** — Every data point tagged with source and verification status

---

## WHO IS BUILDING THIS

**Sloe Labs** — AI solutions consultancy run by Sloe, originally from Congo DRC, currently based in Canada. Background in AI systems development across restaurants, construction, real estate, e-commerce. Technical stack: Next.js, TypeScript, Supabase, Python, n8n, Vercel. Long-term vision: AI infrastructure for Africa.

---

## CODING CONVENTIONS

When working on this codebase:

- **Python (processing)**: Type hints, dataclasses for data structures, async where appropriate, comprehensive logging
- **TypeScript (web)**: Strict mode, Supabase client with typed queries, server components by default (Next.js App Router)
- **Database**: All tables have created_at/updated_at timestamps, UUID primary keys, foreign key relationships, RLS on sensitive tables
- **API responses**: Always include status field, use job_id pattern for async operations
- **Video processing**: Always generate both JSON results and annotated video output
- **Player data**: Always include verification_status and data_source fields
- **Scores**: Always compute Reliability and Data Confidence independently

---

## TERMINOLOGY

| Term | Meaning |
|------|---------|
| Track ID | ByteTrack-assigned persistent ID for a detected person across video frames |
| Reliability Score | Composite 0-100 score measuring verified player quality |
| Data Confidence Score | Composite 0-100 score measuring data availability/completeness |
| Layer (A-G) | One of seven data categories in the player profile architecture |
| Vision Pipeline | The YOLO → ByteTrack → Metrics → AI Report processing chain |
| League Intelligence | Proprietary contextual data about African leagues/clubs |
| Annotated Video | Output video with bounding boxes and track IDs overlaid on frames |
| Heat Map | Zone distribution showing where a player spent time on the pitch |
| Processing Job | An async video analysis task with status tracking |
| Verification Badge | ✅ Verified / ⚠️ Partial / ❌ Unverified status on data points |
| **SAM3** | Segment Anything Model 3 — Meta's text-prompted segmentation model |
| **Text-Prompted Segmentation** | Segmenting objects by natural language description |
| **RLE (Run-Length Encoding)** | Compact encoding for binary segmentation masks |
| **Team Label** | Classification of track as home/away/referee/unknown |
| **Dominant Color** | Most common RGB color in a segmented region (jersey detection) |
| **Lazy Loading** | Loading model only when first needed, not at startup |

---

## DEVELOPMENT METHODOLOGY

This project follows the **BMAD (Breakthrough Method for Agile AI-Driven Development)** methodology for AI-assisted software engineering.

### Key Practices

1. **Context Engineering** — Rich documentation that can be loaded into any AI context
2. **Role Specialization** — AI assistants play specific roles (Architect, Implementer, Reviewer)
3. **Iterative Refinement** — Plan → Scaffold → Implement → Refine → Document
4. **Human-in-the-Loop** — Critical decisions require human judgment
5. **Explicit Constraints** — Clear boundaries for what AI should/shouldn't do

### Documentation Files

| Document | Purpose | Update Frequency |
|----------|---------|-----------------|
| `SCOUTBASE_CONTEXT.md` | Full project context | When major changes occur |
| `ARCHITECTURE.md` | Technical architecture | When architecture changes |
| `docs/BMAD.md` | Development methodology | Rarely |
| `docs/CONTEXT_ENGINEERING.md` | AI collaboration guide | Rarely |

### Session Start Protocol

When beginning an AI-assisted development session:

1. Load `SCOUTBASE_CONTEXT.md` for project understanding
2. State the specific task clearly
3. Set constraints explicitly
4. Request planning before implementation
5. Review and refine iteratively

For detailed methodology, see: `docs/BMAD.md`
For context engineering strategies, see: `docs/CONTEXT_ENGINEERING.md`

---

## ENVIRONMENT VARIABLES

### Required for SAM3
```bash
HF_TOKEN=hf_xxxxx              # HuggingFace token (request access first)
SAM3_VARIANT=base              # base, large, or huge
SAM3_DEVICE=auto               # cuda, cpu, or auto
```

### Optional: Database
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Optional: AI Reports
```bash
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

---

*End of context document. This file should be updated as the project evolves.*
*Last updated: February 2026*
