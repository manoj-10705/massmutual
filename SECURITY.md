# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 2.x | ✅ Active |
| 1.x | ❌ End of life |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** create a public GitHub issue
2. Email: security@massmutual-project.local
3. Include: description, reproduction steps, potential impact
4. We will respond within 48 hours

## Security Practices

### Secrets Management

- All secrets are managed via environment variables (`.env` file)
- `.env` is listed in `.gitignore` — never committed
- Pre-commit hooks scan for leaked secrets (gitleaks)
- No hardcoded passwords in source code
- All Python config uses `os.getenv()` with fail-fast pattern

### API Security

- Optional API key authentication (`X-API-Key` header)
- Rate limiting: 200 req/min global, 20 req/min for AI queries
- CORS restrictions via `flask-cors`
- Input validation on all endpoints
- SQL injection prevention via parameterized queries and `psycopg2.sql`

### AI Safety

- AI-generated SQL is validated before execution (SELECT only)
- Dangerous SQL keywords are blocked (INSERT, UPDATE, DELETE, DROP, etc.)
- Query execution timeout: 10 seconds
- All AI queries logged to `ai_query_log` for audit

### Container Security

- All application containers run as non-root users
- `.dockerignore` files prevent secrets from leaking into images
- Docker resource limits prevent container resource exhaustion
- Network isolation: data-plane and front-plane separation

### Data Protection

- Redis authentication enabled (`requirepass`)
- Redis persistence (`appendonly`) prevents data loss
- PostgreSQL role-based access control
- Separate database instances for application and Airflow metadata

## Dependencies

We use pinned dependencies to prevent supply chain attacks:
- `requirements.txt` files pin exact versions
- GitHub Actions CI validates Docker builds on every push
