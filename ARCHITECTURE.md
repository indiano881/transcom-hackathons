# Innovation Airlock — Architecture

## Overview

Innovation Airlock is a self-service deployment gateway for static frontend projects at Transcom. Users upload a ZIP archive containing HTML/CSS/JS, the system runs AI-powered checks, and — if approved — containerizes and deploys the site to Google Cloud Run.

```
                        +-------------------------------------------+
                        |              Innovation Airlock            |
                        +-------------------------------------------+

  +-----------+         +-----------------+         +-----------------+
  |           |  HTTP   |                 | Claude  |                 |
  |  Browser  | ------> |  FastAPI        | ------> |  Anthropic API  |
  |  (React)  | <------ |  Backend        | <------ |  (Claude 4.5    |
  |           |         |  :8000          |         |   Sonnet)       |
  +-----------+         +-----------------+         +-----------------+
   localhost:5173              |    |
   (Vite dev proxy)           |    |
                              v    v
                     +--------+    +-----------+
                     | SQLite |    | Local     |
                     | (DB)   |    | Filesystem|
                     +--------+    | (ZIPs)    |
                                   +-----------+
                                        |
                                        v
                        +-------------------------------+
                        |        Google Cloud           |
                        |                               |
                        |  Cloud Build  --> Artifact    |
                        |  (build img)     Registry     |
                        |                    |          |
                        |                    v          |
                        |  Terraform --> Cloud Run      |
                        |  (IaC)       (serve site)     |
                        |                               |
                        |  GCS Bucket                   |
                        |  (Terraform state)            |
                        +-------------------------------+
```

---

## Frontend

**Stack:** React 19, Vite 7, TypeScript 5.9 (strict mode)

The entire UI is driven by a **state machine** in `App.tsx` with five phases:

```
upload  -->  checking  -->  results  -->  deploying  -->  deployed
                              |
                              +--> (user uploads another)
```

| Component          | Role                                             |
|--------------------|--------------------------------------------------|
| `DropZone`         | Drag-and-drop / file picker, validates `.zip`    |
| `UploadProgress`   | Spinner showing 3 concurrent AI checks           |
| `CheckResults`     | Displays security / cost / brand verdicts         |
| `DeployButton`     | Mode selector (Demo 1h / Production)              |
| `DeploymentList`   | Table of all deployments, polled every 10s        |
| `DeploymentCard`   | Single deployment row with status + actions        |
| `StatusBadge`      | Colored badge for pass/warn/fail/deployed/expired  |

**API layer:** `api.ts` provides typed fetch wrappers (`uploadZip`, `deployProject`, `listDeployments`, `deleteDeployment`). All calls go to `/api/*`, proxied to `:8000` by Vite in dev.

---

## Backend

**Stack:** FastAPI, Uvicorn, aiosqlite, Anthropic SDK, Pydantic v2

### Routers

| Endpoint                               | Method | Description                          |
|----------------------------------------|--------|--------------------------------------|
| `/api/upload`                          | POST   | Accept ZIP, validate, run AI checks  |
| `/api/deployments`                     | GET    | List all deployments                 |
| `/api/deployments/{id}`               | GET    | Get single deployment                |
| `/api/deployments/{id}/deploy`        | POST   | Build container + deploy to Cloud Run|
| `/api/deployments/{id}`               | DELETE | Teardown infra + delete record       |
| `/api/health`                          | GET    | Health check                         |

### Services

| Service            | File                        | Responsibility                                                 |
|--------------------|-----------------------------|----------------------------------------------------------------|
| ZIP Handler        | `services/zip_handler.py`   | Validates ZIP (50MB limit, allowed extensions, needs `index.html`), extracts to local dir |
| AI Analyzer        | `services/ai_analyzer.py`   | Runs 3 checks concurrently via `asyncio.gather` using Claude Sonnet |
| Deployer           | `services/deployer.py`      | Generates Dockerfile, builds via Cloud Build, applies Terraform |
| Cleanup            | `services/cleanup.py`       | Background loop (60s) that expires demo deployments after 1h   |

### AI Checks (3 concurrent)

Each check calls the Anthropic API with a specialized system prompt and returns `{status, summary, details[]}`.

| Check      | Prompt file         | What it evaluates                                        | Blocks deploy? |
|------------|---------------------|----------------------------------------------------------|----------------|
| Security   | `prompts/security.py` | XSS, secrets, eval/Function, suspicious external scripts | Yes (if `fail`) |
| Cost       | `prompts/cost.py`     | Estimated Cloud Run hosting cost from file metadata       | No              |
| Brand      | `prompts/brand.py`    | Transcom brand alignment (colors, fonts, professionalism) | No              |

**Fallback policy:** If any AI check throws an error, it returns `warn` — it never blocks on AI failure.

### Database

SQLite via `aiosqlite`. Single table `deployments`:

| Column             | Type    | Notes                                           |
|--------------------|---------|-------------------------------------------------|
| `id`               | TEXT PK | 16-char hex UUID                                |
| `name`             | TEXT    | ZIP filename (without extension)                |
| `status`           | TEXT    | `pending → checked → deploying → deployed → expired / failed` |
| `mode`             | TEXT    | `demo` or `prod`                                |
| `security_status`  | TEXT    | `pass`, `warn`, or `fail`                       |
| `cost_status`      | TEXT    | `pass`, `warn`, or `fail`                       |
| `brand_status`     | TEXT    | `pass`, `warn`, or `fail`                       |
| `cloud_run_url`    | TEXT    | Live URL once deployed                          |
| `expires_at`       | TEXT    | ISO timestamp, only for demo mode               |

---

## Infrastructure (GCP)

### Cloud Build

The deployer generates a minimal Dockerfile on-the-fly:

```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html/
EXPOSE 80
```

Then runs `gcloud builds submit --tag <image_url>` to build + push to Artifact Registry.

### Terraform

```
terraform/
  main.tf           # Calls the airlock-deployment module
  variables.tf      # project_id, region, deployment_id, image_url, mode
  providers.tf      # Google provider ~5.0, Terraform >= 1.5.0
  backend.tf        # GCS backend, prefix "airlock"
  modules/
    airlock-deployment/
      main.tf       # Cloud Run v2 service + public IAM binding
```

**Isolation model:** Each deployment gets its own Terraform workspace (`airlock-{id[:12]}`), with state stored in a GCS bucket (`{project}-airlock-tf-state`).

**Cloud Run config:**
- Scale-to-zero (min: 0, max: 2 instances)
- 512 MB memory
- Port 80
- Public access via `allUsers` IAM binding

### GCP Services Used

| Service             | Purpose                                      |
|---------------------|----------------------------------------------|
| Cloud Build         | Build container images from user ZIPs        |
| Artifact Registry   | Store container images                       |
| Cloud Run v2        | Serve deployed frontends (scale-to-zero)     |
| GCS                 | Terraform remote state storage               |

---

## Key Configuration

All config is in `backend/app/config.py` via Pydantic Settings:

| Variable                   | Default             | Source          |
|----------------------------|---------------------|-----------------|
| `ANTHROPIC_API_KEY`        | (required)          | `.env`          |
| `GCP_PROJECT_ID`           | auto-detected       | `gcloud` CLI    |
| `GCP_REGION`               | `europe-north1`     | `.env`          |
| `demo_ttl_seconds`         | `3600` (1 hour)     | hardcoded       |
| `cleanup_interval_seconds` | `60`                | hardcoded       |
