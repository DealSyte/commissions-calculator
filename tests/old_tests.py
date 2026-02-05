
Python
from finalis_engine import FinalisEngine

engine = FinalisEngine()

# ============================================================
# TEST 1: PAYG with Lehman
# ============================================================
test1 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [], "total_paid_this_contract_year": 0,
        "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman", "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 7500000, "rate": 0.0047},
            {"lower_bound": 7500000.01, "upper_bound": None, "rate": 0.0027}
        ],
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True, "annual_subscription": 102000,
        "contract_start_date": "2025-12-19"
    },
    "new_deal": {
        "deal_name": "Test 1 - PAYG Lehman", "success_fees": 5000000,
        "deal_date": "2025-12-19", "is_deal_exempt": False,
        "is_distribution_fee_true": False, "is_sourcing_fee_true": False,
        "has_finra_fee": False, "has_external_retainer": False,
        "external_retainer": 0, "has_preferred_rate": False, "preferred_rate": None
    }
}

r1 = engine.process_deal(test1)
implied1 = r1['calculations']['implied_total']  # 5M * 0.47% = 23,500
net1 = r1['calculations']['net_payout_to_client']  # 5M - 23,500 = 4,976,500
pass1 = (net1 == 4976500 and implied1 == 23500)

print("TEST 1: PAYG + Lehman")
print(f"  Implied: ${implied1:,.2f} | Net: ${net1:,.2f}")
print(f"  {'✅ PASSED' if pass1 else '❌ FAILED'}\n")

# ============================================================
# TEST 2: Fixed Rate (no-PAYG) with credit
# ============================================================
test2 = {
    "state": {
        "current_credit": 50000, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [
            {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 25000, "amount_paid": 0}
        ],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.10, "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False, "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Test 2 - Fixed + Credit", "success_fees": 200000,
        "deal_date": "2025-03-15", "is_deal_exempt": False,
        "is_distribution_fee_true": False, "is_sourcing_fee_true": False,
        "has_finra_fee": True, "has_external_retainer": False,
        "external_retainer": 0, "has_preferred_rate": False, "preferred_rate": None
    }
}

r2 = engine.process_deal(test2)
implied2 = r2['calculations']['implied_total']  # 200k * 10% = 20,000
credit_used2 = r2['calculations']['credit_used_for_implied']  # min(20k, 50k) = 20,000
finra2 = r2['calculations']['finra_fee']  # 200k * 0.4732% = 946.40
net2 = r2['calculations']['net_payout_to_client']  # 200k - 946.40 = 199,053.60
pass2 = (implied2 == 20000 and credit_used2 == 20000 and abs(net2 - 199053.60) < 0.01)

print("TEST 2: Fixed Rate + Credit Absorption")
print(f"  Implied: ${implied2:,.2f} | Credit Used: ${credit_used2:,.2f} | FINRA: ${finra2:,.2f}")
print(f"  Net: ${net2:,.2f}")
print(f"  {'✅ PASSED' if pass2 else '❌ FAILED'}\n")

# ============================================================
# TEST 3: External Retainer (Deducted)
# ============================================================
test3 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05, "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True, "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Test 3 - External Retainer Deducted", "success_fees": 100000,
        "deal_date": "2025-03-15", "is_deal_exempt": False,
        "is_distribution_fee_true": False, "is_sourcing_fee_true": False,
        "has_finra_fee": False, "has_external_retainer": True,
        "external_retainer": 20000, "is_external_retainer_deducted": True,
        "has_preferred_rate": False, "preferred_rate": None
    }
}

r3 = engine.process_deal(test3)
total_value3 = r3['deal_summary']['total_deal_value']  # 100k + 20k = 120k
implied3 = r3['calculations']['implied_total']  # 120k * 5% = 6,000
net3 = r3['calculations']['net_payout_to_client']  # 100k - 6,000 = 94,000
pass3 = (total_value3 == 120000 and implied3 == 6000 and net3 == 94000)

print("TEST 3: External Retainer (Deducted)")
print(f"  Total Deal Value: ${total_value3:,.2f} | Implied: ${implied3:,.2f}")
print(f"  Net: ${net3:,.2f}")
print(f"  {'✅ PASSED' if pass3 else '❌ FAILED'}\n")

# ============================================================
# TEST 4: Lehman Tiers (non-PAYG) with Advance Fees
# ============================================================
test4 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [
            {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 10000, "amount_paid": 0},
            {"payment_id": "p2", "due_date": "2025-12-31", "amount_due": 10000, "amount_paid": 0}
        ],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman", "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
            {"lower_bound": 1000000.01, "upper_bound": None, "rate": 0.03}
        ],
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False, "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Test 4 - Lehman + Advance Fees", "success_fees": 500000,
        "deal_date": "2025-03-15", "is_deal_exempt": False,
        "is_distribution_fee_true": False, "is_sourcing_fee_true": False,
        "has_finra_fee": False, "has_external_retainer": False,
        "external_retainer": 0, "has_preferred_rate": False, "preferred_rate": None
    }
}

r4 = engine.process_deal(test4)
implied4 = r4['calculations']['implied_total']  # 500k * 5% = 25,000
advance4 = r4['calculations']['advance_fees_created']  # min(25k, 20k) = 20,000
net4 = r4['calculations']['net_payout_to_client']  # 500k - 20k = 480,000
pass4 = (implied4 == 25000 and advance4 == 20000 and net4 == 480000)

print("TEST 4: Lehman + Advance Fees")
print(f"  Implied: ${implied4:,.2f} | Advance Created: ${advance4:,.2f}")
print(f"  Net: ${net4:,.2f}")
print(f"  {'✅ PASSED' if pass4 else '❌ FAILED'}\n")

# ============================================================
# TEST 5: Distribution + Sourcing + FINRA + Debt
# ============================================================
test5 = {
    "state": {
        "current_credit": 0, "current_debt": 5000, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.08, "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False, "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Test 5 - All Fees + Debt", "success_fees": 100000,
        "deal_date": "2025-03-15", "is_deal_exempt": False,
        "is_distribution_fee_true": True, "is_sourcing_fee_true": True,
        "has_finra_fee": True, "has_external_retainer": False,
        "external_retainer": 0, "has_preferred_rate": False, "preferred_rate": None
    }
}

r5 = engine.process_deal(test5)
finra5 = r5['calculations']['finra_fee']  # 100k * 0.4732% = 473.20
dist5 = r5['calculations']['distribution_fee']  # 100k * 10% = 10,000
sourc5 = r5['calculations']['sourcing_fee']  # 100k * 10% = 10,000
debt5 = r5['calculations']['debt_collected']  # 5,000
implied5 = r5['calculations']['implied_total']  # 100k * 8% = 8,000
credit_used5 = r5['calculations']['credit_used_for_implied']  # debt becomes credit = 5k, used 5k
net5 = r5['calculations']['net_payout_to_client']  
# 100k - 5k(debt) - 473.20(finra) - 10k(dist) - 10k(sourc) = 74,526.80
expected_net5 = 100000 - 5000 - 473.20 - 10000 - 10000
pass5 = (abs(net5 - expected_net5) < 0.01 and debt5 == 5000)

print("TEST 5: All Fees (FINRA + Dist + Sourc) + Debt Collection")
print(f"  FINRA: ${finra5:,.2f} | Dist: ${dist5:,.2f} | Sourc: ${sourc5:,.2f}")
print(f"  Debt Collected: ${debt5:,.2f} | Implied: ${implied5:,.2f}")
print(f"  Credit Used: ${credit_used5:,.2f} | Net: ${net5:,.2f}")
print(f"  {'✅ PASSED' if pass5 else '❌ FAILED'}\n")

# ============================================================
# Summary
# ============================================================
print("=" * 50)
all_passed = all([pass1, pass2, pass3, pass4, pass5])
print(f"FINAL RESULT: {'✅ ALL TESTS PASSED!' if all_passed else '❌ SOME TESTS FAILED'}")
print("=" * 50)


from finalis_engine import FinalisEngine

engine = FinalisEngine()

print("=" * 60)
print("ADDITIONAL TEST SUITE - EDGE CASES & COMPLEX SCENARIOS")
print("=" * 60 + "\n")

# ============================================================
# TEST 6: PAYG - Entering Commissions Mode
# ============================================================
print("TEST 6: PAYG - Entering Commissions Mode")
print("-" * 60)
 
test6 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0,
        "payg_commissions_accumulated": 8000  # Already paid $8k toward ARR
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,  # $10k ARR
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "PAYG - Entering Commissions", 
        "success_fees": 100000,
        "deal_date": "2025-03-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r6 = engine.process_deal(test6)
implied6 = r6['calculations']['implied_total']  # 100k * 5% = 5,000
arr_comm6 = r6['payg_tracking']['arr_commissions']  # min(5k, 2k remaining) = 2,000
finalis_comm6 = r6['payg_tracking']['finalis_commissions_excess']  # 5k - 2k = 3,000
entered_mode6 = r6['state_changes']['entered_commissions_mode']  # Should be TRUE
pass6 = (arr_comm6 == 2000 and finalis_comm6 == 3000 and entered_mode6 == True)
 
print(f"  Implied: ${implied6:,.2f}")
print(f"  ARR Commissions: ${arr_comm6:,.2f} (covers remaining $2k)")
print(f"  Finalis Commissions: ${finalis_comm6:,.2f}")
print(f"  Entered Commissions Mode: {entered_mode6}")
print(f"  {'✅ PASSED' if pass6 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 7: PAYG - Already in Commissions Mode
# ============================================================
print("TEST 7: PAYG - Already in Commissions Mode")
print("-" * 60)
 
test7 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,  # Already in mode
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 15000, "total_paid_all_time": 15000,
        "payg_commissions_accumulated": 15000  # Already covered ARR + $5k excess
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.04,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "PAYG - Pure Commissions", 
        "success_fees": 200000,
        "deal_date": "2025-06-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r7 = engine.process_deal(test7)
implied7 = r7['calculations']['implied_total']  # 200k * 4% = 8,000
arr_comm7 = r7['payg_tracking']['arr_commissions']  # 0 (ARR already covered)
finalis_comm7 = r7['payg_tracking']['finalis_commissions_excess']  # All 8k is excess
pass7 = (arr_comm7 == 0 and finalis_comm7 == 8000)
 
print(f"  Implied: ${implied7:,.2f}")
print(f"  ARR Commissions: ${arr_comm7:,.2f} (already covered)")
print(f"  Finalis Commissions: ${finalis_comm7:,.2f} (100% excess)")
print(f"  {'✅ PASSED' if pass7 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 8: Cost Cap - Annual Type (Partial)
# ============================================================
print("TEST 8: Cost Cap - Annual Type (Partial Cap)")
print("-" * 60)
 
test8 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 90000,  # Already paid $90k this year
        "total_paid_all_time": 90000
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 50000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "annual",
        "cost_cap_amount": 100000  # $100k annual cap
    },
    "new_deal": {
        "deal_name": "Cost Cap - Annual Partial", 
        "success_fees": 500000,
        "deal_date": "2025-11-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r8 = engine.process_deal(test8)
implied8 = r8['calculations']['implied_total']  # 500k * 5% = 25,000
finalis_before_cap8 = r8['calculations']['finalis_commissions_before_cap']  # 25,000
finalis_after_cap8 = r8['calculations']['finalis_commissions']  # Only 10k fits (90k + 10k = 100k cap)
not_charged8 = r8['calculations']['amount_not_charged_due_to_cap']  # 15,000
pass8 = (finalis_after_cap8 == 10000 and not_charged8 == 15000)
 
print(f"  Implied: ${implied8:,.2f}")
print(f"  Before Cap: ${finalis_before_cap8:,.2f}")
print(f"  After Cap: ${finalis_after_cap8:,.2f}")
print(f"  Not Charged: ${not_charged8:,.2f}")
print(f"  {'✅ PASSED' if pass8 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 9: Cost Cap - Total Type (Fully Hit)
# ============================================================
print("TEST 9: Cost Cap - Total Type (Fully Hit)")
print("-" * 60)
 
test9 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 50000,
        "total_paid_all_time": 250000  # Already paid $250k lifetime
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.06,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2023-01-01",
        "cost_cap_type": "total",
        "cost_cap_amount": 250000  # $250k lifetime cap
    },
    "new_deal": {
        "deal_name": "Cost Cap - Total Hit", 
        "success_fees": 1000000,
        "deal_date": "2025-12-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r9 = engine.process_deal(test9)
implied9 = r9['calculations']['implied_total']  # 1M * 6% = 60,000
finalis_after_cap9 = r9['calculations']['finalis_commissions']  # 0 (cap fully hit)
not_charged9 = r9['calculations']['amount_not_charged_due_to_cap']  # 60,000
pass9 = (finalis_after_cap9 == 0 and not_charged9 == 60000)
 
print(f"  Implied: ${implied9:,.2f}")
print(f"  After Cap: ${finalis_after_cap9:,.2f} (cap fully hit)")
print(f"  Not Charged: ${not_charged9:,.2f}")
print(f"  {'✅ PASSED' if pass9 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 10: Preferred Rate Override
# ============================================================
print("TEST 10: Preferred Rate Override")
print("-" * 60)
 
test10 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman",  # Contract has Lehman
        "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
            {"lower_bound": 1000000.01, "upper_bound": None, "rate": 0.03}
        ],
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Preferred Rate Override", 
        "success_fees": 2000000,
        "deal_date": "2025-03-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": True,  # Override with preferred
        "preferred_rate": 0.02  # 2% instead of Lehman
    }
}
 
r10 = engine.process_deal(test10)
implied10 = r10['calculations']['implied_total']  # 2M * 2% = 40,000 (NOT Lehman calculation)
pass10 = (implied10 == 40000)
 
print(f"  Success Fees: $2,000,000")
print(f"  Contract Rate: Lehman (would be ~$80k)")
print(f"  Preferred Rate: 2%")
print(f"  Implied (with override): ${implied10:,.2f}")
print(f"  {'✅ PASSED' if pass10 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 11: Deal Exempt (1.5% flat)
# ============================================================
print("TEST 11: Deal Exempt (1.5% flat)")
print("-" * 60)
 
test11 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", 
        "fixed_rate": 0.05,  # Contract is 5%
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "M&A Exempt Deal", 
        "success_fees": 10000000,
        "deal_date": "2025-03-15", 
        "is_deal_exempt": True,  # Exempt = 1.5% flat
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r11 = engine.process_deal(test11)
implied11 = r11['calculations']['implied_total']  # 10M * 1.5% = 150,000 (NOT 5%)
pass11 = (implied11 == 150000)
 
print(f"  Success Fees: $10,000,000")
print(f"  Contract Rate: 5%")
print(f"  Deal Exempt: 1.5%")
print(f"  Implied: ${implied11:,.2f}")
print(f"  {'✅ PASSED' if pass11 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 12: External Retainer NOT Deducted
# ============================================================
print("TEST 12: External Retainer NOT Deducted")
print("-" * 60)
 
test12 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Retainer NOT Deducted", 
        "success_fees": 500000,
        "deal_date": "2025-03-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": True,
        "external_retainer": 100000,
        "is_external_retainer_deducted": False,  # NOT deducted
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r12 = engine.process_deal(test12)
total_value12 = r12['deal_summary']['total_deal_value']  # 500k (retainer ignored)
implied12 = r12['calculations']['implied_total']  # 500k * 5% = 25,000
finalis12 = r12['calculations']['finalis_commissions']  # 25,000
net12 = r12['calculations']['net_payout_to_client']  # 500k - 25k = 475,000
pass12 = (total_value12 == 500000 and implied12 == 25000 and net12 == 475000)
 
print(f"  Success Fees: $500,000")
print(f"  External Retainer: $100,000 (NOT deducted)")
print(f"  Total for Calculations: ${total_value12:,.2f}")
print(f"  Implied: ${implied12:,.2f}")
print(f"  Net Payout: ${net12:,.2f}")
print(f"  {'✅ PASSED' if pass12 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 13: Deferred Backend Collection
# ============================================================
print("TEST 13: Deferred Backend Collection")
print("-" * 60)
 
test13 = {
    "state": {
        "current_credit": 0, 
        "current_debt": 0, 
        "deferred_subscription_fee": 50000,  # $50k deferred
        "deferred_schedule": None,
        "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, 
        "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Deferred Collection", 
        "success_fees": 200000,
        "deal_date": "2025-03-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r13 = engine.process_deal(test13)
deferred_collected13 = r13['calculations']['deferred_collected']  # 50,000
final_deferred13 = r13['state_changes']['final_deferred']  # 0
pass13 = (deferred_collected13 == 50000 and final_deferred13 == 0)
 
print(f"  Initial Deferred: $50,000")
print(f"  Deferred Collected: ${deferred_collected13:,.2f}")
print(f"  Final Deferred: ${final_deferred13:,.2f}")
print(f"  {'✅ PASSED' if pass13 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 14: Multi-Year Deferred Schedule
# ============================================================
print("TEST 14: Multi-Year Deferred Schedule (Year 2)")
print("-" * 60)
 
test14 = {
    "state": {
        "current_credit": 0, 
        "current_debt": 0, 
        "deferred_subscription_fee": 0,
        "deferred_schedule": [
            {"year": 1, "amount": 30000},
            {"year": 2, "amount": 40000},  # Currently in year 2
            {"year": 3, "amount": 50000}
        ],
        "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, 
        "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2024-01-01"  # Started last year
    },
    "new_deal": {
        "deal_name": "Multi-Year Deferred Y2", 
        "success_fees": 300000,
        "deal_date": "2025-06-15",  # Year 2 of contract
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r14 = engine.process_deal(test14)
deferred_collected14 = r14['calculations']['deferred_collected']  # Should collect Year 2: 40,000
contract_year14 = r14['state_changes']['contract_year']  # Should be 2
pass14 = (deferred_collected14 == 40000 and contract_year14 == 2)
 
print(f"  Contract Year: {contract_year14}")
print(f"  Deferred Year 2: $40,000")
print(f"  Deferred Collected: ${deferred_collected14:,.2f}")
print(f"  {'✅ PASSED' if pass14 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 15: Lehman Multi-Tier with Historical Production
# ============================================================
print("TEST 15: Lehman with Historical Production")
print("-" * 60)
 
test15 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman",
        "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
            {"lower_bound": 1000000.01, "upper_bound": 5000000, "rate": 0.04},
            {"lower_bound": 5000000.01, "upper_bound": None, "rate": 0.03}
        ],
        "accumulated_success_fees_before_this_deal": 4000000,  # Already did $4M
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Lehman with History", 
        "success_fees": 3000000,  # New $3M deal
        "deal_date": "2025-06-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r15 = engine.process_deal(test15)
# Historical: $4M (past Tier 1, in Tier 2)
# New deal: $3M
#   - First $1M of deal in Tier 2 (4M→5M) @ 4% = $40k
#   - Next $2M of deal in Tier 3 (5M→7M) @ 3% = $60k
#   - Total = $100k
implied15 = r15['calculations']['implied_total']
pass15 = (implied15 == 100000)
 
print(f"  Historical Production: $4,000,000")
print(f"  New Deal: $3,000,000")
print(f"  Tier 2 portion (4M→5M): $1M @ 4% = $40k")
print(f"  Tier 3 portion (5M→7M): $2M @ 3% = $60k")
print(f"  Implied Total: ${implied15:,.2f}")
print(f"  {'✅ PASSED' if pass15 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 16: PAYG + Cost Cap Combined
# ============================================================
print("TEST 16: PAYG + Cost Cap Combined")
print("-" * 60)
 
test16 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0,
        "total_paid_all_time": 0,
        "payg_commissions_accumulated": 0
    },
    "contract": {
        "rate_type": "lehman",
        "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
            {"lower_bound": 1000000.01, "upper_bound": 5000000, "rate": 0.04},
            {"lower_bound": 5000000.01, "upper_bound": None, "rate": 0.03}
        ],
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "total",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "PAYG + Cost Cap", 
        "success_fees": 3000000,
        "deal_date": "2025-12-19", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r16 = engine.process_deal(test16)
# Lehman: $50k + $80k = $130k
# Cost cap: $100k
# Amount not charged: $130k - $100k = $30k
implied16 = r16['calculations']['implied_total']  # 130,000
finalis16 = r16['calculations']['finalis_commissions']  # 100,000 (capped)
not_charged16 = r16['calculations']['amount_not_charged_due_to_cap']  # 30,000
arr_comm16 = r16['payg_tracking']['arr_commissions']  # 10,000
finalis_excess16 = r16['payg_tracking']['finalis_commissions_excess']  # 90,000
pass16 = (implied16 == 130000 and finalis16 == 100000 and not_charged16 == 30000 
          and arr_comm16 == 10000 and finalis_excess16 == 90000)
 
print(f"  Lehman Implied: ${implied16:,.2f}")
print(f"  Cost Cap: $100,000")
print(f"  Finalis Commissions: ${finalis16:,.2f}")
print(f"  Not Charged: ${not_charged16:,.2f}")
print(f"  ARR Commissions: ${arr_comm16:,.2f}")
print(f"  Finalis Excess: ${finalis_excess16:,.2f}")
print(f"  {'✅ PASSED' if pass16 else '❌ FAILED'}\n")
 
# ============================================================
# Summary
# ============================================================
print("=" * 60)
print("ADDITIONAL TESTS SUMMARY")
print("=" * 60)
 
all_tests = [pass6, pass7, pass8, pass9, pass10, pass11, pass12, pass13, pass14, pass15, pass16]
passed = sum(all_tests)
total = len(all_tests)
 
print(f"Tests Passed: {passed}/{total}")
if passed == total:
    print("✅ ALL ADDITIONAL TESTS PASSED!")
else:
    print(f"❌ {total - passed} TEST(S) FAILED")
print("=" * 60)


📋 TEST CASES COVERED:


Scenario
6
PAYG entering commissions mode (partial ARR coverage)
7
PAYG already in commissions mode (100% excess)
8
Cost cap annual type (partial hit)
9
Cost cap total type (fully hit)
10
Preferred rate override
11
Deal exempt (M&A 1.5%)
12
External retainer NOT deducted
13
Deferred backend collection
14
Multi-year deferred schedule
15
Lehman with historical production
16
PAYG + Cost Cap combined



More tests:





from finalis_engine import FinalisEngine
 
engine = FinalisEngine()
 
print("=" * 60)
print("ADVANCED TEST SUITE - COMPLEX EDGE CASES")
print("=" * 60 + "\n")
 
# ============================================================
# TEST 17: PAYG Cost Cap - Multiple Deals (Sequential)
# ============================================================
print("TEST 17: PAYG Cost Cap - Multiple Deals Hitting Cap Gradually")
print("-" * 60)
 
# Deal 1: Uses $50k of $100k cap
test17a = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0,
        "payg_commissions_accumulated": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "total",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "PAYG Cap Deal 1", 
        "success_fees": 1000000,
        "deal_date": "2025-03-01", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r17a = engine.process_deal(test17a)
# Implied: $50k, all fits in cap, ARR covered
implied17a = r17a['calculations']['implied_total']  # 50,000
finalis17a = r17a['calculations']['finalis_commissions']  # 50,000
payg_acc17a = r17a['updated_contract_state']['payg_commissions_accumulated']  # 50,000
 
# Deal 2: Uses another $40k (total $90k)
test17b = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 50000,
        "total_paid_all_time": 50000,
        "payg_commissions_accumulated": 50000
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 1000000,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "total",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "PAYG Cap Deal 2", 
        "success_fees": 800000,
        "deal_date": "2025-06-01", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r17b = engine.process_deal(test17b)
# Implied: $40k, all fits (50k + 40k = 90k < 100k cap)
implied17b = r17b['calculations']['implied_total']  # 40,000
finalis17b = r17b['calculations']['finalis_commissions']  # 40,000
not_charged17b = r17b['calculations']['amount_not_charged_due_to_cap']  # 0
 
# Deal 3: Tries to use $30k but only $10k left in cap
test17c = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 90000,
        "total_paid_all_time": 90000,
        "payg_commissions_accumulated": 90000
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 1800000,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "total",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "PAYG Cap Deal 3", 
        "success_fees": 600000,
        "deal_date": "2025-09-01", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r17c = engine.process_deal(test17c)
# Implied: $30k, but only $10k fits in cap
implied17c = r17c['calculations']['implied_total']  # 30,000
finalis17c = r17c['calculations']['finalis_commissions']  # 10,000
not_charged17c = r17c['calculations']['amount_not_charged_due_to_cap']  # 20,000
pass17 = (finalis17a == 50000 and finalis17b == 40000 and finalis17c == 10000 and not_charged17c == 20000)
 
print(f"  Deal 1: Implied ${implied17a:,.2f} → Charged ${finalis17a:,.2f}")
print(f"  Deal 2: Implied ${implied17b:,.2f} → Charged ${finalis17b:,.2f}")
print(f"  Deal 3: Implied ${implied17c:,.2f} → Charged ${finalis17c:,.2f} (cap hit)")
print(f"  Deal 3 Not Charged: ${not_charged17c:,.2f}")
print(f"  {'✅ PASSED' if pass17 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 18: Advance Fees Priority Over Commissions in Cap
# ============================================================
print("TEST 18: Cost Cap - Advance Fees Have Priority")
print("-" * 60)
 
test18 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [
            {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 50000, "amount_paid": 0},
            {"payment_id": "p2", "due_date": "2025-12-31", "amount_due": 50000, "amount_paid": 0}
        ],
        "total_paid_this_contract_year": 85000,  # Already paid $85k
        "total_paid_all_time": 85000
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.10,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01",
        "cost_cap_type": "annual",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "Advance Priority Test", 
        "success_fees": 500000,
        "deal_date": "2025-11-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r18 = engine.process_deal(test18)
# Implied: $50k
# Available in cap: $15k (100k - 85k)
# Advance fees created: $15k (uses all available cap)
# Finalis commissions: $0 (no space left)
# Not charged: $35k ($50k implied - $15k charged)
implied18 = r18['calculations']['implied_total']  # 50,000
advance18 = r18['calculations']['advance_fees_created']  # 15,000
finalis18 = r18['calculations']['finalis_commissions']  # 0
not_charged18 = r18['calculations']['amount_not_charged_due_to_cap']  # 35,000
pass18 = (advance18 == 15000 and finalis18 == 0 and not_charged18 == 35000)
 
print(f"  Implied: ${implied18:,.2f}")
print(f"  Cap Available: $15,000")
print(f"  Advance Fees: ${advance18:,.2f} (priority - uses all cap)")
print(f"  Finalis Commissions: ${finalis18:,.2f} (no space left)")
print(f"  Not Charged: ${not_charged18:,.2f}")
print(f"  {'✅ PASSED' if pass18 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 19: Lehman Crossing 3 Tiers in Single Deal
# ============================================================
print("TEST 19: Lehman Deal Crossing 3 Tiers")
print("-" * 60)
 
test19 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman",
        "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
            {"lower_bound": 1000000.01, "upper_bound": 5000000, "rate": 0.04},
            {"lower_bound": 5000000.01, "upper_bound": 10000000, "rate": 0.03},
            {"lower_bound": 10000000.01, "upper_bound": None, "rate": 0.02}
        ],
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Lehman 3-Tier Cross", 
        "success_fees": 12000000,  # $12M crosses 3 tiers
        "deal_date": "2025-06-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r19 = engine.process_deal(test19)
# Tier 1: $0-$1M @ 5% = $50,000
# Tier 2: $1M-$5M ($4M) @ 4% = $160,000
# Tier 3: $5M-$10M ($5M) @ 3% = $150,000
# Tier 4: $10M-$12M ($2M) @ 2% = $40,000
# Total: $400,000
implied19 = r19['calculations']['implied_total']
pass19 = (implied19 == 400000)
 
print(f"  Deal Size: $12,000,000")
print(f"  Tier 1 ($0-$1M): $1M @ 5% = $50,000")
print(f"  Tier 2 ($1M-$5M): $4M @ 4% = $160,000")
print(f"  Tier 3 ($5M-$10M): $5M @ 3% = $150,000")
print(f"  Tier 4 ($10M-$12M): $2M @ 2% = $40,000")
print(f"  Total Implied: ${implied19:,.2f}")
print(f"  {'✅ PASSED' if pass19 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 20: All Fees Combined (FINRA + Dist + Sourc + Debt + Deferred)
# ============================================================
print("TEST 20: Maximum Fee Complexity")
print("-" * 60)
 
test20 = {
    "state": {
        "current_credit": 10000,
        "current_debt": 15000, 
        "deferred_subscription_fee": 25000,
        "deferred_schedule": None,
        "is_in_commissions_mode": False,
        "future_subscription_fees": [
            {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 30000, "amount_paid": 5000}
        ],
        "total_paid_this_contract_year": 0, 
        "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "lehman",
        "fixed_rate": None,
        "lehman_tiers": [
            {"lower_bound": 0, "upper_bound": 2000000, "rate": 0.05},
            {"lower_bound": 2000000.01, "upper_bound": None, "rate": 0.03}
        ],
        "accumulated_success_fees_before_this_deal": 1500000,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Maximum Complexity", 
        "success_fees": 1000000,
        "deal_date": "2025-05-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": True,
        "is_sourcing_fee_true": True,
        "has_finra_fee": True, 
        "has_external_retainer": True,
        "external_retainer": 50000,
        "is_external_retainer_deducted": True,
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r20 = engine.process_deal(test20)
# Total for calc: $1M + $50k = $1,050,000
# FINRA: $1M * 0.4732% = $4,732
# Distribution: $1M * 10% = $100,000
# Sourcing: $1M * 10% = $100,000
# Debt collected: min($1M, $15k + $25k) = $40,000
# Lehman: 
#   - Historical: $1.5M (in Tier 1)
#   - New: $1.05M crosses to Tier 2
#   - Tier 1: $500k @ 5% = $25,000
#   - Tier 2: $550k @ 3% = $16,500
#   - Total: $41,500
# Credit from debt: $40k
# Credit total: $10k + $40k = $50k
# Implied after credit: $41,500 (credit > implied, so $0 implied remaining)
# Advance fees: Create from credit remaining
# Net payout: $1M - $4,732 - $100k - $100k - $40k = $755,268
 
finra20 = r20['calculations']['finra_fee']
dist20 = r20['calculations']['distribution_fee']
sourc20 = r20['calculations']['sourcing_fee']
debt20 = r20['calculations']['debt_collected']
implied20 = r20['calculations']['implied_total']
credit_used20 = r20['calculations']['credit_used_for_implied']
net20 = r20['calculations']['net_payout_to_client']
 
expected_finra = 4732.00
expected_dist = 100000
expected_sourc = 100000
expected_debt = 40000
expected_implied = 41500
expected_net = 1000000 - expected_finra - expected_dist - expected_sourc - expected_debt
 
pass20 = (abs(finra20 - expected_finra) < 1 and dist20 == expected_dist 
          and sourc20 == expected_sourc and debt20 == expected_debt
          and implied20 == expected_implied and abs(net20 - expected_net) < 1)
 
print(f"  Deal: $1,000,000 + $50k retainer = $1,050,000")
print(f"  FINRA: ${finra20:,.2f}")
print(f"  Distribution: ${dist20:,.2f}")
print(f"  Sourcing: ${sourc20:,.2f}")
print(f"  Debt Collected: ${debt20:,.2f} (regular + deferred)")
print(f"  Lehman Implied: ${implied20:,.2f}")
print(f"  Credit Used: ${credit_used20:,.2f}")
print(f"  Net Payout: ${net20:,.2f}")
print(f"  {'✅ PASSED' if pass20 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 21: Contract Year Boundary (Multi-Year Tracking)
# ============================================================
print("TEST 21: Contract Year Boundary - Annual Cap Reset")
print("-" * 60)
 
# Deal in Year 1
test21a = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 80000,
        "total_paid_all_time": 80000
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2024-01-01",
        "cost_cap_type": "annual",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "Year 1 Deal", 
        "success_fees": 600000,
        "deal_date": "2024-11-15",  # Year 1
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r21a = engine.process_deal(test21a)
# Implied: $30k, can only charge $20k (80k + 20k = 100k cap)
year21a = r21a['state_changes']['contract_year']  # 1
finalis21a = r21a['calculations']['finalis_commissions']  # 20,000
not_charged21a = r21a['calculations']['amount_not_charged_due_to_cap']  # 10,000
 
# Deal in Year 2 - Cap should reset
test21b = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0,  # Reset for new year
        "total_paid_all_time": 100000  # Cumulative
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 600000,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2024-01-01",
        "cost_cap_type": "annual",
        "cost_cap_amount": 100000
    },
    "new_deal": {
        "deal_name": "Year 2 Deal", 
        "success_fees": 600000,
        "deal_date": "2025-02-15",  # Year 2
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r21b = engine.process_deal(test21b)
# Implied: $30k, full $30k should be charged (new year, cap reset)
year21b = r21b['state_changes']['contract_year']  # 2
finalis21b = r21b['calculations']['finalis_commissions']  # 30,000
not_charged21b = r21b['calculations']['amount_not_charged_due_to_cap']  # 0
 
pass21 = (year21a == 1 and finalis21a == 20000 and not_charged21a == 10000
          and year21b == 2 and finalis21b == 30000 and not_charged21b == 0)
 
print(f"  Year 1 Deal:")
print(f"    Contract Year: {year21a}")
print(f"    Finalis: ${finalis21a:,.2f} (capped)")
print(f"    Not Charged: ${not_charged21a:,.2f}")
print(f"  Year 2 Deal:")
print(f"    Contract Year: {year21b}")
print(f"    Finalis: ${finalis21b:,.2f} (full - cap reset)")
print(f"    Not Charged: ${not_charged21b:,.2f}")
print(f"  {'✅ PASSED' if pass21 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 22: Preferred Rate + External Retainer Deducted
# ============================================================
print("TEST 22: Preferred Rate with External Retainer (Deducted)")
print("-" * 60)
 
test22 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": True,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", 
        "fixed_rate": 0.05,  # 5% standard
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 50000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Preferred + Retainer", 
        "success_fees": 2000000,
        "deal_date": "2025-06-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": True,
        "external_retainer": 300000,
        "is_external_retainer_deducted": True,
        "has_preferred_rate": True,
        "preferred_rate": 0.03  # 3% preferred (lower than 5%)
    }
}
 
r22 = engine.process_deal(test22)
# Total: $2M + $300k = $2.3M
# Preferred rate: 3%
# Implied: $2.3M * 3% = $69,000
total22 = r22['deal_summary']['total_deal_value']
implied22 = r22['calculations']['implied_total']
finalis22 = r22['calculations']['finalis_commissions']
pass22 = (total22 == 2300000 and implied22 == 69000 and finalis22 == 69000)
 
print(f"  Success Fees: $2,000,000")
print(f"  External Retainer: $300,000 (deducted)")
print(f"  Total: ${total22:,.2f}")
print(f"  Standard Rate: 5%")
print(f"  Preferred Rate: 3%")
print(f"  Implied: ${implied22:,.2f} (using preferred)")
print(f"  {'✅ PASSED' if pass22 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 23: Debt + Deferred Both Partial Collection
# ============================================================
print("TEST 23: Partial Debt + Deferred Collection")
print("-" * 60)
 
test23 = {
    "state": {
        "current_credit": 0,
        "current_debt": 30000,  # $30k regular debt
        "deferred_subscription_fee": 40000,  # $40k deferred
        "deferred_schedule": None,
        "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, 
        "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.05,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Partial Debt Collection", 
        "success_fees": 50000,  # Only $50k available
        "deal_date": "2025-03-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r23 = engine.process_deal(test23)
# Total debt: $30k + $40k = $70k
# Can collect: min($50k, $70k) = $50k
# First pays regular debt: $30k
# Then deferred: $20k (of $40k)
# Remaining debt: $0
# Remaining deferred: $20k
debt23 = r23['calculations']['debt_collected']  # 50,000
deferred_coll23 = r23['calculations']['deferred_collected']  # 20,000
final_debt23 = r23['state_changes']['final_debt']  # 0
final_deferred23 = r23['state_changes']['final_deferred']  # 20,000
pass23 = (debt23 == 50000 and deferred_coll23 == 20000 
          and final_debt23 == 0 and final_deferred23 == 20000)
 
print(f"  Initial Regular Debt: $30,000")
print(f"  Initial Deferred: $40,000")
print(f"  Total Owed: $70,000")
print(f"  Success Fees: $50,000")
print(f"  Debt Collected: ${debt23:,.2f}")
print(f"  Deferred Collected: ${deferred_coll23:,.2f}")
print(f"  Final Regular Debt: ${final_debt23:,.2f}")
print(f"  Final Deferred: ${final_deferred23:,.2f}")
print(f"  {'✅ PASSED' if pass23 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 24: Advance Fees Covering Multiple Payments
# ============================================================
print("TEST 24: Advance Fees Spanning Multiple Payments")
print("-" * 60)
 
test24 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [
            {"payment_id": "p1", "due_date": "2025-03-31", "amount_due": 25000, "amount_paid": 0},
            {"payment_id": "p2", "due_date": "2025-06-30", "amount_due": 25000, "amount_paid": 0},
            {"payment_id": "p3", "due_date": "2025-09-30", "amount_due": 25000, "amount_paid": 10000},
            {"payment_id": "p4", "due_date": "2025-12-31", "amount_due": 25000, "amount_paid": 0}
        ],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.10,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": False,
        "annual_subscription": 100000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "Multi-Payment Advance", 
        "success_fees": 800000,
        "deal_date": "2025-02-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r24 = engine.process_deal(test24)
# Implied: $80k
# Total owed in future: $25k + $25k + $15k + $25k = $90k
# Advance created: min($80k, $90k) = $80k
# Should fully pay p1 ($25k) and p2 ($25k) and p3 ($15k remaining) and partial p4 ($15k of $25k)
advance24 = r24['calculations']['advance_fees_created']  # 80,000
payments24 = r24['updated_future_payments']
p1_remaining = next(p['remaining'] for p in payments24 if p['payment_id'] == 'p1')
p2_remaining = next(p['remaining'] for p in payments24 if p['payment_id'] == 'p2')
p3_remaining = next(p['remaining'] for p in payments24 if p['payment_id'] == 'p3')
p4_remaining = next(p['remaining'] for p in payments24 if p['payment_id'] == 'p4')
pass24 = (advance24 == 80000 and p1_remaining == 0 and p2_remaining == 0 
          and p3_remaining == 0 and p4_remaining == 10000)
 
print(f"  Implied: $80,000")
print(f"  Advance Created: ${advance24:,.2f}")
print(f"  Payment 1 Remaining: ${p1_remaining:,.2f} (fully covered)")
print(f"  Payment 2 Remaining: ${p2_remaining:,.2f} (fully covered)")
print(f"  Payment 3 Remaining: ${p3_remaining:,.2f} (fully covered)")
print(f"  Payment 4 Remaining: ${p4_remaining:,.2f} (partial)")
print(f"  {'✅ PASSED' if pass24 else '❌ FAILED'}\n")
 
# ============================================================
# TEST 25: PAYG - Exactly Hitting ARR Target
# ============================================================
print("TEST 25: PAYG - Exactly Hitting ARR Target (No Excess)")
print("-" * 60)
 
test25 = {
    "state": {
        "current_credit": 0, "current_debt": 0, "deferred_subscription_fee": 0,
        "deferred_schedule": None, "is_in_commissions_mode": False,
        "future_subscription_fees": [],
        "total_paid_this_contract_year": 0, "total_paid_all_time": 0,
        "payg_commissions_accumulated": 7000  # Already paid $7k toward $10k ARR
    },
    "contract": {
        "rate_type": "fixed", "fixed_rate": 0.03,
        "lehman_tiers": None,
        "accumulated_success_fees_before_this_deal": 0,
        "is_pay_as_you_go": True,
        "annual_subscription": 10000,
        "contract_start_date": "2025-01-01"
    },
    "new_deal": {
        "deal_name": "PAYG Exact ARR", 
        "success_fees": 100000,
        "deal_date": "2025-06-15", 
        "is_deal_exempt": False,
        "is_distribution_fee_true": False, 
        "is_sourcing_fee_true": False,
        "has_finra_fee": False, 
        "has_external_retainer": False,
        "external_retainer": 0, 
        "has_preferred_rate": False, 
        "preferred_rate": None
    }
}
 
r25 = engine.process_deal(test25)
# Implied: $100k * 3% = $3,000
# ARR remaining: $10k - $7k = $3,000
# All implied goes to ARR, none to excess
implied25 = r25['calculations']['implied_total']  # 3,000
arr_comm25 = r25['payg_tracking']['arr_commissions']  # 3,000
finalis_excess25 = r25['payg_tracking']['finalis_commissions_excess']  # 0
entered_mode25 = r25['state_changes']['entered_commissions_mode']  # True (just hit ARR)
in_mode25 = r25['updated_contract_state']['is_in_commissions_mode']  # True
pass25 = (implied25 == 3000 and arr_comm25 == 3000 and finalis_excess25 == 0 
          and entered_mode25 == True and in_mode25 == True)
 
print(f"  Previous PAYG Commissions: $7,000")
print(f"  ARR Target: $10,000")
print(f"  Remaining to Cover: $3,000")
print(f"  Implied This Deal: ${implied25:,.2f}")
print(f"  ARR Commissions: ${arr_comm25:,.2f}")
print(f"  Finalis Excess: ${finalis_excess25:,.2f}")
print(f"  Entered Commissions Mode: {entered_mode25}")
print(f"  {'✅ PASSED' if pass25 else '❌ FAILED'}\n")
 
# ============================================================
# Summary
# ============================================================
print("=" * 60)
print("ADVANCED TESTS SUMMARY")
print("=" * 60)
 
all_tests = [pass17, pass18, pass19, pass20, pass21, pass22, pass23, pass24, pass25]
passed = sum(all_tests)
total = len(all_tests)
 
print(f"Tests Passed: {passed}/{total}")
if passed == total:
    print("✅ ALL ADVANCED TESTS PASSED!")
else:
    print(f"❌ {total - passed} TEST(S) FAILED")
print("=" * 60)

