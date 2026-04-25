# Contributing to MassMutual Financial Pipeline

Thank you for contributing! Please follow these guidelines.

## Development Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd MassMutual

# 2. Set up Python environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r frontend/requirements.txt
pip install pytest pytest-cov ruff black pre-commit

# 3. Install pre-commit hooks
pre-commit install

# 4. Create .env file
cp .env.example .env
# Edit with your API keys
```

## Code Standards

### Python

- **Formatter:** Black (line length 120)
- **Linter:** Ruff
- **Type hints:** Required on all new functions
- **Docstrings:** Required on all classes and public functions
- **Naming:** `snake_case` for variables/functions, `PascalCase` for classes

### SQL

- **Keywords:** UPPERCASE (`SELECT`, `FROM`, `WHERE`)
- **Table names:** `snake_case` with prefix (`dim_`, `fact_`, `kpi_`)
- **Parameterized queries:** Always use `%s` placeholders, never f-strings
- **Dynamic identifiers:** Use `psycopg2.sql.Identifier`

### JavaScript

- **Style:** ES6+ (const/let, arrow functions, template literals)
- **No inline JS:** All JavaScript in `/static/js/`

### CSS

- **Custom Properties:** Use `var(--token)` from design system
- **No magic numbers:** All values via CSS custom properties
- **Mobile-first:** Responsive with `min-width` breakpoints

## Branch Strategy

```
main          ← production-ready code
  └── develop ← integration branch
       └── feature/xxx  ← feature branches
       └── fix/xxx      ← bug fixes
```

## Pull Request Checklist

- [ ] Tests pass: `pytest tests/unit -v`
- [ ] Lint passes: `ruff check .`
- [ ] Format passes: `black --check .`
- [ ] No hardcoded secrets or passwords
- [ ] Type hints on new functions
- [ ] Docstrings on new classes/functions
- [ ] `.env.example` updated if new env vars added
- [ ] README updated if user-facing changes
