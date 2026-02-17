# Contributing to Finalis Engine API

## Development Setup

```bash
# Clone the repository
git clone https://github.com/DealSyte/commissions-calculator.git
cd commissions-calculator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

# Open in VS Code (recommended)
code .
```

## Development Workflow

### Branch Strategy (Single-Branch)

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code, auto-deploys to staging |
| `feature/*` | New features (branch from main) |
| `fix/*` | Bug fixes (branch from main) |

### Typical Workflow

```bash
# 1. Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. Make changes, linting runs automatically on save

# 3. Commit
git add .
git commit -m "feat: add my feature"

# 4. Push and create PR to main
git push origin feature/my-feature
# → Create PR to main branch
# → CI runs lint + tests automatically

# 5. After merge to main, verify in staging environment

# 6. Tag for production release
git tag v3.1.0
git push origin v3.1.0
```

## Code Quality

### Linting (Ruff)

Linting runs automatically:
- **On save** in VS Code
- **On push** via GitHub Actions

Manual commands:
```bash
ruff check .           # Check for issues
ruff check --fix .     # Auto-fix issues
ruff format .          # Format code
```

### Testing (pytest)

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_lambda_handler.py -v

# Run with coverage
pytest tests/ --cov=engine --cov-report=html
```

### Pre-commit Checks

Before pushing, ensure:
```bash
ruff check .           # ✓ No lint errors
ruff format --check .  # ✓ Code formatted
pytest tests/ -v       # ✓ All tests pass
```

## Local Testing

### Flask Server
```bash
python main.py
# → http://localhost:8080
```

### Lambda Handler (Direct)
```bash
python -c "
from lambda_handler import lambda_handler
import json

event = {
    'httpMethod': 'GET',
    'path': '/health'
}
result = lambda_handler(event, None)
print(json.dumps(json.loads(result['body']), indent=2))
"
```

### SAM Local (Docker)
```bash
sam build
sam local start-api
# → http://localhost:3000
```

## Deployment

### Manual Deploy
```bash
sam build
sam deploy --config-env dev      # Dev
sam deploy --config-env staging  # Staging
sam deploy --config-env prod     # Production
```

### Automated Deploy (CI/CD)
- Push to `main` → deploys to **staging**
- Tag `v*.*.*` → deploys to **production**

## Project Structure

```
├── lambda_handler.py      # Production entry point
├── main.py                # Local dev entry point
├── engine/                # Core business logic
│   ├── models.py          # Data models
│   ├── processor.py       # Main orchestrator
│   ├── validators.py      # Input validation
│   └── calculators/       # Calculation modules
├── tests/                 # Test suite
├── template.yaml          # SAM/CloudFormation
├── samconfig.toml         # Deployment configs
└── pyproject.toml         # Ruff/pytest config
```

## Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: correct bug
docs: update documentation
test: add tests
refactor: code restructure
chore: maintenance tasks
```

## Questions?

Contact the team on Slack or open an issue.
