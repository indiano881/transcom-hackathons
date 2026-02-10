# Innovation Airlock — User & System Flow

## End-to-End Flow at a Glance

```
  User drops ZIP           AI checks run           User picks mode         Site goes live
       |                       |                        |                       |
  [ UPLOAD ] ──> [ CHECKING ] ──> [ RESULTS ] ──> [ DEPLOYING ] ──> [ DEPLOYED ]
                                      |                                     |
                                      |                              (demo: auto-expires
                                      |                               after 1 hour)
                                      v
                              Security fail? ──> BLOCKED (403)
```

---

## Phase 1 — Upload

**What the user does:** Drags a `.zip` file onto the drop zone (or clicks to browse).

**What the system does:**

```
1. Frontend validates file extension (.zip)
2. POST /api/upload  (multipart form data)
3. Backend saves ZIP to temp file
4. zip_handler.py validates:
   ├── File size ≤ 50 MB
   ├── Extracted size ≤ 100 MB
   ├── No path traversal (../ in filenames)
   ├── Only allowed extensions (html, css, js, json, images, fonts, etc.)
   └── index.html exists (at root or 1 level deep)
5. Extracts to  backend/deployments/{deployment_id}/
```

**If validation fails:** 400 error returned, user sees error message, stays on upload screen.

---

## Phase 2 — AI Checks (Concurrent)

**What the user sees:** A progress spinner with three steps running simultaneously.

**What the system does:**

```
asyncio.gather (all 3 run in parallel)
  │
  ├── Security Check
  │   Sends all text files to Claude with security prompt
  │   Looks for: XSS, hardcoded secrets, eval(), suspicious external scripts
  │   Returns: pass | warn | fail
  │
  ├── Cost Forecast
  │   Sends file metadata (sizes, counts) to Claude with cost prompt
  │   Estimates: monthly Cloud Run hosting cost
  │   Returns: pass | warn | fail
  │
  └── Brand Validation
      Sends all text files to Claude with brand prompt
      Checks: Transcom colors, IBM Plex Sans font, professionalism
      Returns: pass | warn | fail
```

**AI Model:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`), max 1024 tokens per check.

**Error handling:** If any check throws an exception, it returns `warn` with a message that the check could not complete. The system never blocks a deployment because the AI was unavailable.

**After all 3 complete:**
- Results stored in SQLite
- Deployment status set to `checked`
- Response sent to frontend

---

## Phase 3 — Results & Decision

**What the user sees:** Three result cards (Security, Cost, Brand) each showing pass/warn/fail with details.

**Decision logic:**

```
Security = fail?
  ├── YES → Deploy button is DISABLED
  │         User must fix issues and re-upload
  │
  └── NO → Deploy button is ENABLED
            User picks deployment mode:
              ├── Demo  (auto-expires in 1 hour)
              └── Prod  (persists until manually deleted)
```

**Only security `fail` blocks deployment.** Cost and brand warnings are advisory only.

---

## Phase 4 — Deploying

**What the user sees:** A deploying spinner.

**What the system does:**

```
POST /api/deployments/{id}/deploy  { mode: "demo" | "prod" }

Step 1: Build Container Image
  ├── Generate Dockerfile (nginx:alpine + static files)
  ├── gcloud builds submit --tag {region}-docker.pkg.dev/{project}/{repo}/{id}:latest
  └── Image pushed to Artifact Registry

Step 2: Terraform Apply
  ├── terraform init -backend-config=bucket={project}-airlock-tf-state
  ├── terraform workspace new airlock-{id[:12]}  (or select if exists)
  └── terraform apply -auto-approve
        -var project_id=...
        -var deployment_id=...
        -var image_url=...
        -var mode=demo|prod

Step 3: Get Cloud Run URL
  └── terraform output -json service_url

Step 4: Update Database
  ├── status = "deployed"
  ├── cloud_run_url = <the live URL>
  ├── deployed_at = now
  └── expires_at = now + 1h  (demo only)
```

**If any step fails:** Deployment status set to `failed`, error returned to frontend.

---

## Phase 5 — Deployed

**What the user sees:**
- Success message
- Deployment appears in the history table with a clickable live URL
- "Deploy another" button to start over

**Cloud Run service config:**
- nginx:alpine serving static files on port 80
- Scale-to-zero (0–2 instances)
- 512 MB memory
- Public access (no auth required)

---

## Lifecycle Management

### Demo Auto-Expiry

```
Background cleanup loop (runs every 60 seconds)
  │
  └── Query: SELECT id FROM deployments
              WHERE expires_at < NOW
              AND status = 'deployed'
       │
       For each expired deployment:
         ├── terraform destroy (tear down Cloud Run service)
         ├── Delete local files (backend/deployments/{id}/)
         └── Update DB: status = 'expired'
```

### Manual Teardown

```
DELETE /api/deployments/{id}
  │
  ├── If status = 'deployed':
  │     └── terraform destroy (best effort)
  │
  ├── Delete local files
  └── DELETE FROM deployments WHERE id = ?
```

---

## Deployment Status State Machine

```
                           upload & AI checks
                                  │
                                  v
  ┌─────────┐   validate   ┌──────────┐   deploy    ┌───────────┐
  │ pending  │ ──────────>  │ checked  │ ─────────>  │ deploying │
  └─────────┘              └──────────┘              └───────────┘
                                                      │         │
                                                      v         v
                                                ┌──────────┐ ┌────────┐
                                                │ deployed │ │ failed │
                                                └──────────┘ └────────┘
                                                      │
                                          (demo TTL expires)
                                                      │
                                                      v
                                                ┌──────────┐
                                                │ expired  │
                                                └──────────┘
```

---

## API Reference (Quick)

| Endpoint                          | Method | Body                  | Returns              |
|-----------------------------------|--------|-----------------------|----------------------|
| `/api/upload`                     | POST   | ZIP file (multipart)  | AI check results + deployment_id |
| `/api/deployments`               | GET    | —                     | List of all deployments |
| `/api/deployments/{id}`          | GET    | —                     | Single deployment    |
| `/api/deployments/{id}/deploy`   | POST   | `{ mode: "demo" }`   | Cloud Run URL        |
| `/api/deployments/{id}`          | DELETE | —                     | Confirmation         |
| `/api/health`                    | GET    | —                     | `{ status: "ok" }`  |

---

## Security Model

| Layer             | Control                                                       |
|-------------------|---------------------------------------------------------------|
| Upload validation | File size limits, extension whitelist, path traversal blocked |
| AI security scan  | Claude analyzes all text files for XSS, secrets, eval, etc.  |
| Deploy gate       | Security `fail` = hard block (HTTP 403)                       |
| AI fault tolerance| AI errors fall back to `warn`, never block                    |
| Infrastructure    | Each deployment isolated in its own Terraform workspace       |
