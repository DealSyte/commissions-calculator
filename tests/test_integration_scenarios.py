"""
Integration Test Scenarios for Finalis Contract Engine

These tests are derived from business user test cases (old_tests.py) and
cover complex, real-world scenarios that validate end-to-end functionality.

Run with: python -m pytest tests/test_integration_scenarios.py -v

IMPORTANT: This file has a companion business summary document:
    docs/test_scenarios_business_summary.md

When adding or modifying tests, please update the business summary document
to keep them in sync. The summary provides plain-English explanations of
each test scenario for business stakeholders.
"""


import pytest

from engine import DealProcessor


class TestPreferredRateOverride:
    """Test preferred rate overrides contract rate."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_preferred_rate_overrides_lehman(self, processor):
        """Preferred rate should override Lehman tiers."""
        input_data = {
            "contract": {
                "rate_type": "lehman",
                "lehman_tiers": [
                    {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
                    {"lower_bound": 1000000.01, "upper_bound": None, "rate": 0.03}
                ],
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Preferred Rate Override",
                "success_fees": 2000000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False,
                "has_preferred_rate": True,
                "preferred_rate": 0.02  # 2% instead of Lehman
            }
        }
        result = processor.process_from_dict(input_data)

        # Lehman would be: $1M × 5% + $1M × 3% = $80,000
        # Preferred rate: $2M × 2% = $40,000
        assert result["calculations"]["implied_total"]["value"] == 40000.0

    def test_preferred_rate_overrides_fixed(self, processor):
        """Preferred rate should override fixed rate."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Preferred Override Fixed",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False,
                "has_preferred_rate": True,
                "preferred_rate": 0.03
            }
        }
        result = processor.process_from_dict(input_data)

        # Fixed would be 5%, preferred is 3%
        assert result["calculations"]["implied_total"]["value"] == 3000.0


class TestDealExempt:
    """Test deal exempt rate (1.5% flat for M&A)."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_deal_exempt_uses_1_5_percent(self, processor):
        """Deal exempt should use 1.5% flat rate."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,  # Contract is 5%
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "M&A Exempt Deal",
                "success_fees": 10000000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": True,  # Exempt = 1.5% flat
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # 5% would be $500k, but exempt is 1.5%
        assert result["calculations"]["implied_total"]["value"] == 150000.0


class TestExternalRetainer:
    """Test external retainer handling."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_external_retainer_deducted(self, processor):
        """External retainer deducted adds to success fees for calculation."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Retainer Deducted",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False,
                "has_external_retainer": True,
                "external_retainer": 20000,
                "is_external_retainer_deducted": True
            }
        }
        result = processor.process_from_dict(input_data)

        # Total: $100k + $20k = $120k
        # Implied: $120k × 5% = $6,000
        assert result["deal_summary"]["total_deal_value"] == 120000.0
        assert result["calculations"]["implied_total"]["value"] == 6000.0

    def test_external_retainer_not_deducted(self, processor):
        """External retainer NOT deducted is ignored in calculations."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Retainer NOT Deducted",
                "success_fees": 500000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False,
                "has_external_retainer": True,
                "external_retainer": 100000,
                "is_external_retainer_deducted": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Retainer ignored: $500k (not $600k)
        # Implied: $500k × 5% = $25,000
        assert result["deal_summary"]["total_deal_value"] == 500000.0
        assert result["calculations"]["implied_total"]["value"] == 25000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 25000.0


class TestLehmanWithHistoricalProduction:
    """Test Lehman tiers with historical production."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_lehman_starting_mid_tier(self, processor):
        """New deal starts calculation mid-tier based on historical."""
        input_data = {
            "contract": {
                "rate_type": "lehman",
                "lehman_tiers": [
                    {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
                    {"lower_bound": 1000000.01, "upper_bound": 5000000, "rate": 0.04},
                    {"lower_bound": 5000000.01, "upper_bound": None, "rate": 0.03}
                ],
                "accumulated_success_fees_before_this_deal": 4000000,  # Already did $4M
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Lehman with History",
                "success_fees": 3000000,  # New $3M deal
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Historical: $4M (past Tier 1, in Tier 2)
        # New deal: $3M
        #   - First $1M of deal in Tier 2 (4M→5M) @ 4% = $40k
        #   - Next $2M of deal in Tier 3 (5M→7M) @ 3% = $60k
        #   - Total = $100k
        assert result["calculations"]["implied_total"]["value"] == 100000.0

    def test_lehman_crossing_multiple_tiers(self, processor):
        """Single deal crosses 3+ tiers."""
        input_data = {
            "contract": {
                "rate_type": "lehman",
                "lehman_tiers": [
                    {"lower_bound": 0, "upper_bound": 1000000, "rate": 0.05},
                    {"lower_bound": 1000000.01, "upper_bound": 5000000, "rate": 0.04},
                    {"lower_bound": 5000000.01, "upper_bound": 10000000, "rate": 0.03},
                    {"lower_bound": 10000000.01, "upper_bound": None, "rate": 0.02}
                ],
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Lehman 3-Tier Cross",
                "success_fees": 12000000,  # $12M crosses 3 tiers
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Tier 1: $0-$1M @ 5% = $50,000
        # Tier 2: $1M-$5M ($4M) @ 4% = $160,000
        # Tier 3: $5M-$10M ($5M) @ 3% = $150,000
        # Tier 4: $10M-$12M ($2M) @ 2% = $40,000
        # Total: $400,000
        assert result["calculations"]["implied_total"]["value"] == 400000.0


class TestCostCapScenarios:
    """Test cost cap edge cases."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_annual_cap_partial_hit(self, processor):
        """Annual cap limits charges when partially exceeded."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01",
                "cost_cap_type": "annual",
                "cost_cap_amount": 100000
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 90000,  # Already paid $90k
                "total_paid_all_time": 90000
            },
            "deal": {
                "deal_name": "Cost Cap - Annual Partial",
                "success_fees": 500000,
                "deal_date": "2025-11-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $25k
        # Available in cap: $10k (100k - 90k)
        # Commissions: $10k
        # Not charged: $15k
        assert result["calculations"]["implied_total"]["value"] == 25000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 10000.0
        assert result["calculations"]["amount_not_charged_due_to_cap"]["value"] == 15000.0

    def test_total_cap_fully_hit(self, processor):
        """Total (lifetime) cap fully exhausted means zero commissions."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.06,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2023-01-01",
                "cost_cap_type": "total",
                "cost_cap_amount": 250000
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 50000,
                "total_paid_all_time": 250000  # Cap fully used
            },
            "deal": {
                "deal_name": "Cost Cap - Total Hit",
                "success_fees": 1000000,
                "deal_date": "2025-12-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $60k
        # Available in cap: $0
        # All not charged
        assert result["calculations"]["implied_total"]["value"] == 60000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 0
        assert result["calculations"]["amount_not_charged_due_to_cap"]["value"] == 60000.0

    def test_advance_fees_have_priority_in_cap(self, processor):
        """Advance fees are created before cost cap is applied to commissions.

        Note: Cost cap applies to Finalis commissions, not advance subscription prepayments.
        Advance fees are subscriptions being prepaid, which is a separate category.
        """
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.10,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01",
                "cost_cap_type": "annual",
                "cost_cap_amount": 100000
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [
                    {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 50000, "amount_paid": 0},
                    {"payment_id": "p2", "due_date": "2025-12-31", "amount_due": 50000, "amount_paid": 0}
                ],
                "total_paid_this_contract_year": 85000,  # Only $15k left in cap
                "total_paid_all_time": 85000
            },
            "deal": {
                "deal_name": "Advance Priority Test",
                "success_fees": 500000,
                "deal_date": "2025-11-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $50k
        # Subscription owed: $100k
        # Advance fees = min(implied, owed) = $50k (goes to prepay subscription)
        # Commissions: $0 (all implied used for advance)
        # Cost cap doesn't limit subscription prepayments
        assert result["calculations"]["implied_total"]["value"] == 50000.0
        assert result["calculations"]["advance_fees_created"]["value"] == 50000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 0


class TestPaygCostCapCombined:
    """Test PAYG with cost cap."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_payg_with_cost_cap(self, processor):
        """PAYG contract with cost cap applies both rules.

        The cost cap applies to the TOTAL going to Finalis (ARR + excess).
        When capped, ARR has priority over excess commissions.
        """
        input_data = {
            "contract": {
                "rate_type": "lehman",
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
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 0,
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG + Cost Cap",
                "success_fees": 3000000,
                "deal_date": "2025-12-19",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Lehman: $50k + $80k = $130k (implied before cap)
        # Cost cap: $100k (total to Finalis, including ARR)
        # Amount not charged: $30k
        assert result["calculations"]["implied_total"]["value"] == 130000.0

        # Cost cap applies to total (ARR + excess), not just excess
        # ARR has priority: $10k ARR, then $90k excess
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 10000.0
        assert result["payg_tracking"]["finalis_commissions_this_deal"] == 90000.0

        # finalis_commissions = excess only (after ARR)
        assert result["calculations"]["finalis_commissions"]["value"] == 90000.0
        assert result["calculations"]["amount_not_charged_due_to_cap"]["value"] == 30000.0

    def test_payg_cost_cap_smaller_than_arr(self, processor):
        """When cost cap is smaller than ARR, even ARR gets capped.

        Edge case: If cost cap is $5k and ARR is $10k, only $5k can go to ARR.
        """
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,  # $10k ARR
                "contract_start_date": "2025-01-01",
                "cost_cap_type": "total",
                "cost_cap_amount": 5000  # Only $5k cap!
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 0,
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG Cap < ARR",
                "success_fees": 500000,
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $500k × 5% = $25,000
        # ARR target: $10k, but cost cap is only $5k
        # Only $5k can go to ARR, $0 to excess
        assert result["calculations"]["implied_total"]["value"] == 25000.0
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 5000.0
        assert result["payg_tracking"]["finalis_commissions_this_deal"] == 0
        assert result["calculations"]["finalis_commissions"]["value"] == 0
        assert result["calculations"]["amount_not_charged_due_to_cap"]["value"] == 20000.0

        # ARR not fully covered, so not in commissions mode yet
        assert not result["state_changes"]["entered_commissions_mode"]

    def test_payg_cost_cap_sequential_deals(self, processor):
        """Multiple PAYG deals gradually hitting the cost cap.

        Deal 1: Uses $50k of $100k cap
        Deal 2: Uses remaining $50k, gets capped
        """
        # Deal 1: $50k implied, all fits
        input_data_1 = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,
                "contract_start_date": "2025-01-01",
                "cost_cap_type": "total",
                "cost_cap_amount": 100000
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 0,
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG Sequential 1",
                "success_fees": 1000000,
                "deal_date": "2025-03-01",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result1 = processor.process_from_dict(input_data_1)

        # Implied: $50k, all fits under $100k cap
        # ARR: $10k, Excess: $40k
        assert result1["calculations"]["implied_total"]["value"] == 50000.0
        assert result1["payg_tracking"]["arr_contribution_this_deal"] == 10000.0
        assert result1["payg_tracking"]["finalis_commissions_this_deal"] == 40000.0
        assert result1["calculations"]["amount_not_charged_due_to_cap"]["value"] == 0

        # Deal 2: Uses state from Deal 1, hits cap
        input_data_2 = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 1000000,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,
                "contract_start_date": "2025-01-01",
                "cost_cap_type": "total",
                "cost_cap_amount": 100000
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,  # ARR covered from Deal 1
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 50000,
                "total_paid_this_contract_year": 50000,
                "total_paid_all_time": 50000  # $50k already paid
            },
            "deal": {
                "deal_name": "PAYG Sequential 2",
                "success_fees": 2000000,
                "deal_date": "2025-09-01",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result2 = processor.process_from_dict(input_data_2)

        # Implied: $100k
        # Available in cap: $100k - $50k = $50k
        # All $50k goes to excess (ARR already covered)
        assert result2["calculations"]["implied_total"]["value"] == 100000.0
        assert result2["payg_tracking"]["arr_contribution_this_deal"] == 0
        assert result2["payg_tracking"]["finalis_commissions_this_deal"] == 50000.0
        assert result2["calculations"]["finalis_commissions"]["value"] == 50000.0
        assert result2["calculations"]["amount_not_charged_due_to_cap"]["value"] == 50000.0


class TestPaygEdgeCases:
    """Test PAYG edge cases."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_payg_exactly_hitting_arr_target(self, processor):
        """PAYG deal exactly covers remaining ARR, no excess.

        Business expectation: When ARR is fully covered (even if exactly),
        entered_commissions_mode should be True.
        """
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.03,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 7000,  # Already paid $7k toward $10k ARR
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG Exact ARR",
                "success_fees": 100000,
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $100k × 3% = $3,000
        # ARR remaining: $10k - $7k = $3,000
        # Exactly covers, no excess
        assert result["calculations"]["implied_total"]["value"] == 3000.0
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 3000.0
        assert result["payg_tracking"]["finalis_commissions_this_deal"] == 0
        # Business expectation: ARR fully covered means entered commissions mode
        assert result["state_changes"]["entered_commissions_mode"]

    def test_payg_entering_commissions_mode(self, processor):
        """PAYG transitions to commissions mode when ARR covered."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 8000,  # Already paid $8k toward $10k ARR
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG Enter Mode",
                "success_fees": 100000,
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $5,000
        # ARR remaining: $2,000
        # Goes to ARR: $2,000
        # Excess commission: $3,000
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 2000.0
        assert result["payg_tracking"]["finalis_commissions_this_deal"] == 3000.0
        assert result["state_changes"]["entered_commissions_mode"]

    def test_payg_already_in_commissions_mode(self, processor):
        """PAYG already in commissions mode, all to excess."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.04,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": True,
                "annual_subscription": 10000,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": True,  # Already in mode
                "future_subscription_fees": [],
                "payg_commissions_accumulated": 15000,
                "total_paid_this_contract_year": 15000,
                "total_paid_all_time": 15000
            },
            "deal": {
                "deal_name": "PAYG - Pure Commissions",
                "success_fees": 200000,
                "deal_date": "2025-06-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $8,000
        # All to excess (ARR already covered)
        assert result["calculations"]["implied_total"]["value"] == 8000.0
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 0
        assert result["payg_tracking"]["finalis_commissions_this_deal"] == 8000.0


class TestAdvanceFeesMultiplePayments:
    """Test advance fees spanning multiple future payments."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_advance_fees_cover_multiple_payments(self, processor):
        """Large implied covers multiple future payments."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.10,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 0,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [
                    {"payment_id": "p1", "due_date": "2025-03-31", "amount_due": 25000, "amount_paid": 0},
                    {"payment_id": "p2", "due_date": "2025-06-30", "amount_due": 25000, "amount_paid": 0},
                    {"payment_id": "p3", "due_date": "2025-09-30", "amount_due": 25000, "amount_paid": 10000},
                    {"payment_id": "p4", "due_date": "2025-12-31", "amount_due": 25000, "amount_paid": 0}
                ],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Multi-Payment Advance",
                "success_fees": 800000,
                "deal_date": "2025-02-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Implied: $80k
        # Total owed in future: $25k + $25k + $15k + $25k = $90k
        # Advance created: min($80k, $90k) = $80k
        assert result["calculations"]["implied_total"]["value"] == 80000.0
        assert result["calculations"]["advance_fees_created"]["value"] == 80000.0

        # Check payments updated
        payments = result["updated_future_payments"]
        p1 = next(p for p in payments if p["payment_id"] == "p1")
        p2 = next(p for p in payments if p["payment_id"] == "p2")
        p3 = next(p for p in payments if p["payment_id"] == "p3")
        p4 = next(p for p in payments if p["payment_id"] == "p4")

        # p1: fully paid (0 remaining)
        assert p1["remaining"] == 0
        # p2: fully paid (0 remaining)
        assert p2["remaining"] == 0
        # p3: fully paid (0 remaining, started with 15k owed)
        assert p3["remaining"] == 0
        # p4: partial (25k - 15k = 10k remaining)
        assert p4["remaining"] == 10000.0


class TestPartialDebtCollection:
    """Test partial debt + deferred collection."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_partial_debt_and_deferred_collection(self, processor):
        """When deal can't cover all debt, regular debt first, then deferred."""
        input_data = {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 30000,  # $30k regular debt
                "deferred_subscription_fee": 40000,  # $40k deferred
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Partial Debt Collection",
                "success_fees": 50000,  # Only $50k available
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": False
            }
        }
        result = processor.process_from_dict(input_data)

        # Total debt: $30k + $40k = $70k
        # Can collect: $50k
        # First pays regular debt: $30k
        # Then deferred: $20k (of $40k)
        assert result["calculations"]["debt_collected"]["value"] == 50000.0
        assert result["state_changes"]["final_debt"] == 0
        assert result["state_changes"]["final_deferred"] == 20000.0


class TestMaximumComplexity:
    """Test all fees combined - maximum complexity scenario."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_all_fees_combined(self, processor):
        """Complex scenario with all fee types + debt + credit."""
        input_data = {
            "contract": {
                "rate_type": "lehman",
                "lehman_tiers": [
                    {"lower_bound": 0, "upper_bound": 2000000, "rate": 0.05},
                    {"lower_bound": 2000000.01, "upper_bound": None, "rate": 0.03}
                ],
                "accumulated_success_fees_before_this_deal": 1500000,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 10000,
                "current_debt": 15000,
                "deferred_subscription_fee": 25000,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [
                    {"payment_id": "p1", "due_date": "2025-06-30", "amount_due": 30000, "amount_paid": 5000}
                ],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Maximum Complexity",
                "success_fees": 1000000,
                "deal_date": "2025-05-15",
                "is_distribution_fee_true": True,
                "is_sourcing_fee_true": True,
                "is_deal_exempt": False,
                "has_finra_fee": True,
                "has_external_retainer": True,
                "external_retainer": 50000,
                "is_external_retainer_deducted": True
            }
        }
        result = processor.process_from_dict(input_data)

        # Verify all fee types are calculated
        # When retainer is deducted, all fees (including dist/sourcing) use total
        assert result["calculations"]["finra_fee"]["value"] > 0
        assert result["calculations"]["distribution_fee"]["value"] == 105000.0  # 10% of $1.05M
        assert result["calculations"]["sourcing_fee"]["value"] == 105000.0  # 10% of $1.05M

        # Verify debt was collected
        assert result["calculations"]["debt_collected"]["value"] == 40000.0  # 15k + 25k

        # Verify total includes retainer
        assert result["deal_summary"]["total_deal_value"] == 1050000.0

        # Verify implied is calculated correctly with Lehman + historical
        # Historical: $1.5M (in Tier 1)
        # New deal total: $1.05M
        #   - First $500k in Tier 1 @ 5% = $25,000
        #   - Next $550k in Tier 2 @ 3% = $16,500
        #   - Total = $41,500
        assert result["calculations"]["implied_total"]["value"] == 41500.0
