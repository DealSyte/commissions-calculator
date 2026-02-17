# Finalis Engine API Documentation

**Version:** 3.0  
**Runtime:** AWS Lambda (production) / Flask (local development)

---

## Base URLs

| Environment | URL |
|-------------|-----|
| **Production** | `https://{api-id}.execute-api.us-east-1.amazonaws.com/Prod` |
| **Staging** | `https://{api-id}.execute-api.us-east-1.amazonaws.com/Prod` |
| **Local** | `http://localhost:8080` |

> **Note:** Each environment has its own API Gateway. Get the actual URL from the SAM deployment output or AWS Console.

---

## Invoking from finalis-api (Same AWS Account)

For internal service-to-service calls from `finalis-api`, use **direct Lambda invocation** via AWS SDK. This is faster than API Gateway and uses IAM for authentication.

### Lambda Function Names

| Environment | Function Name |
|-------------|---------------|
| **Staging** | `finalis-engine-staging` |
| **Production** | `finalis-engine-prod` |

### TypeScript Example (AWS SDK v3)

```typescript
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';

// Initialize Lambda client (reuse across requests)
const lambdaClient = new LambdaClient({ region: 'us-east-1' });

// Types for the engine request/response
interface EngineContract {
  rate_type: 'fixed' | 'lehman';
  fixed_rate?: number;
  accumulated_success_fees_before_this_deal: number;
  contract_start_date: string;
  is_pay_as_you_go: boolean;
  lehman_tiers?: Array<{ lower_bound: number; upper_bound: number | null; rate: number }>;
  annual_subscription?: number;
  cost_cap_amount?: number;
  cost_cap_scope?: 'annual' | 'total';
}

interface EngineState {
  current_credit: number;
  current_debt: number;
  is_in_commissions_mode: boolean;
  total_paid_this_contract_year: number;
  total_paid_all_time: number;
  future_subscription_fees: Array<{ due_date: string; amount_due: number; amount_paid: number }>;
  deferred_schedule: Array<{ year: number; amount: number }>;
  payg_commissions_accumulated?: number;
}

interface EngineDeal {
  deal_name: string;
  success_fees: number;
  deal_date: string;
  is_distribution_fee_true: boolean;
  is_sourcing_fee_true: boolean;
  is_deal_exempt: boolean;
  has_finra_fee?: boolean;
  external_retainer?: number;
  has_external_retainer?: boolean;
  include_retainer_in_fees?: boolean;
  has_preferred_rate?: boolean;
  preferred_rate?: number;
}

interface EnginePayload {
  contract: EngineContract;
  state: EngineState;
  deal: EngineDeal;
}

interface EngineResult {
  deal_summary: Record<string, unknown>;
  calculations: {
    finalis_commission: number;
    net_payout: number;
    finra_fee: number;
    distribution_fee: number;
    sourcing_fee: number;
    implied_cost: number;
    [key: string]: unknown;
  };
  state_changes: Record<string, unknown>;
  updated_contract_state: EngineState;
  payg_tracking?: Record<string, unknown>;
}

/**
 * Invoke the Finalis Engine Lambda directly.
 */
async function invokeEngine(
  payload: EnginePayload,
  environment: 'staging' | 'prod' = 'staging'
): Promise<EngineResult> {
  const functionName = `finalis-engine-${environment}`;

  // Wrap payload in API Gateway-like event structure
  const event = {
    httpMethod: 'POST',
    path: '/process_deal',
    body: JSON.stringify(payload),
  };

  const command = new InvokeCommand({
    FunctionName: functionName,
    InvocationType: 'RequestResponse',
    Payload: Buffer.from(JSON.stringify(event)),
  });

  const response = await lambdaClient.send(command);

  // Parse response
  const responsePayload = JSON.parse(
    Buffer.from(response.Payload!).toString('utf-8')
  );

  if (responsePayload.statusCode !== 200) {
    throw new Error(`Engine error: ${responsePayload.body}`);
  }

  return JSON.parse(responsePayload.body) as EngineResult;
}

// Usage example
async function processDeal() {
  const result = await invokeEngine({
    contract: {
      rate_type: 'fixed',
      fixed_rate: 0.03,
      accumulated_success_fees_before_this_deal: 0,
      contract_start_date: '2025-01-01',
      is_pay_as_you_go: false,
    },
    state: {
      current_credit: 0,
      current_debt: 0,
      is_in_commissions_mode: true,
      total_paid_this_contract_year: 0,
      total_paid_all_time: 0,
      future_subscription_fees: [],
      deferred_schedule: [],
    },
    deal: {
      deal_name: 'Test Deal',
      success_fees: 1000000,
      deal_date: '2025-06-15',
      is_distribution_fee_true: false,
      is_sourcing_fee_true: false,
      is_deal_exempt: false,
      has_finra_fee: true,
      external_retainer: 0,
      has_external_retainer: false,
      include_retainer_in_fees: false,
    },
  }, 'staging');

  console.log('Commission:', result.calculations.finalis_commission);
  console.log('Net Payout:', result.calculations.net_payout);
}
```

### Health Check via Lambda

```typescript
async function checkEngineHealth(
  environment: 'staging' | 'prod' = 'staging'
): Promise<{ status: string; environment: string }> {
  const functionName = `finalis-engine-${environment}`;

  const event = {
    httpMethod: 'GET',
    path: '/health',
  };

  const command = new InvokeCommand({
    FunctionName: functionName,
    InvocationType: 'RequestResponse',
    Payload: Buffer.from(JSON.stringify(event)),
  });

  const response = await lambdaClient.send(command);
  const responsePayload = JSON.parse(
    Buffer.from(response.Payload!).toString('utf-8')
  );

  return JSON.parse(responsePayload.body);
}
```

### IAM Permissions Required

The calling service (finalis-api) needs `lambda:InvokeFunction` permission:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": [
                "arn:aws:lambda:us-east-1:425693140400:function:finalis-engine-staging",
                "arn:aws:lambda:us-east-1:425693140400:function:finalis-engine-prod"
            ]
        }
    ]
}
```

### Error Handling

```typescript
import { ResourceNotFoundException, ServiceException } from '@aws-sdk/client-lambda';

try {
  const result = await invokeEngine(payload);
} catch (error) {
  if (error instanceof ResourceNotFoundException) {
    // Lambda function doesn't exist
    console.error('Lambda function not found');
  } else if (error instanceof ServiceException) {
    // AWS service error (permissions, throttling, etc.)
    console.error('AWS error:', error.message);
  } else if (error instanceof Error && error.message.startsWith('Engine error:')) {
    // Engine returned non-200 status (validation error, etc.)
    console.error('Engine error:', error.message);
  }
  throw error;
}
```

### Performance Considerations

| Method | Latency | Use Case |
|--------|---------|----------|
| **Direct Lambda** | ~50-100ms | Internal service calls |
| **API Gateway** | ~100-200ms | External clients, webhooks |

For high-throughput scenarios, consider:
- Reusing the LambdaClient instance (don't create per-request)
- Using async invocation for fire-and-forget scenarios

---

## Table of Contents

1. [Overview](#overview)
2. [Endpoints](#endpoints)
3. [Request Schema](#request-schema)
4. [Response Schema](#response-schema)
5. [Examples](#examples)
6. [Error Handling](#error-handling)

---

## Overview

The Finalis Engine API processes M&A deal fees for broker-dealer contracts. It calculates:

- **FINRA fees** (0.4732% regulatory fee)
- **Distribution fees** (10% for distribution deals)
- **Sourcing fees** (10% for sourced deals)
- **Implied costs** (fixed rate or Lehman tiered)
- **Debt collection** and **credit application**
- **Subscription prepayment** allocation
- **Commissions** with cost cap enforcement
- **Net payout** to the broker

---

## Endpoints

### `GET /`
Health check with version info.

**Response:**
```json
{
  "status": "ok",
  "message": "Finalis Engine API running",
  "version": "3.0",
  "endpoints": {
    "process_deal": "/process_deal [POST]",
    "health": "/health [GET]"
  }
}
```

### `GET /health`
Simple health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "environment": "dev"
}
```

### `GET /api`
API information endpoint.

**Response:**
```json
{
  "status": "ok",
  "message": "Finalis Commission Calculator API",
  "version": "3.0",
  "environment": "dev",
  "runtime": "AWS Lambda",
  "endpoints": {
    "process_deal": "/process_deal [POST]",
    "health": "/health [GET]"
  }
}
```

### `POST /process_deal`
Process a deal through the contract engine.

**Content-Type:** `application/json`

---

## Request Schema

The request body must be a JSON object with three top-level keys:

```json
{
  "deal": { ... },
  "contract": { ... },
  "state": { ... }
}
```

### `deal` Object

Information about the deal being processed.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `deal_name` | string | ✅ | - | Name/identifier of the deal |
| `success_fees` | number | ✅ | - | Total success fees in USD (must be > 0) |
| `deal_date` | string | ✅ | - | Date of deal in ISO format (YYYY-MM-DD) |
| `is_distribution_fee_true` | boolean | ✅ | - | Whether 10% distribution fee applies |
| `is_sourcing_fee_true` | boolean | ✅ | - | Whether 10% sourcing fee applies |
| `is_deal_exempt` | boolean | ✅ | - | Whether deal uses exempt rate (1.5%) |
| `has_finra_fee` | boolean | ❌ | `true` | Whether FINRA fee (0.4732%) applies |
| `external_retainer` | number | ❌ | `0` | External retainer amount |
| `has_external_retainer` | boolean | ❌ | `false` | Whether external retainer exists |
| `include_retainer_in_fees` | boolean | ❌ | `true` | Include retainer in fee calculation |
| `has_preferred_rate` | boolean | ❌ | `false` | Whether a preferred rate overrides |
| `preferred_rate` | number | ❌ | `null` | Custom rate (0.0-1.0) if has_preferred_rate |

**Example:**
```json
{
  "deal_name": "Acme Corp Acquisition",
  "success_fees": 500000,
  "deal_date": "2026-01-15",
  "is_distribution_fee_true": false,
  "is_sourcing_fee_true": false,
  "is_deal_exempt": false,
  "has_finra_fee": true,
  "external_retainer": 0,
  "has_external_retainer": false,
  "include_retainer_in_fees": true,
  "has_preferred_rate": false,
  "preferred_rate": null
}
```

---

### `contract` Object

Contract configuration and fee structure.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `rate_type` | string | ✅ | - | `"fixed"` or `"lehman"` |
| `accumulated_success_fees_before_this_deal` | number | ✅ | - | Cumulative success fees before this deal |
| `fixed_rate` | number | ❌* | - | Fixed rate (0.0-1.0), required if rate_type="fixed" |
| `lehman_tiers` | array | ❌* | `[]` | Tiered rates, required if rate_type="lehman" |
| `is_pay_as_you_go` | boolean | ❌ | `false` | PAYG contract (no subscription) |
| `contract_start_date` | string | ❌ | `null` | Contract start date (YYYY-MM-DD) |
| `annual_subscription` | number | ❌ | `0` | Annual subscription amount (ARR target for PAYG) |
| `cost_cap_type` | string | ❌ | `null` | `"annual"` or `"total"` for cost limits |
| `cost_cap_amount` | number | ❌ | `null` | Maximum cost under cap type |

**Fixed Rate Example:**
```json
{
  "rate_type": "fixed",
  "fixed_rate": 0.05,
  "accumulated_success_fees_before_this_deal": 1000000,
  "is_pay_as_you_go": false,
  "annual_subscription": 36000,
  "cost_cap_type": null,
  "cost_cap_amount": null
}
```

**Lehman Tier Example:**
```json
{
  "rate_type": "lehman",
  "accumulated_success_fees_before_this_deal": 5000000,
  "lehman_tiers": [
    { "lower_bound": 0, "upper_bound": 5000000, "rate": 0.05 },
    { "lower_bound": 5000000, "upper_bound": 10000000, "rate": 0.04 },
    { "lower_bound": 10000000, "upper_bound": null, "rate": 0.03 }
  ],
  "is_pay_as_you_go": false,
  "annual_subscription": 48000
}
```

#### `lehman_tiers[]` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lower_bound` | number | ✅ | Start of tier (inclusive) |
| `upper_bound` | number\|null | ✅ | End of tier (exclusive), `null` = unlimited |
| `rate` | number | ✅ | Rate for this tier (0.0-1.0) |

---

### `state` Object

Current contract state (balances, mode, scheduled payments).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `current_credit` | number | ❌ | `0` | Available credit balance |
| `current_debt` | number | ❌ | `0` | Outstanding debt to collect |
| `is_in_commissions_mode` | boolean | ❌ | `false` | Whether contract is in commissions mode |
| `future_subscription_fees` | array | ❌ | `[]` | Scheduled subscription payments |
| `deferred_schedule` | array | ❌ | `[]` | Year-specific deferred fees |
| `deferred_subscription_fee` | number | ❌ | `0` | Legacy single deferred amount |
| `total_paid_this_contract_year` | number | ❌ | `0` | YTD payments (for annual cap) |
| `total_paid_all_time` | number | ❌ | `0` | Lifetime payments (for total cap) |
| `payg_commissions_accumulated` | number | ❌ | `0` | PAYG accumulated commissions |

**Example:**
```json
{
  "current_credit": 5000,
  "current_debt": 2000,
  "is_in_commissions_mode": false,
  "future_subscription_fees": [
    {
      "payment_id": "pay_001",
      "due_date": "2026-03-01",
      "amount_due": 3000,
      "amount_paid": 0
    },
    {
      "payment_id": "pay_002",
      "due_date": "2026-06-01",
      "amount_due": 3000,
      "amount_paid": 0
    }
  ],
  "deferred_schedule": [
    { "year": 2025, "amount": 1000 },
    { "year": 2026, "amount": 1500 }
  ],
  "deferred_subscription_fee": 0,
  "total_paid_this_contract_year": 15000,
  "total_paid_all_time": 45000,
  "payg_commissions_accumulated": 0
}
```

#### `future_subscription_fees[]` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `payment_id` | string | ✅ | Unique payment identifier |
| `due_date` | string | ✅ | Payment due date (YYYY-MM-DD) |
| `amount_due` | number | ✅ | Total amount due |
| `amount_paid` | number | ✅ | Amount already paid |

#### `deferred_schedule[]` Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `year` | number | ✅ | Year the deferred fee applies to |
| `amount` | number | ✅ | Deferred amount for that year |

---

## Response Schema

Successful responses return a JSON object with these sections:

```json
{
  "deal_summary": { ... },
  "calculations": { ... },
  "state_changes": { ... },
  "updated_future_payments": [ ... ],
  "updated_contract_state": { ... },
  "payg_tracking": { ... }  // Only for PAYG contracts
}
```

### `deal_summary` Object

| Field | Type | Description |
|-------|------|-------------|
| `deal_name` | string | Name of the processed deal |
| `success_fees` | string | Success fees amount (string for precision) |
| `deal_date` | string | Date of the deal |
| `contract_year` | number | Year of the contract |

### `calculations` Object

| Field | Type | Description |
|-------|------|-------------|
| `finra_fee` | string | FINRA regulatory fee (0.4732%) |
| `distribution_fee` | string | Distribution fee (10% if applicable) |
| `sourcing_fee` | string | Sourcing fee (10% if applicable) |
| `implied_total` | string | Total implied cost before adjustments |
| `debt_collected` | string | Total debt collected this deal |
| `credit_used` | string | Credit applied against implied |
| `implied_after_credit` | string | Implied remaining after credit |
| `advance_fees_created` | string | Subscription payments prepaid |
| `implied_after_subscription` | string | Implied after subscription allocation |
| `finalis_commissions` | string | Final Finalis commissions |
| `amount_not_charged_due_to_cap` | string | Amount waived due to cost cap |
| `net_payout` | string | Net payout to broker |

### `state_changes` Object

| Field | Type | Description |
|-------|------|-------------|
| `debt_collected` | string | Debt collected this transaction |
| `debt_remaining` | string | Remaining debt balance |
| `credit_generated` | string | New credit from debt collection |
| `credit_used` | string | Credit consumed by implied |
| `credit_remaining` | string | Credit balance after transaction |
| `entered_commissions_mode` | boolean | Whether contract entered commissions mode |
| `is_now_in_commissions_mode` | boolean | Current commissions mode status |

### `updated_future_payments` Array

Array of updated payment objects showing modified `amount_paid` values after advance fee allocation.

### `updated_contract_state` Object

New state values to persist:

| Field | Type | Description |
|-------|------|-------------|
| `current_credit` | string | New credit balance |
| `current_debt` | string | New debt balance |
| `is_in_commissions_mode` | boolean | New commissions mode status |
| `total_paid_this_contract_year` | string | Updated YTD payments |
| `total_paid_all_time` | string | Updated lifetime payments |

### `payg_tracking` Object (PAYG only)

| Field | Type | Description |
|-------|------|-------------|
| `arr_target` | string | Annual subscription target |
| `arr_contribution_this_deal` | string | Contribution toward ARR this deal |
| `finalis_commissions_this_deal` | string | Excess commissions collected this deal (after ARR coverage). Does NOT include `arr_contribution_this_deal`. Add both to get total Finalis charge. |
| `commissions_accumulated` | string | Cumulative commissions |
| `remaining_to_cover_arr` | string | ARR still needed |
| `arr_coverage_percentage` | number | Percentage of ARR covered |

---

## Examples

### Example 1: Simple Fixed Rate Deal

**Request:**
```json
{
  "deal": {
    "deal_name": "Widget Co Sale",
    "success_fees": 100000,
    "deal_date": "2026-02-01",
    "is_distribution_fee_true": false,
    "is_sourcing_fee_true": false,
    "is_deal_exempt": false,
    "has_finra_fee": true
  },
  "contract": {
    "rate_type": "fixed",
    "fixed_rate": 0.05,
    "accumulated_success_fees_before_this_deal": 0,
    "is_pay_as_you_go": false,
    "annual_subscription": 0
  },
  "state": {
    "current_credit": 0,
    "current_debt": 0,
    "is_in_commissions_mode": false,
    "future_subscription_fees": []
  }
}
```

**Response:**
```json
{
  "deal_summary": {
    "deal_name": "Widget Co Sale",
    "success_fees": "100000",
    "deal_date": "2026-02-01",
    "contract_year": 1
  },
  "calculations": {
    "finra_fee": "473.20",
    "distribution_fee": "0",
    "sourcing_fee": "0",
    "implied_total": "5473.20",
    "debt_collected": "0",
    "credit_used": "0",
    "implied_after_credit": "5473.20",
    "advance_fees_created": "0",
    "implied_after_subscription": "5473.20",
    "finalis_commissions": "5473.20",
    "amount_not_charged_due_to_cap": "0",
    "net_payout": "94526.80"
  },
  "state_changes": {
    "debt_collected": "0",
    "debt_remaining": "0",
    "credit_generated": "0",
    "credit_used": "0",
    "credit_remaining": "0",
    "entered_commissions_mode": true,
    "is_now_in_commissions_mode": true
  },
  "updated_future_payments": [],
  "updated_contract_state": {
    "current_credit": "0",
    "current_debt": "0",
    "is_in_commissions_mode": true,
    "total_paid_this_contract_year": "5473.20",
    "total_paid_all_time": "5473.20"
  }
}
```

### Example 2: Deal with Credit and Subscription Prepayment

**Request:**
```json
{
  "deal": {
    "deal_name": "MegaCorp Merger",
    "success_fees": 500000,
    "deal_date": "2026-03-15",
    "is_distribution_fee_true": false,
    "is_sourcing_fee_true": false,
    "is_deal_exempt": false,
    "has_finra_fee": true
  },
  "contract": {
    "rate_type": "fixed",
    "fixed_rate": 0.05,
    "accumulated_success_fees_before_this_deal": 100000,
    "annual_subscription": 36000
  },
  "state": {
    "current_credit": 10000,
    "current_debt": 0,
    "is_in_commissions_mode": false,
    "future_subscription_fees": [
      {
        "payment_id": "sub_q2",
        "due_date": "2026-04-01",
        "amount_due": 9000,
        "amount_paid": 0
      },
      {
        "payment_id": "sub_q3",
        "due_date": "2026-07-01",
        "amount_due": 9000,
        "amount_paid": 0
      }
    ]
  }
}
```

### Example 3: Lehman Tiered Contract

**Request:**
```json
{
  "deal": {
    "deal_name": "Enterprise Deal",
    "success_fees": 2000000,
    "deal_date": "2026-06-01",
    "is_distribution_fee_true": false,
    "is_sourcing_fee_true": false,
    "is_deal_exempt": false
  },
  "contract": {
    "rate_type": "lehman",
    "accumulated_success_fees_before_this_deal": 4000000,
    "lehman_tiers": [
      { "lower_bound": 0, "upper_bound": 5000000, "rate": 0.05 },
      { "lower_bound": 5000000, "upper_bound": 10000000, "rate": 0.04 },
      { "lower_bound": 10000000, "upper_bound": null, "rate": 0.03 }
    ]
  },
  "state": {
    "current_credit": 0,
    "current_debt": 0,
    "is_in_commissions_mode": true
  }
}
```

**Calculation Breakdown:**
- Accumulated before: $4M → starts in tier 1 (5%)
- Deal: $2M → $1M at 5% + $1M at 4%
- Implied: $50,000 + $40,000 = $90,000
- FINRA: $2M × 0.4732% = $9,464
- Total: $99,464

### Example 4: PAYG Contract

**Request:**
```json
{
  "deal": {
    "deal_name": "Startup Acquisition",
    "success_fees": 200000,
    "deal_date": "2026-04-01",
    "is_distribution_fee_true": false,
    "is_sourcing_fee_true": false,
    "is_deal_exempt": false
  },
  "contract": {
    "rate_type": "fixed",
    "fixed_rate": 0.05,
    "accumulated_success_fees_before_this_deal": 0,
    "is_pay_as_you_go": true,
    "annual_subscription": 24000
  },
  "state": {
    "current_credit": 0,
    "current_debt": 0,
    "is_in_commissions_mode": false,
    "payg_commissions_accumulated": 0
  }
}
```

**PAYG Logic:**
- ARR target: $24,000
- Implied: $10,000 (5% × $200K) + FINRA
- First $24K of commissions → ARR contribution
- Remaining → Finalis commissions

---

## Error Handling

### Validation Errors (400)

```json
{
  "error": "success_fees must be positive, got: 0",
  "status": "validation_failed"
}
```

**Common validation errors:**
- `success_fees must be positive`
- `rate_type must be 'fixed' or 'lehman'`
- `fixed_rate is required for fixed rate contracts`
- `lehman_tiers required for lehman rate type`

### Missing Input (400)

```json
{
  "error": "No input data provided",
  "status": "failed"
}
```

### Server Error (500)

```json
{
  "error": "Internal processing error message",
  "status": "failed"
}
```

---

## Rate Reference

| Fee Type | Rate | Condition |
|----------|------|-----------|
| FINRA Fee | 0.4732% | `has_finra_fee = true` |
| Distribution Fee | 10% | `is_distribution_fee_true = true` |
| Sourcing Fee | 10% | `is_sourcing_fee_true = true` |
| Deal Exempt Rate | 1.5% | `is_deal_exempt = true` |
| Fixed Rate | Variable | Set in `contract.fixed_rate` |
| Lehman Tiers | Variable | Set in `contract.lehman_tiers[]` |

---

## Integration Notes

1. **Decimal Precision**: All monetary values in responses are strings to preserve precision. Parse as decimal, not float.

2. **State Persistence**: After each deal, persist `updated_contract_state` values for the next call.

3. **Idempotency**: The API is stateless. For idempotent processing, track deal IDs externally.

4. **CORS**: Enabled for all origins. Suitable for browser-based integrations.

5. **Timeouts**: Complex Lehman calculations with many tiers may take slightly longer. Set client timeout ≥ 30s.
