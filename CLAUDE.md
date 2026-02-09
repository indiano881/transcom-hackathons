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

No test suite exists yet.

## Architecture

Drag-and-drop ZIP deployment gateway: user uploads a ZIP of static HTML/CSS/JS, the backend runs concurrent AI checks (security, cost, brand), then containerizes with nginx and deploys to Cloud Run via Terraform.

**Frontend** (React 19 + Vite + TypeScript): State machine in `App.tsx` drives the UI through phases: `upload → checking → results → deploying → deployed`. API client in `api.ts` hits `/api/*` which Vite proxies to the backend (`vite.config.ts`).

**Backend** (FastAPI + SQLite via aiosqlite):
- `routers/upload.py` — Accepts ZIP, validates via `zip_handler.py` (50MB max, allowed extensions, requires `index.html`), runs 3 AI checks concurrently via `ai_analyzer.py`, stores results in SQLite
- `routers/deployments.py` — Deploy (blocked if `security_status='fail'`), list, get, teardown
- `services/deployer.py` — Generates `Dockerfile` (nginx:alpine), runs `gcloud builds submit`, then `terraform apply` with a per-deployment workspace (`airlock-{id[:12]}`)
- `services/cleanup.py` — Background loop (60s interval) tears down expired demo deployments
- `prompts/` — System prompts for security, cost, and brand AI checks

**Terraform** (`terraform/modules/airlock-deployment/`): Cloud Run v2 service with scale-to-zero, public IAM access. One Terraform workspace per deployment, state in GCS.

### Deployment Status Flow
```
pending → checked → deploying → deployed → expired (demos only)
                 ↘ failed
```

### Key Design Decisions
- AI checks return `pass|warn|fail` — only security `fail` blocks deployment (403)
- Demo deployments auto-expire after 1 hour (`demo_ttl_seconds` in config)
- GCP project ID auto-detected via `gcloud config get-value project` in `config.py`
- All AI check errors fall back to `warn` (never block on AI failure)

## Environment Variables

Required: `ANTHROPIC_API_KEY`
Optional: `GCP_PROJECT_ID`, `GCP_REGION` (defaults to `europe-north1`)

## Gotchas

- **Python 3.9**: Use `from __future__ import annotations` when using `str | None` union syntax
- **Vite scaffold**: Won't overwrite existing directory — delete first, then create
- **Brand colors**: Primary `#0C0C0C` (black), `#FFB800` (gold), `#FFFFFF` (white); Secondary `#173EDE` (blue), `#FFEDBE` (cream), `#DFF1F1` (teal). Font: IBM Plex Sans (loaded from Google Fonts in `frontend/index.html`)
