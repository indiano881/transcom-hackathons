# Gemini Chat Integration — Implementation Plan

## Vision

Add a built-in Gemini chat to Innovation Airlock so users can go from **prompt to live site** without leaving the app. The full loop:

```
User types prompt
      ↓
Gemini generates HTML/CSS/JS
      ↓
AI checks (security, cost, brand) run automatically
      ↓
If check fails → auto-feed failure back to Gemini → regenerate
      ↓
User previews the result
      ↓
One-click deploy to Cloud Run
      ↓
User can iterate: "change the header color" → regenerate → redeploy
```

---

## Phase 1 — Backend: Gemini Chat Service

### New dependency
```
google-genai >= 1.0.0
```

### New file: `backend/app/services/gemini_chat.py`

Uses the **Google Gen AI SDK** (not the deprecated `vertexai` SDK) to call Gemini via Vertex AI:

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project=settings.gcp_project_id,
    location=settings.gcp_region,
)
```

**Model choice:** `gemini-2.5-flash` — 15x cheaper than Pro, 400-700ms latency, great for code generation. Can upgrade to Pro for complex requests later.

**System prompt** is the key to quality. It should instruct Gemini to:
- Always output a **complete, self-contained HTML file** (inline CSS + JS) unless the user specifically asks for separate files
- Follow Transcom brand guidelines (colors, fonts) by default
- Never include external scripts from untrusted CDNs
- Never use eval(), inline event handlers with user data, or hardcoded secrets
- Structure output as JSON: `{ "files": [{ "name": "index.html", "content": "..." }, ...] }`

**Structured output** — use Gemini's JSON mode with a Pydantic schema to guarantee parseable output:
```python
class GeneratedFile(BaseModel):
    name: str
    content: str

class GenerationResult(BaseModel):
    files: list[GeneratedFile]
    explanation: str
```

**Conversation history** — maintain chat history per session so users can iterate ("make the button bigger", "add a contact form"). Store in-memory (dict keyed by session/deployment ID). No need for DB persistence — conversations are ephemeral.

**Streaming** — Gemini supports streaming responses. Use SSE (Server-Sent Events) to stream the response to the frontend for a real-time chat feel.

### New file: `backend/app/routers/generate.py`

| Endpoint | Method | Description |
|---|---|---|
| `POST /api/generate` | POST | Send prompt to Gemini, get generated code |
| `POST /api/generate/{id}/iterate` | POST | Send follow-up prompt (uses conversation history) |
| `GET /api/generate/{id}/preview` | GET | Get current generated files for preview |

**`POST /api/generate` flow:**
1. Receive user prompt (text, optionally with image attachments for mockup-to-code)
2. Call Gemini with system prompt + user prompt
3. Parse structured JSON output → extract files
4. Write files to `deployments/{new_id}/`
5. Run AI checks automatically (`run_all_checks()` — existing pipeline)
6. **If security check fails:** auto-feed the failure details back to Gemini as a follow-up message, ask it to fix the issues, repeat (max 2 auto-retries)
7. Return: generated files, check results, deployment ID

**`POST /api/generate/{id}/iterate` flow:**
1. Receive follow-up prompt + deployment ID
2. Load conversation history
3. Call Gemini with history + new prompt
4. Overwrite files in `deployments/{id}/`
5. Re-run AI checks
6. Auto-fix loop if security fails
7. Return updated files + check results

### New file: `backend/app/prompts/generate.py`

System prompt for Gemini code generation. Key sections:
- Role: "You are a web developer creating static websites"
- Brand defaults: Transcom colors, IBM Plex Sans font
- Output format: structured JSON with files array
- Security rules: no eval, no inline handlers, no external untrusted scripts
- Quality: semantic HTML, responsive, accessible
- When user mentions a client brand (e.g. "Pinterest campaign"), use that client's brand instead of Transcom

---

## Phase 2 — Frontend: Chat Interface

### New component: `ChatPanel.tsx`

A chat interface with:
- Message input (textarea with send button)
- Message history display (user messages + Gemini responses)
- Typing indicator while Gemini generates
- Code preview panel showing the generated HTML rendered in an iframe
- "Deploy" button that appears after successful generation

### New component: `CodePreview.tsx`

- Renders generated HTML in a sandboxed `<iframe srcDoc={...}>`
- Toggle between preview and code view
- Shows which files were generated

### Modified: `App.tsx` — New entry path

Add a new initial choice to the state machine:

```
Current:  upload → checking → results → deploying → deployed

New:      choose → (upload path OR generate path)
                    ↓
          generate → chatting → previewing → checking → results → deploying → deployed
```

The landing page gets two cards:
1. **"Upload ZIP"** — existing flow (DropZone)
2. **"Create with AI"** — new flow (ChatPanel)

### Modified: `types.ts` — New types

```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  files?: GeneratedFile[];
  timestamp: string;
}

interface GeneratedFile {
  name: string;
  content: string;
}

interface GenerateResponse {
  deployment_id: string;
  files: GeneratedFile[];
  explanation: string;
  security: CheckResult;
  cost: CheckResult;
  brand: CheckResult;
}
```

### Modified: `api.ts` — New API functions

```typescript
async function generateFromPrompt(prompt: string): Promise<GenerateResponse>
async function iterateGeneration(id: string, prompt: string): Promise<GenerateResponse>
```

### UI Layout for chat mode

```
┌─────────────────────────────────────────────────────┐
│  Innovation Airlock              [Upload] [Create]   │
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│  Chat messages       │   Live Preview (iframe)      │
│  ┌──────────────┐    │   ┌──────────────────────┐   │
│  │ User: make   │    │   │                      │   │
│  │ a landing    │    │   │  [rendered HTML]      │   │
│  │ page for...  │    │   │                      │   │
│  └──────────────┘    │   │                      │   │
│  ┌──────────────┐    │   └──────────────────────┘   │
│  │ AI: Here's   │    │                              │
│  │ your page... │    │   Check Results               │
│  └──────────────┘    │   [Security ✓] [Cost ✓]      │
│                      │   [Brand ✓]                   │
│  ┌──────────────┐    │                              │
│  │ Type message  │    │   [Deploy Demo] [Deploy Prod]│
│  └──────────────┘    │                              │
└──────────────────────┴──────────────────────────────┘
```

---

## Phase 3 — Auto-Fix Loop (the magic)

This is what makes the experience seamless. When AI checks fail:

```
Gemini generates code
      ↓
Security check returns FAIL: "Found inline onclick handler with unsanitized input on line 42"
      ↓
Automatically send to Gemini:
  "The security check found these issues: [details]. Please fix them and regenerate."
      ↓
Gemini regenerates with fixes
      ↓
Re-run checks
      ↓
Pass? → Show to user
Still fail? → Try once more (max 2 auto-retries), then show results with warnings
```

The user might never see a security failure — it just self-heals. Brand and cost warnings are shown but don't block.

---

## Phase 4 — Nice-to-haves (future)

- **Image-to-code**: User uploads a mockup image, Gemini generates HTML that matches it (Gemini supports vision/multimodal input)
- **Template library**: Pre-built prompts like "Landing page", "Dashboard", "Contact form"
- **Version history**: Keep previous iterations, allow rollback
- **Streaming responses**: SSE for real-time token-by-token display in chat

---

## Implementation Order

| Step | What | Files | Effort |
|------|------|-------|--------|
| 1 | Add `google-genai` to requirements.txt | `requirements.txt` | 5 min |
| 2 | Create Gemini system prompt | `backend/app/prompts/generate.py` | 30 min |
| 3 | Create Gemini chat service | `backend/app/services/gemini_chat.py` | 1-2 hrs |
| 4 | Create generate router | `backend/app/routers/generate.py` | 1-2 hrs |
| 5 | Register router in main.py | `backend/app/main.py` | 5 min |
| 6 | Add new types to frontend | `frontend/src/types.ts` | 15 min |
| 7 | Add API functions | `frontend/src/api.ts` | 15 min |
| 8 | Build ChatPanel component | `frontend/src/components/ChatPanel.tsx` | 2-3 hrs |
| 9 | Build CodePreview component | `frontend/src/components/CodePreview.tsx` | 1 hr |
| 10 | Update App.tsx with new flow | `frontend/src/App.tsx` | 1-2 hrs |
| 11 | Add CSS for chat layout | `frontend/src/App.css` | 1 hr |
| 12 | Auto-fix loop in generate router | `backend/app/routers/generate.py` | 1 hr |
| 13 | Test end-to-end | — | 1-2 hrs |

**Total estimate: ~1-2 days of focused work**

---

## Config Changes

New env variables:
- `GOOGLE_CLOUD_PROJECT` — already available via `gcp_project_id`
- `GOOGLE_CLOUD_LOCATION` — already available via `gcp_region`
- No new API key needed if running on GCP (uses ADC). For local dev, `gcloud auth application-default login` is sufficient.

New settings in `config.py`:
```python
gemini_model: str = "gemini-2.5-flash"
gemini_max_tokens: int = 8192  # code generation needs more tokens than checks
gemini_auto_fix_retries: int = 2
```

---

## Key Decisions

1. **Gemini 2.5 Flash over Pro** — 15x cheaper, fast enough for code gen, can upgrade per-request if needed
2. **Structured JSON output** — ensures parseable multi-file responses, no fragile regex parsing
3. **In-memory conversation history** — no DB complexity, conversations are session-scoped
4. **Auto-fix loop** — max 2 retries to avoid infinite loops, then show results as-is
5. **Same deploy pipeline** — generated code goes through the exact same check → deploy flow as uploaded ZIPs
6. **iframe preview** — sandboxed rendering, no XSS risk to our app
