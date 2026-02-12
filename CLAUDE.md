# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # Add your ANTHROPIC_API_KEY
python run.py            # Runs on :8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev              # Runs on :5173
```

Open http://localhost:5173

## Commands

```bash
# Frontend
cd frontend && npm run dev       # Dev server with HMR
cd frontend && npm run build     # Production build → dist/
cd frontend && npm run lint      # ESLint (TS + React)
cd frontend && npm run preview   # Preview production build

# Backend
cd backend && python run.py      # Uvicorn dev server

# Terraform (used by deployer.py, rarely run manually)
cd terraform && terraform init -backend-config=bucket={project}-airlock-tf-state
cd terraform && terraform apply -var=project_id=... -var=deployment_id=... -var=image_url=...
```

No test suite exists yet. Sample ZIPs for manual testing are in `sample-zips/`.

## Architecture

Drag-and-drop ZIP deployment gateway: user uploads a ZIP of static HTML/CSS/JS, the backend runs concurrent AI checks (security, cost, brand), then containerizes with nginx and deploys to Cloud Run via Terraform. Detailed diagrams in `ARCHITECTURE.md` and `FLOW.md`.

**Frontend** (React 19 + Vite + TypeScript 5.9): State machine in `App.tsx` drives the UI through phases: `upload → checking → results → deploying → deployed`. API client in `api.ts` hits `/api/*` which Vite proxies to the backend (`vite.config.ts`). All styles in a single `App.css` with CSS variables for brand colors. Components: `DropZone`, `UploadProgress`, `CheckResults`, `StatusBadge`, `DeployButton`, `DeploymentList`, `DeploymentCard`, `Header`. Polling (10s interval) keeps deployment list updated.

**Backend** (FastAPI + SQLite via aiosqlite):
- `routers/upload.py` — Accepts ZIP, validates via `zip_handler.py`, runs 3 AI checks concurrently via `ai_analyzer.py`, stores results in SQLite
- `routers/deployments.py` — Deploy (blocked if `security_status='fail'`), list, get, teardown
- `services/deployer.py` — Generates `Dockerfile` (nginx:alpine), runs `gcloud builds submit`, then `terraform apply` with a per-deployment workspace (`airlock-{id[:12]}`)
- `services/cleanup.py` — Background loop (60s interval) tears down expired demo deployments
- `prompts/` — System prompts for security, cost, and brand AI checks

ZIP validation (`zip_handler.py`): 50MB upload / 100MB extracted limit, allowed extension whitelist, path traversal blocked, requires `index.html` (auto-promoted from one level deep if needed).

AI checks use `claude-sonnet-4-5-20250929` with max 1024 tokens per check.

**Terraform** (`terraform/modules/airlock-deployment/`): Cloud Run v2 service with scale-to-zero, public IAM access. One Terraform workspace per deployment, state in GCS.

**code-armor/** — Separate Spring Boot 4.0.2 (Java/JDK 25) module with JWT auth, Spring Data JPA, MySQL via Docker. Independent from the main Python backend; has its own `controller/`, `service/`, `repository/`, `security/` packages.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload` | POST | Accept ZIP (multipart), validate, run AI checks |
| `/api/deployments` | GET | List all deployments |
| `/api/deployments/{id}` | GET | Get single deployment |
| `/api/deployments/{id}/deploy` | POST | Build container + deploy to Cloud Run |
| `/api/deployments/{id}` | DELETE | Teardown infra + delete record |
| `/api/health` | GET | Health check |

### Deployment Status Flow
```
pending → checked → deploying → deployed → expired (demos only)
                 ↘ failed
```

### Database Schema (`deployments` table)
Single SQLite table: `id` (16-char hex PK), `name`, `status`, `mode` (demo|prod), `file_count`, `total_size`, `security_status`, `security_details` (JSON), `cost_status`, `cost_details` (JSON), `brand_status`, `brand_details` (JSON), `cloud_run_url`, `created_at`, `deployed_at`, `expires_at`.

### Naming Conventions
- Deployment IDs: 16-char hex from `uuid4().hex[:16]`
- Terraform workspaces: `airlock-{id[:12]}`
- Cloud Run services: `airlock-{id}`
- Container images: `{region}-docker.pkg.dev/{project}/airlock/{id}:latest`

### Key Design Decisions
- AI checks return `pass|warn|fail` — only security `fail` blocks deployment (403)
- Demo deployments auto-expire after 1 hour (`demo_ttl_seconds` in config)
- GCP project ID auto-detected via `gcloud config get-value project` in `config.py`
- All AI check errors fall back to `warn` (never block on AI failure)
- ZIP validation skips `__MACOSX/` and dotfiles automatically

## Environment Variables

Required: `ANTHROPIC_API_KEY`
Optional: `GCP_PROJECT_ID`, `GCP_REGION` (defaults to `europe-north1`)

## Planned Features

**Gemini Chat Integration** (`GEMINI_CHAT_PLAN.md`): `POST /api/generate` endpoint using `gemini-2.5-flash` to generate static sites from prompts. Auto-retry loop for security failures (up to 2x). Frontend `ChatPanel` component alongside current upload flow.

## Gotchas

- **Python 3.9**: Use `from __future__ import annotations` when using `str | None` union syntax
- **Vite scaffold**: Won't overwrite existing directory — delete first, then create
- **Brand colors**: Primary `#0C0C0C` (black), `#FFB800` (gold), `#FFFFFF` (white); Secondary `#173EDE` (blue), `#FFEDBE` (cream), `#DFF1F1` (teal). Font: IBM Plex Sans (loaded from Google Fonts in `frontend/index.html`)
- **macOS ZIPs**: `__MACOSX/` directories and `._` resource fork files are auto-skipped in `zip_handler.py`
