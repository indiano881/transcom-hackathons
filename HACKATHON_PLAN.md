# Hackathon Brainstorm: "Innovation Airlock"

## Context

Transcom hackathon (~2 weeks). Non-engineers (Sales/Solutions) "vibe code" HTML widgets with AI tools (Gemini, Canvas, Lovable) but have no way to deploy/share them. They're stuck on localhost. We build the bridge: **drag-and-drop HTML file → live shareable URL on GCP**, with AI-powered security scanning and auto-containerization.

**Target persona:** The Visualizer (Sales rep who made an HTML dashboard, needs a link for the client)
**Deliverable:** Working end-to-end prototype
**AI budget:** $50 OpenRouter API key

---

## Architecture Overview

```
  User (Sales Rep)
       │
       │  drag & drop HTML file(s)
       ▼
┌─────────────────────────┐
│     Web UI (React)      │  ← Hosted on Cloud Run
│  - Upload zone          │
│  - Security report      │
│  - Deployment history   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   Backend API (Python)  │  ← Hosted on Cloud Run
│                         │
│  1. Receive files       │
│  2. AI Analyze          │──→ OpenRouter (Claude/GPT)
│  3. Security scan       │    - Detect artifact type
│  4. Generate Dockerfile │    - Find hardcoded secrets
│  5. Build container     │    - Security vulnerabilities
│  6. Deploy via IaC      │    - Generate security report
│  7. Return live URL     │
└──────────┬──────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
┌─────────┐  ┌──────────────┐
│ Cloud   │  │  Deployment  │
│ Build   │  │  Engine      │
│ + AR    │  │ (Terraform)  │
└─────────┘  └──────┬───────┘
                    │
                    ▼
            ┌──────────────┐
            │  Cloud Run   │  ← nginx serving the HTML
            │  Service     │
            │              │
            │  → Live URL  │
            └──────────────┘
```

---

## Key Design Decisions (DECIDED)

### 1. Deployment engine: Pure Terraform

Full Terraform pipeline. Backend generates `.tf` files dynamically and runs `terraform apply`.
- Terraform manages everything: Artifact Registry, Cloud Build trigger, Cloud Run service
- State per deployment using Terraform workspaces (backed by GCS)
- Enterprise-grade: every deployment is auditable, version-controlled, destroyable via `terraform destroy`
- This IS the differentiator — "every vibe-coded artifact gets proper IaC, automatically"

**State management approach:** One GCS bucket, one workspace per deployment.
```
gs://airlock-tf-state/
  ├── airlock-sarah-a1b2c3/    # workspace per deployment
  ├── airlock-john-d4e5f6/
  └── ...
```

### 2. Frontend: React vs Streamlit

**React:** More polished demo, drag-and-drop feels native, shows product thinking
**Streamlit:** Faster to build, but looks like a data tool, less "product"

Recommendation: **React** (or even a Vite + vanilla JS app) — the drag-and-drop UX IS the demo.

### 3. Container strategy for HTML files

Dead simple: `FROM nginx:alpine` + `COPY files /usr/share/nginx/html/`
AI generates this Dockerfile, but for static HTML it's always the same pattern.

### 4. Google Workspace angle (stretch goal)

- Google Chat bot: "@airlock deploy" with file attachment
- Google Drive: upload to magic folder → auto-deploy
- Either would be a killer demo differentiator

---

## Component Breakdown

### Component 1: Web UI
- **Tech:** React + Vite (or Next.js)
- **Features:**
  - Drag-and-drop upload zone
  - Real-time deployment status (websocket or polling)
  - Security scan results display
  - Deployment history with URLs
  - Simple auth (Google OAuth — Workspace-native)
- **Effort:** 2-3 days

### Component 2: Backend API
- **Tech:** Python FastAPI
- **Endpoints:**
  - `POST /upload` — receive files, trigger pipeline
  - `GET /deployments` — list all deployments
  - `GET /deployments/{id}` — status + URL
  - `GET /deployments/{id}/security-report` — AI scan results
- **Effort:** 2-3 days

### Component 3: AI Analyzer
- **Tech:** OpenRouter API (Claude or GPT-4)
- **Responsibilities:**
  - **Type detection:** "This is a static HTML page with embedded Chart.js"
  - **Security scan:** Check for hardcoded secrets, XSS vulnerabilities, external script loading, suspicious patterns
  - **Dependency analysis:** What external resources does it load? CDN scripts?
  - **Generate report:** Human-readable security assessment
  - **Generate Dockerfile:** Appropriate for the artifact type
- **Prompt engineering** is the key here — build good system prompts for analysis
- **Effort:** 1-2 days

### Component 4: Pure Terraform Deployment Pipeline
- **Terraform module** `modules/airlock-deployment/` manages the full lifecycle:
  - `google_artifact_registry_repository` — per-deployment image repo
  - `null_resource` with `local-exec` — triggers `docker build` + `docker push` (or Cloud Build)
  - `google_cloud_run_v2_service` — the deployed service
  - `google_cloud_run_service_iam_member` — public access (allUsers invoker)
- **Backend generates:** `main.tf` + `terraform.tfvars` per deployment, runs in isolated workspace
- **Naming:** `airlock-{username}-{short-hash}` → URL: `airlock-sarah-a1b2c3-xxx.run.app`
- **Teardown:** `terraform destroy` on the workspace removes everything cleanly
- **Effort:** 2-3 days (Davide's primary task)

### Component 5: Audit Trail / Admin View (stretch)
- Simple dashboard showing all deployments
- Who deployed what, when, security scan results
- Ability to tear down deployments
- **Effort:** 1 day

---

## Suggested Team Task Split

Given the team (Davide=infra, Xiaoliang=backend, Rasmus=AI/agents, Natalia+Qi=ML/Python, Riyad=data/ML, Aron+Jakob=business):

| Person | Component | Why |
|--------|-----------|-----|
| Davide | Terraform modules + GCP pipeline (build/deploy) | IaC expertise |
| Xiaoliang | Backend API (FastAPI) + frontend | Full-stack skills |
| Rasmus | AI analyzer prompts + agent orchestration | AI/agent expertise |
| Natalia/Qi | Security scanning logic + testing | Python + ML |
| Riyad | Data pipeline for audit trail + metrics | Data engineering |
| Aron/Jakob | Product requirements, demo script, presentation | Business context |

---

## Demo Script (2 min)

1. **The Problem** (30s): "Sarah from Sales built an HTML dashboard with Gemini. It's amazing. But it's stuck on her laptop."
2. **The Solution** (15s): "Innovation Airlock: drag, scan, deploy."
3. **Live Demo** (60s):
   - Drag HTML file into the UI
   - AI scans it: "Static HTML, Chart.js, no security issues, safe to deploy"
   - Click "Deploy"
   - 30 seconds later: live URL appears
   - Open the URL on phone → it works
4. **Enterprise Value** (15s): "Full audit trail. Security scanning. IaC-backed. Zero shadow IT."

---

## Repo Structure

```
innovation-airlock/
├── frontend/                 # React + Vite
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── DropZone.tsx
│   │   │   ├── SecurityReport.tsx
│   │   │   └── DeploymentList.tsx
│   │   └── api.ts
│   ├── package.json
│   └── Dockerfile
├── backend/                  # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── upload.py
│   │   │   └── deployments.py
│   │   ├── services/
│   │   │   ├── analyzer.py        # AI code analysis via OpenRouter
│   │   │   ├── builder.py         # Cloud Build orchestration
│   │   │   ├── deployer.py        # Terraform apply
│   │   │   └── storage.py         # GCS for uploaded files
│   │   └── models.py
│   ├── templates/
│   │   ├── Dockerfile.static      # nginx template for HTML
│   │   ├── Dockerfile.python      # python template (stretch)
│   │   └── Dockerfile.node        # node template (stretch)
│   ├── requirements.txt
│   └── Dockerfile
├── terraform/
│   ├── modules/
│   │   └── airlock-deployment/    # Reusable module for each deployment
│   │       ├── main.tf            # Cloud Run service
│   │       ├── variables.tf
│   │       └── outputs.tf
│   └── state/                     # State management config
│       └── backend.tf
├── sample-artifacts/              # Demo HTML files for testing
│   ├── sales-dashboard.html
│   └── product-comparison.html
└── README.md
```

---

## Risk / Open Questions

1. **Terraform + Docker build speed:** `terraform apply` + container build might take 2-5 min. For demo: pre-warm a deployment, show the result instantly, then show the pipeline running for a second one.
2. **Terraform state:** DECIDED — GCS backend with workspaces per deployment. Need to set up the state bucket in the new GCP project first.
3. **Cost:** Cloud Run scales to zero. Add TTL labels + a cleanup cron that runs `terraform destroy` on expired workspaces.
4. **Auth:** For hackathon, skip real auth or use simple Google OAuth (since it's a Google Workspace house).
5. **Scope:** Only The Visualizer (HTML → URL). No Python/Node apps, no API key injection.
6. **New GCP project:** Need to set up: enable APIs (Cloud Run, Cloud Build, Artifact Registry, Secret Manager), create state bucket, set up service accounts.
7. **Team coordination:** Davide remote from Italy — async-friendly, clear interfaces between components.

---

## Terraform Module Design (Core Differentiator)

The `airlock-deployment` module is the heart of the system. Each user deployment gets its own Terraform workspace with this module:

```hcl
# modules/airlock-deployment/variables.tf
variable "project_id" {}
variable "region" { default = "europe-north1" }
variable "deployment_name" {}        # e.g., "airlock-sarah-a1b2c3"
variable "image_tag" {}              # container image tag
variable "creator_email" {}          # who deployed this
variable "security_scan_status" {}   # "passed" | "warning" | "failed"
variable "artifact_type" {}          # "static-html" | "python" | "node"
variable "ttl_hours" { default = 72 } # auto-cleanup after N hours

# modules/airlock-deployment/main.tf
resource "google_cloud_run_v2_service" "deployment" {
  name     = var.deployment_name
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/airlock/${var.deployment_name}:${var.image_tag}"
      resources {
        limits = { memory = "256Mi", cpu = "1" }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2  # cost control
    }
  }

  labels = {
    managed-by     = "airlock"
    creator        = replace(var.creator_email, "@", "-at-")
    security-scan  = var.security_scan_status
    artifact-type  = var.artifact_type
  }
}

# Public access (for shareable URLs)
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.deployment.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# modules/airlock-deployment/outputs.tf
output "url" {
  value = google_cloud_run_v2_service.deployment.uri
}
output "deployment_name" {
  value = var.deployment_name
}
```

**Backend orchestration flow:**
```python
# deployer.py (pseudocode)
def deploy(artifact_id, files, scan_result, user_email):
    workspace = f"airlock-{user_email.split('@')[0]}-{artifact_id[:6]}"

    # 1. Build container image
    build_container(files, workspace)  # docker build + push to AR

    # 2. Generate tfvars
    write_tfvars(workspace, {
        "deployment_name": workspace,
        "image_tag": "latest",
        "creator_email": user_email,
        "security_scan_status": scan_result.status,
        "artifact_type": scan_result.type,
    })

    # 3. Terraform apply in isolated workspace
    run(f"terraform workspace select -or-create {workspace}")
    run(f"terraform apply -auto-approve -var-file={workspace}.tfvars")

    # 4. Capture URL from output
    url = run("terraform output -raw url")
    return url
```

---

## Proposed Sprint Plan (2 weeks)

### Week 1: Foundation
- **Day 1-2:** Set up repo, GCP project, Terraform modules, basic backend API
- **Day 3-4:** AI analyzer integration, Dockerfile generation, Cloud Build pipeline
- **Day 5:** Frontend drag-and-drop UI, connect to backend

### Week 2: Integration + Polish
- **Day 6-7:** End-to-end flow working (upload → deploy → URL)
- **Day 8-9:** Security report UI, deployment history, polish
- **Day 10:** Demo prep, presentation, edge case handling
