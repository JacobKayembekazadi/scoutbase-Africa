# ScoutBase Africa Vision OS

**AI-Powered Player Intelligence & Risk Assessment Platform for African Football**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

ScoutBase Africa transforms raw match footage into verified player intelligence using computer vision. Point a camera at any African league match and automatically generate the same quality of player data that European leagues produce with million-dollar stadium systems.

### Core Capabilities

| Feature | Technology | Output |
|---------|------------|--------|
| **Player Detection** | YOLOv11 | Bounding boxes for every person per frame |
| **Multi-Object Tracking** | ByteTrack | Persistent player IDs across entire match |
| **Text-Prompted Segmentation** | SAM3 (NEW) | "Segment all players in blue jerseys" |
| **Team Differentiation** | SAM3 + Color Analysis | Home/Away/Referee classification |
| **Metrics Extraction** | Custom Pipeline | Minutes, sprints, speed, heat maps |
| **AI Scout Reports** | Gemini/Claude | Natural language performance analysis |

---

## Architecture

```
Video Input
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VISION PIPELINE                               │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ YOLO v11     │───▶│ ByteTrack    │───▶│ Metrics          │  │
│  │ Detection    │    │ Tracking     │    │ Extraction       │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                   │                     │             │
│         │                   ▼                     │             │
│         │          ┌──────────────────┐          │             │
│         └─────────▶│ SAM3 Enhancement │◀─────────┘             │
│                    │ (Optional Layer) │                         │
│                    │ - Text Prompts   │                         │
│                    │ - Team Labels    │                         │
│                    │ - Segmentation   │                         │
│                    └──────────────────┘                         │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │ Output           │
                    │ - JSON Results   │
                    │ - Annotated Video│
                    │ - CSV Summary    │
                    │ - AI Report      │
                    └──────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- GPU with CUDA (recommended) or CPU
- HuggingFace account (for SAM3)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/africa-vision-os.git
cd africa-vision-os

# Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install ByteTrack
pip install git+https://github.com/roboflow/trackers.git

# Frontend setup
cd web
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Running Locally

```bash
# Terminal 1: Start API server
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start web app
cd web
npm run dev
```

### Docker Deployment (GPU)

```bash
# Build and run with GPU support
docker-compose up --build

# Or without GPU
docker build -t scoutbase-api .
docker run -p 8000:8000 -e HF_TOKEN=your_token scoutbase-api
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/process` | Upload video and start processing |
| `GET` | `/status/{job_id}` | Check job status |
| `GET` | `/results/{job_id}` | Get tracking results |
| `GET` | `/results/{job_id}/video` | Download annotated video |
| `GET` | `/results/{job_id}/tracks` | Get all tracks with assignments |

### SAM3 Endpoints (NEW)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sam3/status` | Check SAM3 availability and GPU status |
| `POST` | `/sam3/segment` | Text-prompted frame segmentation |
| `POST` | `/sam3/track` | Video object tracking with text prompts |
| `POST` | `/sam3/teams` | Segment players by team (jersey color) |
| `POST` | `/sam3/enhance/{job_id}/tracks` | Add SAM3 data to ByteTrack results |

### Player Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/players` | List all players |
| `POST` | `/players` | Create new player |
| `PUT` | `/players/{id}` | Update player |
| `GET` | `/shortlist` | Get shortlisted players |

---

## SAM3 Integration

SAM3 (Segment Anything Model 3) adds text-prompted segmentation capabilities:

### Setup

1. **Request HuggingFace Access**
   ```
   https://huggingface.co/facebook/sam2.1-hiera-base-plus
   ```

2. **Configure Environment**
   ```bash
   export HF_TOKEN=hf_your_token_here
   export SAM3_VARIANT=base  # base, large, or huge
   export SAM3_DEVICE=auto   # cuda, cpu, or auto
   ```

### Usage Examples

**Segment by text prompt:**
```python
import requests

response = requests.post("http://localhost:8000/sam3/segment", json={
    "job_id": "abc123",
    "frame_number": 500,
    "prompt": "players in blue jerseys",
    "confidence_threshold": 0.5
})
```

**Team segmentation:**
```python
response = requests.post("http://localhost:8000/sam3/teams", json={
    "job_id": "abc123",
    "home_color_hint": "blue",
    "away_color_hint": "red",
    "include_ball": True
})
```

**Enhance existing tracks:**
```python
response = requests.post("http://localhost:8000/sam3/enhance/abc123/tracks", json={
    "add_team_labels": True,
    "sample_frames": 20
})
```

---

## Project Structure

```
africa-vision-os/
├── server.py                 # FastAPI server with all endpoints
├── process_match.py          # YOLO + ByteTrack pipeline
├── requirements.txt          # Python dependencies
├── Dockerfile               # GPU-enabled container
├── docker-compose.yml       # Dev compose with GPU
├── .env.example            # Environment template
│
├── sam3/                    # SAM3 Integration Module
│   ├── __init__.py         # Module exports
│   ├── config.py           # HF auth, model settings
│   ├── model_loader.py     # Lazy loading, checkpoints
│   ├── processor.py        # Segmentation/tracking logic
│   └── types.py            # Pydantic models
│
├── web/                     # Next.js Frontend
│   ├── src/
│   │   ├── app/            # App router pages
│   │   ├── components/     # React components
│   │   └── lib/
│   │       ├── api.ts      # API client functions
│   │       └── types.ts    # TypeScript definitions
│   └── package.json
│
├── checkpoints/            # Model checkpoint storage
├── uploads/                # Uploaded videos
├── results/                # Processing outputs
│
└── docs/                   # Documentation
    ├── ARCHITECTURE.md     # Technical architecture
    ├── SCOUTBASE_CONTEXT.md # Full project context
    ├── BMAD.md            # Development methodology
    └── CONTEXT_ENGINEERING.md # AI collaboration guide
```

---

## Environment Variables

```bash
# Required for SAM3
HF_TOKEN=hf_xxxxx                    # HuggingFace token

# SAM3 Configuration
SAM3_VARIANT=base                    # base, large, huge
SAM3_DEVICE=auto                     # cuda, cpu, auto

# Optional: Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Optional: AI Reports
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Performance

| Configuration | Video Length | Processing Time |
|--------------|--------------|-----------------|
| GPU (RTX 3080) | 90 min match | ~15-25 min |
| CPU (8-core) | 90 min match | ~60-90 min |
| GPU + SAM3 | Per frame | ~50-100ms |

---

## Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Technical architecture and system design
- **[SCOUTBASE_CONTEXT.md](./SCOUTBASE_CONTEXT.md)** - Full project context for AI assistance
- **[CURRENT_STATE.md](./CURRENT_STATE.md)** - Current project status (MUST READ/UPDATE)
- **[BMAD.md](./docs/BMAD.md)** - BMAD development methodology
- **[CONTEXT_ENGINEERING.md](./docs/CONTEXT_ENGINEERING.md)** - AI collaboration strategies

---

## For AI Agents

> **MANDATORY PROTOCOL**: All AI agents working on this project MUST:

1. **READ** `CURRENT_STATE.md` before starting any work
2. **UPDATE** `CURRENT_STATE.md` after EVERY session with:
   - What was added/modified/removed
   - Files changed
   - Any issues discovered
3. **FOLLOW** the BMAD methodology in `docs/BMAD.md`

**Failure to update `CURRENT_STATE.md` violates project protocol.**

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

## Acknowledgments

- [Ultralytics](https://github.com/ultralytics/ultralytics) - YOLOv11
- [Roboflow](https://github.com/roboflow/trackers) - ByteTrack implementation
- [Meta AI](https://github.com/facebookresearch/segment-anything-2) - SAM2/SAM3
- [Supervision](https://github.com/roboflow/supervision) - Video annotation

---

**Built by [Sloe Labs](https://sloe.ai)** - AI Infrastructure for Africa
