# Product Requirements Document: Finalis Contract Engine API (v2.0)

## 1. Introduction

The Finalis Contract Engine is a backend service designed to process M&A deal success fees deterministically. It serves as the "financial brain" that applies contract-specific rules (standard or Pay-As-You-Go) to calculate payouts, manage debt/credit, and update the long-term state of a customer's contract.

---

## 2. Functional Requirements

### 2.1 Input Validation & Integrity

The system **MUST** reject transactions before processing if they violate these constraints:

#### Financial Non-Negativity
- `success_fees`, `external_retainer`, `current_credit`, `current_debt`, `amount_due`, and `amount_paid` must strictly be ≥ 0.

#### Retainer Logic
- If `has_external_retainer` is `true`, the flag `include_retainer_in_fees` is **mandatory**.

#### Rate Validations
- `fixed_rate`, `preferred_rate`, and all Lehman tier rates must be between 0 and 1 (inclusive).

#### PAYG Constraints
If the contract is "Pay-As-You-Go" (`is_pay_as_you_go=True`):
- `current_credit` must be 0 (PAYG does not support credit).
- `future_subscription_fees` list must be empty (PAYG does not support subscription prepayments).

---

### 2.2 Standard Fee Calculations (Pre-Commission)

Before calculating the Finalis commission, the system must calculate and deduct the following regulatory and service fees from the Gross Success Fee:

| Fee Type | Rate | Condition |
|----------|------|-----------|
| **FINRA/SIPC Fee** | Fixed at 0.4732% (0.004732) | Applied unless `has_finra_fee` is explicitly `False` |
| **Distribution Fee** | Fixed at 10% | Applied if `is_distribution_fee_true` is `True` |
| **Sourcing Fee** | Fixed at 10% | Applied if `is_sourcing_fee_true` is `True` |

---

### 2.3 Implied Cost (Broker-Dealer Cost) Logic

The system must calculate the "Implied Cost" (the baseline cost before credits/caps are applied) using the following priority hierarchy (highest to lowest):

1. **Preferred Rate Override**: If `has_preferred_rate` is `True`, use the provided `preferred_rate` for the entire deal volume.

2. **Deal Exempt**: If `is_deal_exempt` is `True`, apply a flat rate of **1.5%**.

3. **Lehman Progressive Tiers** (if `rate_type='lehman'`):
   - Must utilize `accumulated_success_fees_before_this_deal` to determine the starting tier.
   - **Gap Handling**: If there is a numerical gap between the current accumulated volume and the next tier's lower bound, the logic must "jump" the gap to the next tier logic rather than failing.
   - **Infinite Tiers**: Must support tiers where `upper_bound` is `null` (infinite capacity).

4. **Fixed Rate**: A simple percentage applied to the full success fee.

---

### 2.4 Debt & Deferred Fee Collection

#### Collection Priority
Debt is collected from the Gross Success Fee **before** credits are generated.

#### Deferred Logic (Multi-Year)
The system must check a `deferred_schedule` list. It determines the applicable deferred fee by calculating the **Contract Year**:
- Year 1 = Days 0-364
- Year 2 = Days 365-729
- etc.

Based on `contract_start_date` vs. `deal_date`.

#### Credit Generation

| Contract Type | Credit Generation Rule |
|---------------|------------------------|
| **Standard Contracts** | 100% of collected debt (both regular and deferred) is converted into Credit |
| **PAYG Contracts** | Debt collection generates **Zero Credit** |

---

### 2.5 Commission & Credit Application Logic

#### Standard Contracts

1. **Credit Usage**: Existing Credit + Newly Generated Credit is applied to reduce the Implied Cost.

2. **Advance Subscription**: Remaining Implied Cost (after credit) is forcefully applied to `future_subscription_fees` (sorted by due date). Logic must handle partial payments of specific installments.

3. **Final Commission**: Any Implied Cost remaining after credit usage and advance subscription payments becomes the "Finalis Commission".

#### Pay-As-You-Go (PAYG) Contracts

1. **ARR Target**: Implied Cost first fills the `annual_subscription` bucket (ARR).

2. **Commission Trigger**: Only once the accumulated fees (`payg_commissions_accumulated`) exceed the ARR target does the Implied Cost become "Finalis Commission".

---

### 2.6 Cost Cap Safeguards

The system must enforce a "maximum charge" limit if configured:

#### Scope
- Can be `annual` (checking `total_paid_this_contract_year`)
- Or `total` (checking `total_paid_all_time`)

#### Behavior
1. Calculates `available_space` under the cap.
2. **Advance Fees take priority**: If `advance_fees + commissions > cap`, the commissions are reduced first.
3. **Tracking**: The system must return `amount_not_charged_due_to_cap` for transparency.

---

## 3. Financial Precision Standards

| Aspect | Requirement |
|--------|-------------|
| **Data Type** | All monetary calculations must use `Decimal` types, never floats |
| **Rounding Strategy** | `ROUND_HALF_UP` (standard arithmetic rounding) to 2 decimal places |
| **Output Formatting** | All monetary outputs in the JSON response must be cast to `float` with 2 decimal precision for API compatibility |

---

## 4. API Interface Specifications

### Endpoint: `POST /process_deal`

#### Input
JSON object containing:
- `contract` — Rules configuration
- `state` — Accumulated history
- `deal` — Current transaction details

#### Output
A structured JSON object containing:

| Field | Description |
|-------|-------------|
| `deal_summary` | Normalized deal data |
| `calculations` | Granular breakdown of every fee (FINRA, Sourcing, Implied, etc.) |
| `state_changes` | Initial vs. Final values for Debt, Credit, and Deferred balances |
| `updated_contract_state` | The new state object to be saved to the database (including updated accumulators) |
| `payg_tracking` | (Conditional) Specific ARR progress metrics if the deal is PAYG |

### Health Check

| Endpoint | Method | Response |
|----------|--------|----------|
| `/health` | GET | Must return status `200` explicitly for uptime monitoring |

---

## 5. Deployment Requirements

### Production (AWS Lambda)

| Component | Specification |
|-----------|---------------|
| **Runtime** | AWS Lambda with Python 3.12 |
| **Entry Point** | `lambda_handler.lambda_handler` |
| **Infrastructure** | AWS SAM (Serverless Application Model) |
| **API Gateway** | Managed by SAM, handles routing and CORS |
| **Dependencies** | Zero external dependencies (stdlib only) |

### Environments

| Environment | Stack Name | Trigger |
|-------------|------------|---------|
| **Staging** | `finalis-engine-staging` | Push to `main` branch |
| **Production** | `finalis-engine-prod` | Version tag (`v*.*.*`) |

### Local Development

| Component | Specification |
|-----------|---------------|
| **Server** | Flask (v3.1.0) for local testing |
| **Entry Point** | `main.py` |
| **CORS** | Enabled via flask-cors |

---

## Appendix: Processing Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEAL PROCESSING FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐
  │ INPUT DATA   │
  │ - contract   │
  │ - state      │
  │ - deal   │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │ STEP 1: VALIDATE INPUT               │
  │ - Check non-negativity               │
  │ - Validate rate constraints          │
  │ - Enforce PAYG constraints           │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 2: CALCULATE FIXED COSTS        │
  │ - FINRA Fee (0.4732%)                │
  │ - Distribution Fee (10%)             │
  │ - Sourcing Fee (10%)                 │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 3: CALCULATE IMPLIED COST       │
  │ Priority: Preferred > Exempt >       │
  │           Lehman > Fixed             │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 4: COLLECT DEBT                 │
  │ - Regular debt + Deferred backend    │
  │ - Generate credit (standard only)    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 5: APPLY CREDIT                 │
  │ - Reduce implied cost                │
  │ - (Skip for PAYG)                    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 6: ADVANCE SUBSCRIPTION FEES    │
  │ - Apply to future payments           │
  │ - (Skip for PAYG)                    │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 7: CALCULATE COMMISSIONS        │
  │ - Standard: remaining implied        │
  │ - PAYG: after ARR covered            │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 8: APPLY COST CAP               │
  │ - Annual or Total cap                │
  │ - Advance fees have priority         │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────────────────────────────┐
  │ STEP 9: CALCULATE NET PAYOUT         │
  │ - Success fees - all deductions      │
  └──────────────┬───────────────────────┘
                 │
                 ▼
  ┌──────────────┐
  │ OUTPUT JSON  │
  │ - summary    │
  │ - calcs      │
  │ - state      │
  └──────────────┘
```

---

*Document Version: 2.0*  
*Last Updated: February 2026*
