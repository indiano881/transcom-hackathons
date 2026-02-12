# Security Scanner

## Introduction
This project is a local-first static security scanner for source code (SAST-style first pass) focused on web app inputs such as HTML, JavaScript, TypeScript, and common backend files.

It performs:
- Rule-based scanning using configurable regex rules (`rules.json`)
- Optional Semgrep scanning (`--enable-semgrep`)
- Optional Gitleaks secret scanning (`--enable-gitleaks`)
- Optional AI policy gate fusion (`--enable-ai-gate`, default policy mode: `demo`)
- Unified JSON reporting for downstream review/automation

The scanner does **not** execute target code.

## Current Layout
- `scan.py`: scanner CLI entrypoint
- `rules.json`: local regex rules
- `reports/`: output reports
- `example_websites/`: sample scan targets

## Requirements
- Python 3.9+
- Optional (only if enabled):
  - `semgrep` binary in PATH
  - `gitleaks` binary in PATH
  - OpenRouter API key in environment variable (default: `OPENROUTER_API_KEY`)

## Install Optional Engines
Semgrep and Gitleaks are not both "just Python packages":
- Semgrep: can be installed via Homebrew or pip/pipx
- Gitleaks: typically installed as a standalone binary (for example via Homebrew)

Recommended on macOS:

```bash
brew install semgrep gitleaks
```

Alternative for Semgrep:

```bash
python3 -m pip install semgrep
```

Verify installation:

```bash
semgrep --version
gitleaks version
```

Set API key for AI gate (only needed when `--enable-ai-gate`):

```bash
export OPENROUTER_API_KEY=\"<your_key>\"
```

## Quick Start
Run local regex scanning:

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report.json
```

Verbose mode (prints checked files):

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report.json \
  --verbose
```

Enable Semgrep + Gitleaks:

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report-all-engines.json \
  --enable-semgrep \
  --enable-gitleaks
```

Enable AI gate (Demo mode, default):

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report-ai-demo.json \
  --enable-ai-gate
```

Enable AI gate and print exact payload sent to AI:

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report-ai-demo.json \
  --enable-ai-gate \
  --verbose \
  --ai-log-payload
```

Enable AI gate in Strict mode:

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report-ai-strict.json \
  --enable-ai-gate \
  --policy-mode strict
```

Use custom Semgrep configs (default is `auto` if not specified):

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --out ./reports/report-semgrep.json \
  --enable-semgrep \
  --semgrep-config p/default
```

Use custom local rules file:

```bash
python3 scan.py \
  --path ./example_websites/learning_swedish \
  --rules ./rules.json \
  --out ./reports/report-custom-rules.json
```

## CLI Options
- `--path` (required): directory to scan recursively
- `--out` (required): output JSON report path
- `--max-file-kb`: max file size to scan, default `512`
- `--rules`: optional path to `rules.json`
- `--verbose`: print scan progress and file-by-file checks
- `--enable-semgrep`: include Semgrep findings
- `--semgrep-bin`: Semgrep executable path/name (default `semgrep`)
- `--semgrep-config`: repeatable Semgrep config selector/path (default: `auto`)
- `--enable-gitleaks`: include Gitleaks findings
- `--gitleaks-bin`: Gitleaks executable path/name (default `gitleaks`)
- `--gitleaks-config`: optional `.gitleaks.toml` path
- `--enable-ai-gate`: enable AI policy analysis and fusion decision
- `--policy-mode`: `demo | strict` (default: `demo`)
- `--ai-provider`: AI provider (currently `openrouter`)
- `--ai-model`: model name (default: `openai/gpt-4o-mini`)
- `--ai-base-url`: chat completion endpoint URL
- `--ai-credits-url`: credits endpoint URL for balance lookup
- `--ai-api-key-env`: API key env var name (default: `OPENROUTER_API_KEY`)
- `--ai-timeout-sec`: AI request timeout in seconds
- `--ai-max-findings`: max findings sent to AI
- `--ai-context-lines`: source context lines before/after each finding sent to AI (default: `8`)
- `--ai-redact-input` / `--no-ai-redact-input`: redact sensitive values in AI input (default: enabled)
- `--ai-log-payload`: print full request payload sent to AI (stderr)
- `--ai-policy-file`: optional custom policy markdown file

## Report Output
The scanner writes a JSON report with these top-level fields:
- `risk_level`: `Low | Medium | High`
- `recommendation`: `Auto-Deploy | Manual Review Required | Deployment Blocked`
- `rule_findings`: normalized findings list
- `ai_analysis`: summary block for downstream AI review
- `limitations`: scanner limitations
- `metadata`: scan stats and engine statuses
- `ai_gate`: policy-mode fusion output (enabled/disabled state, decision path, overrides)

Each finding contains:
- `rule_id`
- `category`
- `severity`
- `file`
- `line`
- `evidence`
- `description`
- `source_engine` (`local-regex`, `semgrep`, or `gitleaks`)
- `external_rule_id` (when provided by external engines)

`metadata.engines` includes per-engine status (`ok`, `skipped`, `error`) and engine-specific details.
If AI gate is enabled, `risk_level` and `recommendation` are set from `ai_gate.fusion_decision.compat_recommendation`.

`ai_gate.input_redaction` records redaction stats used for AI input payload.
When AI is called, the scanner also records `metadata.ai_api.usage` (cost/tokens) and `metadata.ai_api.credits` (balance snapshot).

## Custom Rule Format (`rules.json`)
`rules.json` expects:

```json
{
  "rules": [
    {
      "rule_id": "SEC001",
      "category": "Secrets",
      "severity": "High",
      "description": "Hard-coded API key or token-like secret.",
      "patterns": ["regex1", "regex2"]
    }
  ]
}
```

Validation rules:
- `severity` must be one of `Low`, `Medium`, `High`
- `patterns` must be a non-empty list of valid regex strings

## Notes
- This is static analysis only; false positives/negatives are expected.
- If Semgrep/Gitleaks are enabled but not installed, the scan still completes, prints a clear warning in CLI output, and records errors under `metadata.engines` (plus `metadata.warnings`).
- If AI gate is enabled but API key/provider/policy fails, the scan still completes and records warning details; in `strict` mode AI failure escalates to at least `Manual Review Required`.
- By default, sensitive values are redacted before sending findings to AI. Detection uses finding context (Secrets/Gitleaks) plus regex patterns (API keys, tokens, bearer headers, password/secret assignments).
- AI input uses `finding + minimal source context snippet` (default: ±8 lines around each finding), not full project source.
- If `--ai-log-payload` is enabled, the full AI request body is printed to terminal; avoid this in shared terminals. Keep redaction enabled unless you explicitly need raw payload debugging.
- By default, after an AI call the scanner prints usage (including cost when available) and credits/balance information to stderr.

## Maintenance
When scanner flags/output/schema are changed in `scan.py`, update this README in the same change so usage instructions and examples stay accurate.
