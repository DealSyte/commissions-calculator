"""
Unit Tests for Fee Calculator

Tests verify calculations against known expected values.
"""

from decimal import Decimal

import pytest

from engine.calculators.fees import FeeCalculator, quantize_money
from engine.models import Contract, ContractState, Deal, LehmanTier, ProcessingContext


class TestQuantizeMoney:
    """Test the money rounding utility."""

    def test_rounds_down_at_half(self):
        # 0.004 rounds to 0.00
        assert quantize_money(Decimal("0.004")) == Decimal("0.00")

    def test_rounds_up_at_half(self):
        # 0.005 rounds to 0.01 (ROUND_HALF_UP)
        assert quantize_money(Decimal("0.005")) == Decimal("0.01")

    def test_rounds_up_above_half(self):
        # 0.006 rounds to 0.01
        assert quantize_money(Decimal("0.006")) == Decimal("0.01")

    def test_preserves_exact_cents(self):
        assert quantize_money(Decimal("123.45")) == Decimal("123.45")

    def test_truncates_extra_precision(self):
        assert quantize_money(Decimal("123.456789")) == Decimal("123.46")


class TestFinraFee:
    """Test FINRA fee calculation (0.4732%)."""

    @pytest.fixture
    def calculator(self):
        return FeeCalculator()

    def test_finra_rate_is_correct(self, calculator):
        """Verify the FINRA rate constant."""
        assert calculator.FINRA_RATE == Decimal("0.004732")

    def test_finra_on_100k(self, calculator):
        """$100,000 × 0.4732% = $473.20"""
        result = calculator._calculate_finra(Decimal("100000"), True)
        assert result == Decimal("473.20")

    def test_finra_on_1m(self, calculator):
        """$1,000,000 × 0.4732% = $4,732.00"""
        result = calculator._calculate_finra(Decimal("1000000"), True)
        assert result == Decimal("4732.00")

    def test_finra_on_odd_amount(self, calculator):
        """$75,432.17 × 0.4732% = $356.95 (rounded)"""
        result = calculator._calculate_finra(Decimal("75432.17"), True)
        assert result == Decimal("356.95")

    def test_finra_exempt_returns_zero(self, calculator):
        """When has_finra_fee=False, return $0."""
        result = calculator._calculate_finra(Decimal("100000"), False)
        assert result == Decimal("0")

    def test_finra_on_zero_amount(self, calculator):
        """Edge case: $0 deal."""
        result = calculator._calculate_finra(Decimal("0"), True)
        assert result == Decimal("0")


class TestDistributionFee:
    """Test distribution fee calculation (10%)."""

    @pytest.fixture
    def calculator(self):
        return FeeCalculator()

    def test_distribution_rate_is_correct(self, calculator):
        assert calculator.DISTRIBUTION_RATE == Decimal("0.10")

    def test_distribution_on_100k(self, calculator):
        """$100,000 × 10% = $10,000"""
        result = calculator._calculate_distribution(Decimal("100000"), True)
        assert result == Decimal("10000.00")

    def test_distribution_disabled_returns_zero(self, calculator):
        result = calculator._calculate_distribution(Decimal("100000"), False)
        assert result == Decimal("0")

    def test_distribution_rounds_correctly(self, calculator):
        """$33,333.33 × 10% = $3,333.33"""
        result = calculator._calculate_distribution(Decimal("33333.33"), True)
        assert result == Decimal("3333.33")


class TestSourcingFee:
    """Test sourcing fee calculation (10%)."""

    @pytest.fixture
    def calculator(self):
        return FeeCalculator()

    def test_sourcing_rate_is_correct(self, calculator):
        assert calculator.SOURCING_RATE == Decimal("0.10")

    def test_sourcing_on_100k(self, calculator):
        result = calculator._calculate_sourcing(Decimal("100000"), True)
        assert result == Decimal("10000.00")

    def test_sourcing_disabled_returns_zero(self, calculator):
        result = calculator._calculate_sourcing(Decimal("100000"), False)
        assert result == Decimal("0")


class TestImpliedCalculation:
    """Test implied (BD cost) calculation."""

    @pytest.fixture
    def calculator(self):
        return FeeCalculator()

    def test_deal_exempt_rate_is_correct(self, calculator):
        assert calculator.DEAL_EXEMPT_RATE == Decimal("0.015")

    def test_fixed_rate_5_percent(self, calculator):
        """$100,000 at 5% = $5,000"""
        ctx = self._make_context(success_fees=100000, rate_type="fixed", fixed_rate=0.05)
        result = calculator._calculate_implied(ctx)
        assert result == Decimal("5000.00")

    def test_fixed_rate_3_percent(self, calculator):
        """$250,000 at 3% = $7,500"""
        ctx = self._make_context(success_fees=250000, rate_type="fixed", fixed_rate=0.03)
        result = calculator._calculate_implied(ctx)
        assert result == Decimal("7500.00")

    def test_deal_exempt_overrides_fixed_rate(self, calculator):
        """Deal exempt (1.5%) takes priority over fixed rate."""
        ctx = self._make_context(success_fees=100000, rate_type="fixed", fixed_rate=0.05, is_deal_exempt=True)
        result = calculator._calculate_implied(ctx)
        # 1.5% of 100k = 1500
        assert result == Decimal("1500.00")

    def test_preferred_rate_overrides_everything(self, calculator):
        """Preferred rate (2%) overrides deal exempt and fixed rate."""
        ctx = self._make_context(
            success_fees=100000,
            rate_type="fixed",
            fixed_rate=0.05,
            is_deal_exempt=True,
            has_preferred_rate=True,
            preferred_rate=0.02,
        )
        result = calculator._calculate_implied(ctx)
        # 2% of 100k = 2000
        assert result == Decimal("2000.00")

    def _make_context(
        self,
        success_fees: float,
        rate_type: str = "fixed",
        fixed_rate: float = None,
        is_deal_exempt: bool = False,
        has_preferred_rate: bool = False,
        preferred_rate: float = None,
        accumulated: float = 0,
    ) -> ProcessingContext:
        """Helper to create a minimal ProcessingContext."""
        deal = Deal(
            name="Test",
            success_fees=Decimal(str(success_fees)),
            deal_date="2026-01-01",
            is_distribution_fee=False,
            is_sourcing_fee=False,
            is_deal_exempt=is_deal_exempt,
            has_preferred_rate=has_preferred_rate,
            preferred_rate=Decimal(str(preferred_rate)) if preferred_rate else None,
        )
        contract = Contract(
            rate_type=rate_type,
            fixed_rate=Decimal(str(fixed_rate)) if fixed_rate else None,
            accumulated_success_fees=Decimal(str(accumulated)),
        )
        state = ContractState(current_credit=Decimal("0"), current_debt=Decimal("0"), is_in_commissions_mode=False)
        return ProcessingContext(deal=deal, contract=contract, initial_state=state)


class TestLehmanTiers:
    """Test Lehman progressive tier calculation."""

    @pytest.fixture
    def calculator(self):
        return FeeCalculator()

    def test_single_tier_full_allocation(self, calculator):
        """$100k deal in a single 5% tier."""
        tiers = [LehmanTier(lower_bound=Decimal("0"), upper_bound=None, rate=Decimal("0.05"))]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("100000"), tiers=tiers, accumulated_before=Decimal("0")
        )
        assert result == Decimal("5000.00")

    def test_two_tiers_deal_spans_both(self, calculator):
        """
        Tiers: 0-100k at 5%, 100k+ at 3%
        Deal: $150k starting from $0
        Expected: (100k × 5%) + (50k × 3%) = 5000 + 1500 = 6500
        """
        tiers = [
            LehmanTier(lower_bound=Decimal("0"), upper_bound=Decimal("100000"), rate=Decimal("0.05")),
            LehmanTier(lower_bound=Decimal("100000"), upper_bound=None, rate=Decimal("0.03")),
        ]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("150000"), tiers=tiers, accumulated_before=Decimal("0")
        )
        assert result == Decimal("6500.00")

    def test_starts_in_second_tier(self, calculator):
        """
        Tiers: 0-100k at 5%, 100k+ at 3%
        Accumulated: $80k, Deal: $50k
        Expected: (20k × 5%) + (30k × 3%) = 1000 + 900 = 1900
        """
        tiers = [
            LehmanTier(lower_bound=Decimal("0"), upper_bound=Decimal("100000"), rate=Decimal("0.05")),
            LehmanTier(lower_bound=Decimal("100000"), upper_bound=None, rate=Decimal("0.03")),
        ]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("50000"), tiers=tiers, accumulated_before=Decimal("80000")
        )
        assert result == Decimal("1900.00")

    def test_already_in_highest_tier(self, calculator):
        """
        Tiers: 0-100k at 5%, 100k+ at 3%
        Accumulated: $200k, Deal: $50k
        Expected: 50k × 3% = 1500
        """
        tiers = [
            LehmanTier(lower_bound=Decimal("0"), upper_bound=Decimal("100000"), rate=Decimal("0.05")),
            LehmanTier(lower_bound=Decimal("100000"), upper_bound=None, rate=Decimal("0.03")),
        ]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("50000"), tiers=tiers, accumulated_before=Decimal("200000")
        )
        assert result == Decimal("1500.00")

    def test_three_tiers(self, calculator):
        """
        Tiers: 0-50k at 6%, 50k-150k at 4%, 150k+ at 2%
        Deal: $200k starting from $0
        Expected: (50k × 6%) + (100k × 4%) + (50k × 2%) = 3000 + 4000 + 1000 = 8000
        """
        tiers = [
            LehmanTier(lower_bound=Decimal("0"), upper_bound=Decimal("50000"), rate=Decimal("0.06")),
            LehmanTier(lower_bound=Decimal("50000"), upper_bound=Decimal("150000"), rate=Decimal("0.04")),
            LehmanTier(lower_bound=Decimal("150000"), upper_bound=None, rate=Decimal("0.02")),
        ]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("200000"), tiers=tiers, accumulated_before=Decimal("0")
        )
        assert result == Decimal("8000.00")

    def test_gap_between_tiers(self, calculator):
        """
        Handles gap where tier 1 ends at 100k but tier 2 starts at 100k.01
        This tests the gap-jumping logic.
        """
        tiers = [
            LehmanTier(lower_bound=Decimal("0"), upper_bound=Decimal("100000"), rate=Decimal("0.05")),
            LehmanTier(lower_bound=Decimal("100000.01"), upper_bound=None, rate=Decimal("0.03")),
        ]
        result = calculator._calculate_lehman(
            deal_amount=Decimal("150000"), tiers=tiers, accumulated_before=Decimal("0")
        )
        # 100k at 5% = 5000, then gap of 0.01, then 49999.99 at 3% = 1500.00 (rounded)
        # The gap is "jumped" so deal continues
        assert result == Decimal("6500.00")
