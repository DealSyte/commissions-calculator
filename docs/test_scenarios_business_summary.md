# Business Logic Test Scenarios

> **⚠️ SYNC WARNING**: This document must stay in sync with `tests/test_integration_scenarios.py`.
> When adding or modifying tests, update this document accordingly.
> 
> Last synced: 2026-02-05

---

## Table of Contents

1. [Preferred Rate Override](#1-preferred-rate-override)
2. [Deal Exempt (M&A)](#2-deal-exempt-ma)
3. [External Retainer Handling](#3-external-retainer-handling)
4. [Lehman Tiers with Historical Production](#4-lehman-tiers-with-historical-production)
5. [Cost Cap Scenarios](#5-cost-cap-scenarios)
6. [PAYG with Cost Cap](#6-payg-with-cost-cap)
7. [PAYG Edge Cases](#7-payg-edge-cases)
8. [Advance Fees (Multiple Payments)](#8-advance-fees-multiple-payments)
9. [Partial Debt Collection](#9-partial-debt-collection)
10. [Maximum Complexity (All Features)](#10-maximum-complexity-all-features)

---

## 1. Preferred Rate Override

**Test Class**: `TestPreferredRateOverride`

### Business Rule
When a deal has a **preferred rate** set, it overrides the contract's normal rate calculation (whether Lehman tiers or fixed rate).

### Test 1.1: Preferred Rate Overrides Lehman
**Test Method**: `test_preferred_rate_overrides_lehman`

| Input | Value |
|-------|-------|
| Deal Size | $2,000,000 |
| Lehman Tiers | 0-$1M @ 5%, $1M+ @ 3% |
| Preferred Rate | 2% |

| Calculation | Without Preferred | With Preferred |
|-------------|-------------------|----------------|
| Commission | $1M × 5% + $1M × 3% = **$80,000** | $2M × 2% = **$40,000** |

**Expected Result**: Implied = $40,000 (preferred rate wins)

### Test 1.2: Preferred Rate Overrides Fixed
**Test Method**: `test_preferred_rate_overrides_fixed`

| Input | Value |
|-------|-------|
| Deal Size | $100,000 |
| Contract Fixed Rate | 5% |
| Preferred Rate | 3% |

**Expected Result**: Implied = $3,000 (not $5,000)

---

## 2. Deal Exempt (M&A)

**Test Class**: `TestDealExempt`

### Business Rule
M&A deals marked as "exempt" use a flat **1.5% rate** regardless of the contract's normal rate structure.

### Test 2.1: Deal Exempt Uses 1.5%
**Test Method**: `test_deal_exempt_uses_1_5_percent`

| Input | Value |
|-------|-------|
| Deal Size | $10,000,000 |
| Contract Fixed Rate | 5% |
| Deal Exempt | Yes |

| Calculation | Normal | Exempt |
|-------------|--------|--------|
| Commission | $10M × 5% = **$500,000** | $10M × 1.5% = **$150,000** |

**Expected Result**: Implied = $150,000

---

## 3. External Retainer Handling

**Test Class**: `TestExternalRetainer`

### Business Rule
External retainers can be either:
- **Deducted**: Added to success fees for commission calculations
- **Not Deducted**: Ignored in calculations (client keeps it separate)

### Test 3.1: Retainer Deducted
**Test Method**: `test_external_retainer_deducted`

| Input | Value |
|-------|-------|
| Success Fees | $100,000 |
| External Retainer | $20,000 |
| Retainer Deducted | Yes |

**Calculation**:
- Total Deal Value = $100,000 + $20,000 = **$120,000**
- Implied = $120,000 × 5% = **$6,000**

### Test 3.2: Retainer NOT Deducted
**Test Method**: `test_external_retainer_not_deducted`

| Input | Value |
|-------|-------|
| Success Fees | $500,000 |
| External Retainer | $100,000 |
| Retainer Deducted | No |

**Calculation**:
- Total Deal Value = **$500,000** (retainer ignored)
- Implied = $500,000 × 5% = **$25,000**

---

## 4. Lehman Tiers with Historical Production

**Test Class**: `TestLehmanWithHistoricalProduction`

### Business Rule
Lehman tier calculations account for **accumulated production** from previous deals in the contract period. New deals start calculating from where the client left off in the tier structure.

### Test 4.1: Starting Mid-Tier
**Test Method**: `test_lehman_starting_mid_tier`

| Input | Value |
|-------|-------|
| Historical Production | $4,000,000 |
| New Deal Size | $3,000,000 |
| Lehman Tiers | 0-$1M @ 5%, $1M-$5M @ 4%, $5M+ @ 3% |

**Calculation**:
- Historical $4M puts client in Tier 2
- New deal breakdown:
  - First $1M (filling $4M→$5M in Tier 2) @ 4% = $40,000
  - Next $2M (entering Tier 3) @ 3% = $60,000
- **Total Implied = $100,000**

### Test 4.2: Crossing Multiple Tiers
**Test Method**: `test_lehman_crossing_multiple_tiers`

| Input | Value |
|-------|-------|
| Historical Production | $0 |
| New Deal Size | $12,000,000 |
| Lehman Tiers | 0-$1M @ 5%, $1M-$5M @ 4%, $5M-$10M @ 3%, $10M+ @ 2% |

**Calculation**:
| Tier | Amount | Rate | Commission |
|------|--------|------|------------|
| 1 | $1,000,000 | 5% | $50,000 |
| 2 | $4,000,000 | 4% | $160,000 |
| 3 | $5,000,000 | 3% | $150,000 |
| 4 | $2,000,000 | 2% | $40,000 |
| **Total** | $12,000,000 | | **$400,000** |

---

## 5. Cost Cap Scenarios

**Test Class**: `TestCostCapScenarios`

### Business Rule
Cost caps limit the total amount a client pays to Finalis:
- **Annual Cap**: Resets each contract year
- **Total Cap**: Lifetime limit across all years

### Test 5.1: Annual Cap Partial Hit
**Test Method**: `test_annual_cap_partial_hit`

| Input | Value |
|-------|-------|
| Deal Size | $500,000 |
| Fixed Rate | 5% |
| Annual Cap | $100,000 |
| Already Paid This Year | $90,000 |

**Calculation**:
- Implied = $500,000 × 5% = $25,000
- Cap remaining = $100,000 - $90,000 = **$10,000**
- Finalis Commissions = **$10,000** (capped)
- Amount Not Charged = **$15,000**

### Test 5.2: Total Cap Fully Hit
**Test Method**: `test_total_cap_fully_hit`

| Input | Value |
|-------|-------|
| Deal Size | $1,000,000 |
| Fixed Rate | 6% |
| Total (Lifetime) Cap | $250,000 |
| Already Paid All Time | $250,000 |

**Calculation**:
- Implied = $1,000,000 × 6% = $60,000
- Cap remaining = $250,000 - $250,000 = **$0**
- Finalis Commissions = **$0**
- Amount Not Charged = **$60,000**

### Test 5.3: Advance Fees Priority
**Test Method**: `test_advance_fees_have_priority_in_cap`

| Input | Value |
|-------|-------|
| Deal Size | $500,000 |
| Fixed Rate | 10% |
| Annual Cap | $100,000 |
| Already Paid This Year | $85,000 |
| Future Subscriptions Owed | $100,000 |

**Business Logic**:
- Implied = $50,000
- All $50,000 goes to **advance subscription prepayment** (not commissions)
- Cost cap applies to commissions, NOT subscription prepayments
- Result: Advance = $50,000, Commissions = $0

---

## 6. PAYG with Cost Cap

**Test Class**: `TestPaygCostCapCombined`

### Business Rule
Pay-As-You-Go (PAYG) contracts accumulate commissions toward an Annual Recurring Revenue (ARR) target. Once ARR is covered, excess goes to Finalis as commissions. 

**Important**: Cost caps apply to the **total** going to Finalis (ARR + excess), not just the excess. When capped, ARR has priority over excess commissions.

### Test 6.1: PAYG + Cost Cap Combined
**Test Method**: `test_payg_with_cost_cap`

| Input | Value |
|-------|-------|
| Deal Size | $3,000,000 |
| Lehman Tiers | 0-$1M @ 5%, $1M-$5M @ 4%, $5M+ @ 3% |
| ARR Target | $10,000 |
| Total Cost Cap | $100,000 |

**Calculation**:
- Lehman Implied = $50,000 + $80,000 = $130,000
- Cost Cap = $100,000 → **Total to Finalis capped at $100,000**
- Amount Not Charged = $30,000
- ARR Contribution = $10,000 (has priority, covers full ARR)
- Finalis Commissions (excess) = $90,000 ($100k cap - $10k ARR)

> **Key Insight**: The cost cap limits the **total** paid to Finalis. ARR is allocated first from
> the capped amount, then the remainder becomes excess commissions.

### Test 6.2: Cost Cap Smaller Than ARR Target
**Test Method**: `test_payg_cost_cap_smaller_than_arr`

| Input | Value |
|-------|-------|
| Deal Size | $500,000 |
| Fixed Rate | 5% |
| ARR Target | $10,000 |
| Total Cost Cap | $5,000 |

**Calculation**:
- Implied = $500,000 × 5% = $25,000
- Cost Cap = $5,000 → **Total to Finalis limited to $5,000**
- ARR Contribution = $5,000 (all goes to ARR, cap prevents full coverage)
- Finalis Commissions (excess) = $0
- ARR Remaining After = $5,000 (ARR not fully covered!)
- `entered_commissions_mode` = **False** (still accumulating toward ARR)
- Amount Not Charged = $20,000

> **Key Insight**: When the cost cap is smaller than the ARR target, the contract does NOT 
> enter commissions mode even though there was commission activity. The cap prevents ARR 
> from being fully covered.

### Test 6.3: Sequential Deals Under Cost Cap
**Test Method**: `test_payg_cost_cap_sequential_deals`

| Scenario | Deal 1 | Deal 2 |
|----------|--------|--------|
| Deal Size | $500,000 | $500,000 |
| Fixed Rate | 5% | 5% |
| ARR Target | $10,000 | $10,000 |
| Total Cost Cap | $100,000 | $100,000 |
| Already Paid | $0 | $25,000 |
| ARR Accumulated | $0 | $10,000 |
| In Commissions Mode | No | Yes |

**Deal 1 Calculation**:
- Implied = $25,000
- Cost Cap Available = $100,000 → No reduction
- ARR = $10,000 (fully covers ARR target)
- Excess = $15,000
- `entered_commissions_mode` = **True**

**Deal 2 Calculation**:
- Implied = $25,000
- Already in commissions mode → All goes to Finalis
- Cost Cap Available = $100,000 - $25,000 = $75,000 → No reduction
- Finalis Commissions = $25,000

> **Key Insight**: Once ARR is covered and commissions mode is entered, subsequent deals
> allocate all implied commissions to Finalis (subject to cost cap).

---

## 7. PAYG Edge Cases

**Test Class**: `TestPaygEdgeCases`

### Test 7.1: Exactly Hitting ARR Target
**Test Method**: `test_payg_exactly_hitting_arr_target`

| Input | Value |
|-------|-------|
| Deal Size | $100,000 |
| Fixed Rate | 3% |
| ARR Target | $10,000 |
| Already Accumulated | $7,000 |

**Calculation**:
- Implied = $100,000 × 3% = $3,000
- ARR Remaining = $10,000 - $7,000 = $3,000
- All $3,000 goes to ARR → $0 excess

> **Note**: When ARR is fully covered (even if exactly), `entered_commissions_mode = True`.
> The next deal will have all commissions go directly to Finalis.

### Test 7.2: Entering Commissions Mode
**Test Method**: `test_payg_entering_commissions_mode`

| Input | Value |
|-------|-------|
| Deal Size | $100,000 |
| Fixed Rate | 5% |
| ARR Target | $10,000 |
| Already Accumulated | $8,000 |

**Calculation**:
- Implied = $5,000
- ARR Remaining = $2,000
- ARR Contribution = $2,000
- Excess to Finalis = **$3,000**
- `entered_commissions_mode` = **True**

### Test 7.3: Already in Commissions Mode
**Test Method**: `test_payg_already_in_commissions_mode`

| Input | Value |
|-------|-------|
| Deal Size | $200,000 |
| Fixed Rate | 4% |
| Already in Commissions Mode | Yes |

**Calculation**:
- Implied = $8,000
- ARR Contribution = $0 (already covered)
- All $8,000 goes to Finalis as excess

---

## 8. Advance Fees (Multiple Payments)

**Test Class**: `TestAdvanceFeesMultiplePayments`

### Business Rule
When a deal generates enough implied commission, it can prepay multiple future subscription payments in order.

### Test 8.1: Covering Multiple Payments
**Test Method**: `test_advance_fees_cover_multiple_payments`

| Input | Value |
|-------|-------|
| Deal Size | $800,000 |
| Fixed Rate | 10% |
| Future Payments | P1: $25k, P2: $25k, P3: $15k owed, P4: $25k |

**Calculation**:
- Implied = $80,000
- Total Future Owed = $90,000
- Advance Created = $80,000 (can't exceed implied)

**Payment Updates**:
| Payment | Original Owed | After Advance |
|---------|---------------|---------------|
| P1 | $25,000 | $0 |
| P2 | $25,000 | $0 |
| P3 | $15,000 | $0 |
| P4 | $25,000 | $10,000 remaining |

---

## 9. Partial Debt Collection

**Test Class**: `TestPartialDebtCollection`

### Business Rule
When collecting debt from a deal, priority is:
1. **Regular debt** (current_debt) - collected first
2. **Deferred subscription fees** - collected second

### Test 9.1: Partial Collection
**Test Method**: `test_partial_debt_and_deferred_collection`

| Input | Value |
|-------|-------|
| Deal Size | $50,000 |
| Fixed Rate | 5% |
| Current Debt | $30,000 |
| Deferred Fees | $40,000 |

**Calculation**:
- Deal can only cover $50,000
- First: Pay all regular debt = $30,000
- Then: Pay partial deferred = $20,000
- Remaining deferred = **$20,000**

---

## 10. Maximum Complexity (All Features)

**Test Class**: `TestMaximumComplexity`

### Business Rule
This test validates that all features work correctly together in a complex real-world scenario.

### Test 10.1: All Fees Combined
**Test Method**: `test_all_fees_combined`

| Input | Value |
|-------|-------|
| Success Fees | $1,000,000 |
| External Retainer (Deducted) | $50,000 |
| Historical Production | $1,500,000 |
| Lehman Tiers | 0-$2M @ 5%, $2M+ @ 3% |
| Current Credit | $10,000 |
| Current Debt | $15,000 |
| Deferred Fees | $25,000 |
| Future Payment | $25,000 owed |
| Distribution Fee | Yes |
| Sourcing Fee | Yes |
| FINRA Fee | Yes |

**Expected Results**:

| Calculation | Value | Notes |
|-------------|-------|-------|
| Total Deal Value | $1,050,000 | Includes retainer |
| Implied Total | $41,500 | Lehman with history |
| Distribution Fee | $100,000 | 10% of success fees only |
| Sourcing Fee | $100,000 | 10% of success fees only |
| FINRA Fee | ~$4,969 | 0.4732% of total |
| Debt Collected | $40,000 | $15k + $25k deferred |

**Lehman Breakdown**:
- Historical $1.5M in Tier 1
- New $1.05M: $500k @ 5% + $550k @ 3% = $25,000 + $16,500 = **$41,500**

---

## Appendix: Business Logic Decisions

| # | Issue | Decision |
|---|-------|----------|
| 1 | PAYG `finalis_commissions_this_deal` semantics | Total to Finalis (includes ARR portion) |
| 2 | PAYG `entered_commissions_mode` when exactly hitting ARR | True (ARR fully covered) |
| 3 | Distribution/Sourcing with external retainer | Use total (consistent with all other fees) |

---

## Sync Checklist

When modifying `tests/test_integration_scenarios.py`:

- [ ] Update corresponding section in this document
- [ ] Update "Last synced" date at top
- [ ] If adding new test class, add new section
- [ ] If removing test, remove from this document
- [ ] Review "Pending Business Decisions" appendix
