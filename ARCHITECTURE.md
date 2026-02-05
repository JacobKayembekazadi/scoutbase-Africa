# ScoutBase Africa — Technical Architecture & Build Guide

## What We're Building

A **Player Intelligence & Risk Assessment Platform** for African football, powered by
computer vision. The platform auto-generates verified player data from match footage
using YOLO object detection + ByteTrack multi-object tracking, then serves it through
a web dashboard for scouts, clubs, and college programs.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    SCOUTBASE PLATFORM                     │
├─────────────────────┬───────────────────────────────────┤
│                     │                                     │
│   Next.js Web App   │      Python Processing Service      │
│   (Vercel)          │      (Railway / Render / GPU VM)    │
│                     │                                     │
│  ┌───────────────┐  │  ┌─────────────────────────────┐   │
│  │ Dashboard      │  │  │ Video Upload Handler        │   │
│  │ Player Profile │  │  │         │                   │   │
│  │ Search/Filter  │  │  │         ▼                   │   │
│  │ Video Playback │  │  │ YOLO Detection (per frame)  │   │
│  │ Shortlists     │  │  │         │                   │   │
│  │ Reports        │  │  │         ▼                   │   │
│  │ League Intel   │  │  │ ByteTrack Tracking          │   │
│  └───────┬───────┘  │  │  (persistent player IDs)     │   │
│          │          │  │         │                   │   │
│          │          │  │         ▼                   │   │
│          │          │  │ Metrics Extraction            │   │
│          │          │  │  (per-player stats)           │   │
│          │          │  │         │                   │   │
│          │          │  │         ▼                   │   │
│          │          │  │ Annotated Video Output        │   │
│          │          │  └────────┬────────────────────┘   │
│          │          │           │                         │
├──────────┴──────────┴───────────┴─────────────────────────┤
│                                                           │
│                    Supabase (Database)                     │
│  ┌─────────────┬──────────────┬────────────────────┐     │
│  │ players     │ matches      │ tracking_data      │     │
│  │ clubs       │ match_events │ processing_jobs    │     │
│  │ leagues     │ videos       │ scout_reports      │     │
│  │ medical     │ contracts    │ shortlists         │     │
│  └─────────────┴──────────────┴────────────────────┘     │
│                                                           │
│                 Supabase Storage (Videos)                  │
│  ┌──────────────────────────────────────────────┐        │
│  │ raw-footage/   │   processed/   │  clips/    │        │
│  └──────────────────────────────────────────────┘        │
└───────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer              | Technology                          | Why                                      |
|--------------------|-------------------------------------|------------------------------------------|
| Frontend           | Next.js 14 + TypeScript             | Your stack, SSR, Vercel deploy           |
| Database           | Supabase (Postgres + Auth + Storage)| Your stack, real-time, row-level security|
| Video Processing   | Python + YOLO + Roboflow Trackers   | Best-in-class detection + tracking       |
| Object Detection   | Ultralytics YOLOv11 / RF-DETR       | Fast, accurate person detection          |
| Object Tracking    | `trackers` lib (ByteTrack/SORT)     | Persistent player IDs across frames      |
| **Text Segmentation** | **Meta SAM3 (SAM2)**             | **Text-prompted segmentation, team ID**  |
| Video Annotation   | Supervision (`sv`)                  | Bounding boxes, labels, traces on video  |
| AI Analysis        | Google Gemini / Claude API          | Generate scout reports from tracking data|
| Hosting (Web)      | Vercel                              | Your standard deploy                     |
| Hosting (Process)  | Railway / Render / GPU VM           | Python service needs GPU for YOLO        |
| **Containerization** | **Docker + NVIDIA CUDA**          | **GPU-enabled containers**               |
| Queue (optional)   | Supabase Edge Functions + webhooks  | Trigger processing on video upload       |

---

## Build Phases

### Phase 1: Working Demo (2-3 weeks) ← YOU ARE HERE
- [ ] Python processing pipeline (upload video → detect → track → extract stats)
- [ ] Supabase database schema
- [ ] Next.js dashboard connected to real Supabase data
- [ ] Upload video → see processed results in dashboard
- [ ] Deploy processing service + web app

### Phase 2: Investor-Ready MVP (4-6 weeks)
- [ ] Player profile pages with real tracked data
- [ ] Video playback with tracking overlays
- [ ] Basic verification system (manual + AI-assisted)
- [ ] Shortlist + comparison tools
- [ ] Auth (Supabase Auth — club accounts)
- [ ] Reliability score algorithm

### Phase 3: Pilot (2-3 months)
- [ ] Rwanda Premier League pilot (5 clubs)
- [ ] South Africa PSL integration
- [ ] NCAA college program dashboard variant
- [ ] Medical records module (with consent framework)
- [ ] Federation data import tools

---

## Key Files in This Project

```
africa-vision-os/
├── server.py                    # FastAPI server (all endpoints)
├── process_match.py             # Core pipeline: YOLO + ByteTrack → player stats
├── requirements.txt             # Python dependencies
├── Dockerfile                   # GPU-enabled container (CUDA 12.1)
├── docker-compose.yml           # Dev compose with GPU support
├── .env.example                 # Environment variable template
│
├── sam3/                        # SAM3 Integration Module (NEW)
│   ├── __init__.py              # Module exports
│   ├── config.py                # HF auth, model variant, device
│   ├── model_loader.py          # Lazy loading from HuggingFace
│   ├── processor.py             # Core segmentation/tracking logic
│   └── types.py                 # Pydantic request/response models
│
├── web/                         # Next.js web application
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/       # Main dashboard page
│   │   │   └── player/[id]/     # Player profile page
│   │   ├── components/          # React components
│   │   └── lib/
│   │       ├── api.ts           # API client (includes SAM3)
│   │       ├── types.ts         # TypeScript definitions
│   │       └── supabase.ts      # Supabase client
│   └── package.json
│
├── checkpoints/                 # Model checkpoint storage
├── uploads/                     # Uploaded videos
├── results/                     # Processing outputs
│
├── docs/
│   ├── BMAD.md                  # Development methodology
│   └── CONTEXT_ENGINEERING.md   # AI collaboration guide
│
├── ARCHITECTURE.md              # This file
├── SCOUTBASE_CONTEXT.md         # Full project context
├── CURRENT_STATE.md             # Current status (AI agents MUST update)
└── README.md                    # Project overview
```

---

## API Endpoints (Processing Service)

### Core Pipeline
| Method | Endpoint              | Description                              |
|--------|-----------------------|------------------------------------------|
| POST   | /process              | Upload video + start processing          |
| GET    | /status/{job_id}      | Check processing job status              |
| GET    | /results/{job_id}     | Get tracking results + player stats      |
| GET    | /results/{job_id}/video | Download annotated video               |
| GET    | /results/{job_id}/csv | Download player summary CSV              |
| GET    | /results/{job_id}/tracks | Get all tracks with assignments        |
| GET    | /jobs                 | List all processing jobs                 |
| GET    | /health               | Health check                             |

### SAM3 Enhancement (NEW)
| Method | Endpoint                        | Description                        |
|--------|--------------------------------|-------------------------------------|
| GET    | /sam3/status                   | Check SAM3 availability & GPU      |
| POST   | /sam3/segment                  | Text-prompted frame segmentation   |
| POST   | /sam3/track                    | Video tracking with text prompts   |
| POST   | /sam3/teams                    | Segment players by team (jersey)   |
| POST   | /sam3/enhance/{job_id}/tracks  | Add SAM3 data to ByteTrack results |

### Player Management
| Method | Endpoint              | Description                              |
|--------|-----------------------|------------------------------------------|
| GET    | /players              | List all players with filters            |
| POST   | /players              | Create new player                        |
| GET    | /players/{id}         | Get player details                       |
| PUT    | /players/{id}         | Update player                            |
| GET    | /shortlist            | Get shortlisted players                  |

---

## How the Vision Pipeline Works

1. **Video uploaded** → stored in Supabase Storage
2. **Processing triggered** → Python service downloads video
3. **Frame-by-frame detection** → YOLO detects all persons in each frame
4. **ByteTrack tracking** → Assigns persistent IDs across frames
   - Player entering at frame 1 as `track_id=7` stays `7` for the entire match
5. **SAM3 enhancement (optional)** → Text-prompted segmentation
   - "players in blue jerseys" → segments home team
   - "goalkeeper" → tracks specific player by role
   - Adds team labels, dominant colors, segmentation masks
6. **Per-player metrics extracted:**
   - Total frames visible (→ estimated minutes played)
   - Bounding box positions over time (→ heat map / movement data)
   - Speed estimates from pixel displacement between frames
   - Zone presence (divide pitch into thirds)
   - Key moments (sudden acceleration = sprint, proximity to goal = involvement)
   - Team affiliation (with SAM3): home/away/referee
7. **Annotated video generated** → Bounding boxes + track IDs overlaid
8. **Results stored** → Supabase tables populated with per-player data
9. **AI report generated** → Feed tracking data to Gemini/Claude for scout report

### SAM3 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 SAM3 ENHANCEMENT LAYER                       │
│                   (Optional, On-Demand)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ /sam3/status │    │ /sam3/segment│    │ /sam3/track  │  │
│  │ Health check │    │ Single frame │    │ Video track  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  ┌──────────────┐    ┌────────────────────────────────────┐ │
│  │ /sam3/teams  │    │ /sam3/enhance/{job_id}/tracks      │ │
│  │ Team segment │    │ Link SAM3 to existing ByteTrack    │ │
│  └──────────────┘    └────────────────────────────────────┘ │
│                                                              │
│  sam3/                                                       │
│  ├── config.py         # HF auth, model variant, device     │
│  ├── model_loader.py   # Lazy loading from HuggingFace     │
│  ├── processor.py      # Core segmentation logic           │
│  └── types.py          # Pydantic request/response models  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment

### Processing Service (Railway)
```bash
cd processing
railway init
railway up
```
Note: For GPU acceleration, use Render GPU instances or a dedicated
VM (Hetzner, Lambda Labs). CPU processing works but is slower (~0.5 FPS
vs ~30 FPS on GPU).

### Web App (Vercel)
```bash
cd web
vercel deploy
```

### Database (Supabase)
1. Create project at supabase.com
2. Run schema.sql in SQL editor
3. Enable Storage for video buckets
4. Set up Row Level Security policies

---

## Environment Variables

### Processing Service
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
PROCESSING_WEBHOOK_URL=https://your-nextjs-app.vercel.app/api/webhook
GEMINI_API_KEY=xxx           # For AI report generation
```

### Web App
```
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
PROCESSING_SERVICE_URL=https://your-processing-service.railway.app
```

### SAM3 Integration (NEW)
```
HF_TOKEN=hf_xxxxxxxxxxxxx         # HuggingFace token (required)
SAM3_VARIANT=base                 # "base", "large", or "huge"
SAM3_DEVICE=auto                  # "cuda", "cpu", or "auto"
SAM3_LAZY_LOAD=true              # Load model on first request
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview, quick start, API reference |
| `ARCHITECTURE.md` | Technical architecture (this file) |
| `SCOUTBASE_CONTEXT.md` | Full project context for AI assistance |
| `docs/BMAD.md` | BMAD development methodology |
| `docs/CONTEXT_ENGINEERING.md` | AI collaboration strategies |
| `.env.example` | Environment variable template |
