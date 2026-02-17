# Copilot Instructions for Finalis Engine API

## 1. Project Overview

This is a **financial calculation engine** for M&A deal commission processing. It runs on AWS Lambda (production) with Flask for local development.

**Critical**: This handles real money calculations. Precision and correctness are paramount.

## 2. Architecture

| Component | Purpose |
|-----------|---------|
| `lambda_handler.py` | Production entry point (AWS Lambda) |
| `main.py` | Local development entry point (Flask) |
| `engine/` | Core business logic |
| `engine/calculators/` | Pipeline calculation steps |
| `tests/` | pytest test suite |

### Processing Pipeline
```
Input → Validate → Fees → Implied → Debt → Credit → Subscription → Commission → Cost Cap → Payout → Output
```

## 3. Technical Requirements

### Python Version
- **Python 3.12** everywhere (Lambda, CI, local)
- Target version in `pyproject.toml`: `py312`

### Dependencies
- **Production (Lambda)**: Zero external dependencies - stdlib only
- **Local dev**: Flask, flask-cors, pytest, ruff

### Architecture
- **ARM64 (Graviton2)** for Lambda - better cost/performance

## 4. Financial Precision Standards

**CRITICAL**: All monetary calculations must follow these rules:

```python
from decimal import Decimal, ROUND_HALF_UP

# ✅ CORRECT: Use Decimal for all money
amount = Decimal("100.50")
rate = Decimal("0.05")
result = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ❌ WRONG: Never use floats for money
amount = 100.50  # NO!
```

- Use `Decimal` type for all monetary values
- Round with `ROUND_HALF_UP` to 2 decimal places
- Output as `float` only at API boundary (for JSON serialization)

## 5. Code Organization

### Business Logic
- All business logic lives in `engine/calculators/`
- Each calculator is a single-responsibility class
- Processors orchestrate calculators, never contain business logic

### Models
- Use `@dataclass` for all domain models
- Models live in `engine/models.py`
- Input validation in `engine/validators.py`

### No External State
- Lambda functions must be stateless
- No database connections, file I/O, or external API calls
- All state passed in request, returned in response

## 6. Testing Requirements

### Coverage
- All calculators must have unit tests
- Integration tests for complete deal processing
- Test edge cases: zero values, negative prevention, boundary conditions

### Running Tests
```bash
pytest tests/ -v           # All tests
pytest tests/test_*.py -v  # Specific file
```

### Test Structure
```python
class TestCalculatorName:
    @pytest.fixture
    def calculator(self):
        return CalculatorClass()
    
    def test_specific_behavior(self, calculator):
        # Arrange
        # Act
        # Assert
```

## 7. Linting & Formatting

### Ruff Configuration
- Configured in `pyproject.toml`
- Rules: E, W, F, I, B, C4, UP
- Line length: 120
- Auto-fix on save enabled

### Commands
```bash
ruff check .           # Check
ruff check --fix .     # Auto-fix
ruff format .          # Format
```

## 8. API Conventions

### Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api` | API info |
| POST | `/process_deal` | Process a deal |

### Request/Response
- Content-Type: `application/json`
- All responses include CORS headers
- Errors return appropriate HTTP status codes (400, 500)

### Error Handling
```python
# Validation errors → 400
# Processing errors → 500
# Always return structured error response
{"error": "message", "status": "failed"}
```

## 9. Git & CI/CD

### Branch Strategy
- `main` branch only (single-branch development)
- Feature branches: `feature/description`
- Fix branches: `fix/description`

### Deployment Triggers
| Trigger | Environment |
|---------|-------------|
| Push to `main` | Staging |
| Tag `v*.*.*` | Production |

### Commit Messages
Use conventional commits:
```
feat: add new calculation
fix: correct rounding error
docs: update API documentation
test: add edge case tests
refactor: simplify pipeline
```

## 10. PR Description Rules

### Overview Section
- 2 sentences maximum
- Focus on what the PR does
- No fluff or marketing language

### Changes Section
- Group by feature/component
- Focus on additions/changes only
- Be concise

### Template
```markdown
## [Brief Title]

[2 sentence overview]

### Changes

**Category 1**
- Change 1
- Change 2

**Files Changed**: X files, Y additions, Z deletions
```

## 11. Security

### Never Log Sensitive Data
- No financial amounts in logs (use deal names/IDs only)
- No PII in error messages

### Input Validation
- Validate all inputs before processing
- Reject negative financial values
- Validate rate constraints (0-1 range)

## 12. Documentation

### Code Comments
- Docstrings for all public functions/classes
- Explain "why" not "what" in inline comments
- Use English only

### Files to Update
When changing functionality:
- `PRD.md` - Product requirements
- `docs/API.md` - API documentation
- `README.md` - If setup/usage changes
- `CONTRIBUTING.md` - If workflow changes

## 13. Common Patterns

### Calculator Pattern
```python
@dataclass
class CalculatorResult:
    value: Decimal
    # ... other fields

class Calculator:
    def calculate(self, ctx: ProcessingContext) -> CalculatorResult:
        # Business logic here
        return CalculatorResult(value=result)
```

### Context Pattern
```python
# ProcessingContext carries state through pipeline
ctx = ProcessingContext(
    deal=deal,
    contract=contract,
    initial_state=state,
)
```

## 14. Things to Avoid

- ❌ Float arithmetic for money
- ❌ External dependencies in Lambda
- ❌ Business logic in controllers/handlers
- ❌ Raw SQL or database calls
- ❌ Console.log (use `logger`)
- ❌ Hardcoded configuration values
- ❌ Dead code or commented-out blocks
- ❌ Tests without assertions
