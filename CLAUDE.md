# Innovation Airlock

Transcom hackathon project — drag-and-drop ZIP deployment to Cloud Run with AI-powered checks.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example .env  # Add your ANTHROPIC_API_KEY
python run.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Architecture

- **Frontend**: React + Vite + TypeScript at `:5173`, proxies `/api` to backend
- **Backend**: Python FastAPI at `:8000`, SQLite database
- **AI**: Anthropic claude-sonnet-4-5-20250929 for security/cost/brand checks
- **Deploy**: gcloud builds submit → Terraform → Cloud Run (europe-north1)

## Key Files

- `backend/app/main.py` — FastAPI app entry
- `backend/app/routers/upload.py` — ZIP upload + AI checks
- `backend/app/routers/deployments.py` — Deploy + CRUD + teardown
- `backend/app/services/ai_analyzer.py` — Claude API integration
- `backend/app/services/deployer.py` — Cloud Build + Terraform
- `frontend/src/App.tsx` — Main state machine
- `terraform/modules/airlock-deployment/` — Cloud Run infra

## Brand

Colors: `#0C0C0C` (black), `#FFB800` (gold), `#FFFFFF` (white), `#173EDE` (blue)
Font: IBM Plex Sans
