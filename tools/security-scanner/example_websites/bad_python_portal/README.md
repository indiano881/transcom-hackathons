# bad_python_portal

Intentionally insecure Flask sample.

## Expected findings
- Hard-coded secret
- `DEBUG=True`
- SQL injection pattern
- Insecure deserialization (`pickle.loads`)
- Dangerous subprocess usage
