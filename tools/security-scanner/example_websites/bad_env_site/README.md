# bad_env_site

Intentionally insecure static sample with leaked environment values.

## Expected findings
- Hard-coded secrets in `.env.local`
- `eval` usage
- External network call
- Missing integrity for external script tag
