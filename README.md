# Finalis Engine API

A contract processing engine for calculating M&A deal fees, commissions, and payouts.

## Features

- **Fee Calculations**: FINRA (0.4732%), Distribution (10%), Sourcing (10%)
- **Rate Structures**: Fixed rate or Lehman tiered pricing
- **Debt/Credit System**: Collect outstanding debt, apply credit balances
- **Subscription Management**: Prepay future subscription fees from deal proceeds
- **Cost Caps**: Annual or lifetime commission limits
- **PAYG Support**: Pay-as-you-go contracts with ARR tracking

## Architecture

This project supports two deployment modes:

| Mode | Entry Point | Use Case |
|------|-------------|----------|
| **AWS Lambda** | `lambda_handler.py` | Production (serverless) |
| **Flask** | `main.py` | Local development & testing |

## Quick Start (Local Development)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally with Flask
python main.py
# → Open http://localhost:8080

# Run tests
pytest tests/ -v

# Run linter
ruff check .
```

## Deployment (AWS Lambda)

### Prerequisites
- AWS CLI configured with credentials
- AWS SAM CLI installed (`brew install aws-sam-cli`)
- Docker (for local SAM builds)

### Deploy to Environment

```bash
# Build (uses Docker)
sam build --use-container

# Deploy to staging
sam deploy --config-env staging

# Deploy to production (requires confirmation)
sam deploy --config-env prod
```

### CI/CD Pipeline

Deployments are automated via GitHub Actions:

| Trigger | Environment | Stack |
|---------|-------------|-------|
| Push to `main` | Staging | `finalis-engine-staging` |
| Tag `v*.*.*` | Production | `finalis-engine-prod` |
| Pull Request | CI only (lint + test) | — |

**Required GitHub Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

**To release to production:**
```bash
git tag v3.0.0
git push origin v3.0.0
```

## Web Interface (Local Testing)

A minimalist web calculator is available at http://localhost:8080 when running locally:

**macOS/Linux:**
```bash
# First time setup (if not already done)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server
python main.py
```

**Windows (PowerShell):**
```powershell
# First time setup (if not already done)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start the server
python main.py
```

Then open http://localhost:8080 in your browser.

**Windows Troubleshooting:**
- If you see "cannot be loaded because running scripts is disabled", run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- If port 8080 is blocked, check Windows Firewall settings or try a different port: `$env:PORT=3000; python main.py`
- Verify Flask installed: `pip list | findstr Flask`

> **Note:** This UI is deliberately minimalist and intended for internal testing only. For production integrations, use the `/process_deal` API endpoint directly.

The web interface provides:
- Full form inputs for deal, contract, and state parameters
- Lehman tier configuration with pre-populated 5-4-3-2-1% standard tiers
- Dynamic subscription fee management
- Real-time calculation results with collapsible sections
- Raw JSON response viewer for debugging
- Mobile-responsive Material Design layout

## API Endpoint

```bash
POST /process_deal
Content-Type: application/json
```

See [API Documentation](docs/API.md) for complete request/response schemas.

### Quick Example

```bash
curl -X POST http://localhost:8080/process_deal \
  -H "Content-Type: application/json" \
  -d '{
    "deal": {
      "deal_name": "Acme Corp Acquisition",
      "success_fees": 100000,
      "deal_date": "2026-01-15",
      "is_distribution_fee_true": false,
      "is_sourcing_fee_true": false,
      "is_deal_exempt": false,
      "has_finra_fee": true,
      "external_retainer": 5000,
      "has_external_retainer": true,
      "include_retainer_in_fees": true
    },
    "contract": {
      "rate_type": "fixed",
      "fixed_rate": 0.05,
      "accumulated_success_fees_before_this_deal": 0,
      "contract_start_date": "2025-01-01",
      "cost_cap_type": "annual",
      "cost_cap_amount": 50000
    },
    "state": {
      "current_credit": 0,
      "current_debt": 0,
      "is_in_commissions_mode": false,
      "future_subscription_fees": [
        {
          "payment_id": "sub-2026-q1",
          "due_date": "2026-03-01",
          "amount_due": 5000,
          "amount_paid": 0
        }
      ],
      "deferred_schedule": [],
      "total_paid_this_contract_year": 0,
      "total_paid_all_time": 0
    }
  }'
```

**Key Fields:**
- `external_retainer` / `include_retainer_in_fees` - When true, retainer is added to success_fees for fee calculations
- `contract_start_date` - Determines contract year for annual caps and deferred fees

> **Note on Retainer Handling:** External retainers are money the member received directly from the client (not through Finalis). When `include_retainer_in_fees=true`, fee calculations (FINRA, distribution, sourcing, implied) use `success_fees + external_retainer`. However, debt collection and net payout calculations use only `success_fees` since the retainer was paid externally and doesn't flow through Finalis.
- `future_subscription_fees` - Standard contracts prepay these from deal proceeds
- `cost_cap_type` / `cost_cap_amount` - Annual or lifetime commission limits
- `deferred_schedule` - Unpaid subscription fees deferred to collect from future deals
- `total_paid_this_contract_year` / `total_paid_all_time` - Used for cost cap calculations

## Documentation

- [API Documentation](docs/API.md) - Complete endpoint reference
- [PRD](PRD.md) - Product requirements document
- [JSON Schemas](docs/schemas/) - Request/response validation schemas

## Project Structure

```
finalis-engine-api/
├── lambda_handler.py          # AWS Lambda entry point (production)
├── main.py                    # Flask entry point (local dev)
├── template.yaml              # SAM/CloudFormation template
├── samconfig.toml             # SAM deployment configs
├── pyproject.toml             # Project config (ruff, pytest)
├── requirements.txt           # Dev dependencies (Flask, pytest)
├── requirements-lambda.txt    # Lambda dependencies (none - zero deps!)
├── finalis_engine.py          # Legacy wrapper
├── static/                    # Web interface
│   └── index.html             # Material Design calculator
├── engine/                    # Core processing engine
│   ├── __init__.py            # Package exports
│   ├── models.py              # Domain models (dataclasses)
│   ├── validators.py          # Input validation
│   ├── processor.py           # Deal processing orchestrator
│   ├── output.py              # Response builder
│   └── calculators/           # Processing pipeline steps
│       ├── fees.py            # Fee calculations
│       ├── debt.py            # Debt collection
│       ├── credit.py          # Credit application
│       ├── subscription.py    # Subscription prepayment
│       ├── commission.py      # Commission calculation
│       ├── cost_cap.py        # Cost cap enforcement
│       └── payout.py          # Net payout calculation
├── tests/                     # Test suite
│   ├── test_engine.py         # Integration tests
│   ├── test_lambda_handler.py # Lambda handler tests
│   └── ...
├── .github/workflows/
│   └── ci.yml                 # CI/CD pipeline
└── docs/                      # Documentation
    ├── API.md                 # API reference
    └── schemas/               # JSON schemas
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_lambda_handler.py -v

# Run with coverage
pytest tests/ --cov=engine --cov-report=html
```

## Linting

Linting is handled by [Ruff](https://docs.astral.sh/ruff/) and runs automatically:
- **On save** in VS Code (via `.vscode/settings.json`)
- **On PR/push** via GitHub Actions

```bash
# Manual lint check
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment (dev/staging/prod) | `dev` |
| `PORT` | Flask server port (local only) | `8080` |

## License

Proprietary - Finalis Inc.