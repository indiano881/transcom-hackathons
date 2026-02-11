# Test Websites For Security Scanner

These sample sites are intentionally vulnerable for scanner testing only.
Do not deploy them.

## Included Targets

1. `bad_shop_frontend`
- Frontend-only sample
- Includes: hard-coded secret, XSS via `innerHTML`, external `fetch`, sensitive logging

2. `bad_node_admin`
- Node/Express sample
- Includes: `eval`, shell execution, string-built SQL query, hard-coded token, external network call

3. `bad_python_portal`
- Flask sample
- Includes: `DEBUG=True`, f-string SQL query, `subprocess` shell call, `pickle.loads`, hard-coded secret

4. `bad_env_site`
- Static sample with environment leak
- Includes: `.env.local` secret, `eval`, external script without integrity

## Suggested Quick Test

Run from `tools/security-scanner`:

```bash
python3 scan.py --path ./example_websites/bad_shop_frontend --out ./reports/bad-shop.json --enable-semgrep --enable-gitleaks --enable-ai-gate --policy-mode demo --verbose
```
