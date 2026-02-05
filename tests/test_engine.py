"""
Tests for Finalis Contract Engine

Run with: python -m pytest tests/ -v
"""

import pytest
from decimal import Decimal
from engine import DealProcessor
from engine.models import DealInput


class TestDealProcessor:
    """Test the main deal processor."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    @pytest.fixture
    def sample_input(self):
        """Standard contract input for testing."""
        return {
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
                "is_in_commissions_mode": False,
                "future_subscription_fees": [
                    {
                        "payment_id": "p1",
                        "due_date": "2025-06-01",
                        "amount_due": 10000,
                        "amount_paid": 0
                    }
                ],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Test Deal",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": True
            }
        }

    def test_basic_processing(self, processor, sample_input):
        """Test basic deal processing."""
        result = processor.process_from_dict(sample_input)

        assert result is not None
        assert "deal_summary" in result
        assert "calculations" in result
        assert "state_changes" in result
        assert "updated_contract_state" in result

    def test_finra_fee_calculation(self, processor, sample_input):
        """Test FINRA fee is calculated correctly."""
        result = processor.process_from_dict(sample_input)

        # FINRA rate is 0.4732%
        expected_finra = round(100000 * 0.004732, 2)
        assert result["calculations"]["finra_fee"]["value"] == expected_finra

    def test_implied_calculation_fixed_rate(self, processor, sample_input):
        """Test implied is calculated correctly with fixed rate."""
        result = processor.process_from_dict(sample_input)

        # Fixed rate is 5%
        expected_implied = round(100000 * 0.05, 2)
        assert result["calculations"]["implied_total"]["value"] == expected_implied

    def test_advance_fees_created(self, processor, sample_input):
        """Test advance fees are applied to future payments."""
        result = processor.process_from_dict(sample_input)

        # Implied is 5000, future payment is 10000
        # Should create 5000 in advance fees
        assert result["calculations"]["advance_fees_created"]["value"] == 5000.0
        
        # Check the payment was updated
        assert len(result["updated_future_payments"]) == 1
        payment = result["updated_future_payments"][0]
        assert payment["amount_paid"] == 5000.0
        assert payment["remaining"] == 5000.0

    def test_no_commissions_when_not_fully_prepaid(self, processor, sample_input):
        """Test no commissions when subscription not fully prepaid."""
        result = processor.process_from_dict(sample_input)

        # Future payment has 5000 remaining, so not in commissions mode
        assert result["calculations"]["finalis_commissions"]["value"] == 0
        assert result["state_changes"]["contract_fully_prepaid"] == False

    def test_commissions_when_fully_prepaid(self, processor, sample_input):
        """Test commissions occur when subscription is fully prepaid."""
        # Reduce future payment so implied covers it completely
        sample_input["state"]["future_subscription_fees"][0]["amount_due"] = 3000

        result = processor.process_from_dict(sample_input)

        # Implied is 5000, payment is only 3000
        # Should be 3000 advance fees + 2000 commissions
        assert result["calculations"]["advance_fees_created"]["value"] == 3000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 2000.0
        assert result["state_changes"]["contract_fully_prepaid"] == True
        assert result["state_changes"]["entered_commissions_mode"] == True

    def test_finra_fee_exempt(self, processor, sample_input):
        """Test FINRA fee can be disabled."""
        sample_input["deal"]["has_finra_fee"] = False
        result = processor.process_from_dict(sample_input)

        assert result["calculations"]["finra_fee"]["value"] == 0

    def test_distribution_fee(self, processor, sample_input):
        """Test distribution fee when enabled."""
        sample_input["deal"]["is_distribution_fee_true"] = True
        result = processor.process_from_dict(sample_input)

        expected = round(100000 * 0.10, 2)
        assert result["calculations"]["distribution_fee"]["value"] == expected

    def test_sourcing_fee(self, processor, sample_input):
        """Test sourcing fee when enabled."""
        sample_input["deal"]["is_sourcing_fee_true"] = True
        result = processor.process_from_dict(sample_input)

        expected = round(100000 * 0.10, 2)
        assert result["calculations"]["sourcing_fee"]["value"] == expected


class TestPayAsYouGo:
    """Test PAYG contract processing."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    @pytest.fixture
    def payg_input(self):
        """PAYG contract input."""
        return {
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
                "payg_commissions_accumulated": 0,
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "PAYG Deal",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": True
            }
        }

    def test_payg_arr_contribution(self, processor, payg_input):
        """Test PAYG implied goes to ARR first."""
        result = processor.process_from_dict(payg_input)

        # Implied is 5000, ARR is 10000
        # All 5000 should go to ARR, no commission yet
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 5000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 0
        assert result["payg_tracking"]["remaining_to_cover_arr"] == 5000.0

    def test_payg_commissions_after_arr_covered(self, processor, payg_input):
        """Test PAYG commissions occur after ARR is covered."""
        # Set accumulated to already cover ARR
        payg_input["state"]["payg_commissions_accumulated"] = 10000

        result = processor.process_from_dict(payg_input)

        # ARR already covered, all implied becomes commission
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 0
        assert result["calculations"]["finalis_commissions"]["value"] == 5000.0

    def test_payg_partial_arr_coverage(self, processor, payg_input):
        """Test PAYG partial ARR coverage."""
        # Set accumulated to 8000, ARR is 10000
        payg_input["state"]["payg_commissions_accumulated"] = 8000

        result = processor.process_from_dict(payg_input)

        # 2000 to ARR, 3000 becomes commission
        assert result["payg_tracking"]["arr_contribution_this_deal"] == 2000.0
        assert result["calculations"]["finalis_commissions"]["value"] == 3000.0


class TestDebtCollection:
    """Test debt collection functionality."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    @pytest.fixture
    def debt_input(self):
        """Input with existing debt."""
        return {
            "contract": {
                "rate_type": "fixed",
                "fixed_rate": 0.05,
                "accumulated_success_fees_before_this_deal": 0,
                "is_pay_as_you_go": False,
                "contract_start_date": "2025-01-01"
            },
            "state": {
                "current_credit": 0,
                "current_debt": 5000,
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Debt Test",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": True
            }
        }

    def test_debt_collection(self, processor, debt_input):
        """Test debt is collected from success fees."""
        result = processor.process_from_dict(debt_input)

        assert result["calculations"]["debt_collected"]["value"] == 5000.0
        assert result["state_changes"]["final_debt"] == 0

    def test_debt_generates_credit(self, processor, debt_input):
        """Test collected debt generates credit."""
        result = processor.process_from_dict(debt_input)

        # Collected debt should become credit
        assert result["state_changes"]["final_credit"] == 0  # Credit used against implied
        # 5000 credit generated, 5000 implied, so credit is fully used


class TestValidation:
    """Test input validation."""

    @pytest.fixture
    def processor(self):
        return DealProcessor()

    def test_negative_success_fees_rejected(self, processor):
        """Test negative success fees are rejected."""
        bad_input = {
            "contract": {"rate_type": "fixed", "fixed_rate": 0.05, "accumulated_success_fees_before_this_deal": 0},
            "state": {"current_credit": 0, "current_debt": 0, "is_in_commissions_mode": False, "future_subscription_fees": []},
            "deal": {
                "deal_name": "Bad Deal",
                "success_fees": -100,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False
            }
        }

        with pytest.raises(ValueError, match="success_fees must be positive"):
            processor.process_from_dict(bad_input)

    def test_invalid_rate_type_rejected(self, processor):
        """Test invalid rate type is rejected."""
        bad_input = {
            "contract": {"rate_type": "invalid", "accumulated_success_fees_before_this_deal": 0},
            "state": {"current_credit": 0, "current_debt": 0, "is_in_commissions_mode": False, "future_subscription_fees": []},
            "deal": {
                "deal_name": "Bad Deal",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False
            }
        }

        with pytest.raises(ValueError, match="Invalid rate_type"):
            processor.process_from_dict(bad_input)


class TestBackwardCompatibility:
    """Test backward compatibility with old API."""

    def test_finalis_engine_class_works(self):
        """Test the old FinalisEngine class still works."""
        from finalis_engine import FinalisEngine

        engine = FinalisEngine()
        
        result = engine.process_deal({
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
                "is_in_commissions_mode": False,
                "future_subscription_fees": [],
                "total_paid_this_contract_year": 0,
                "total_paid_all_time": 0
            },
            "deal": {
                "deal_name": "Compat Test",
                "success_fees": 100000,
                "deal_date": "2025-03-15",
                "is_distribution_fee_true": False,
                "is_sourcing_fee_true": False,
                "is_deal_exempt": False,
                "has_finra_fee": True
            }
        })

        assert result is not None
        assert "calculations" in result
        assert result["calculations"]["implied_total"]["value"] == 5000.0
