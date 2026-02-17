"""
Unit Tests for Debt Collector

Tests verify debt collection logic against known scenarios.
"""

from decimal import Decimal

import pytest

from engine.calculators.debt import DebtCollector
from engine.models import Contract, ContractState, Deal, DeferredEntry, FeeCalculation, ProcessingContext


class TestContractYearCalculation:
    """Test contract year calculation from dates."""

    def test_day_zero_is_year_one(self):
        """Contract start date = deal date → Year 1"""
        result = DebtCollector.calculate_contract_year("2025-01-01", "2025-01-01")
        assert result == 1

    def test_day_364_is_year_one(self):
        """364 days after start → still Year 1"""
        result = DebtCollector.calculate_contract_year("2025-01-01", "2025-12-31")
        assert result == 1

    def test_day_365_is_year_two(self):
        """365 days after start → Year 2"""
        result = DebtCollector.calculate_contract_year("2025-01-01", "2026-01-01")
        assert result == 2

    def test_day_730_is_year_three(self):
        """730 days (2 years) after start → Year 3"""
        result = DebtCollector.calculate_contract_year("2025-01-01", "2027-01-01")
        assert result == 3

    def test_mid_year_calculation(self):
        """180 days into year 2"""
        # 365 + 180 = 545 days → Year 2
        result = DebtCollector.calculate_contract_year("2024-01-01", "2025-06-30")
        assert result == 2


class TestDebtCollection:
    """Test debt collection from success fees."""

    @pytest.fixture
    def collector(self):
        return DebtCollector()

    def test_no_debt_collects_nothing(self, collector):
        """When no debt exists, nothing is collected."""
        ctx = self._make_context(success_fees=100000, current_debt=0, deferred=0)
        result = collector.collect(ctx)

        assert result.total_collected == Decimal("0")
        assert result.regular_debt_collected == Decimal("0")
        assert result.deferred_collected == Decimal("0")

    def test_collects_full_debt_when_success_fees_exceed(self, collector):
        """Success fees $100k, debt $5k → collect all $5k."""
        ctx = self._make_context(success_fees=100000, current_debt=5000, deferred=0)
        result = collector.collect(ctx)

        assert result.total_collected == Decimal("5000")
        assert result.regular_debt_collected == Decimal("5000")
        assert result.remaining_debt == Decimal("0")

    def test_collects_partial_debt_when_success_fees_insufficient(self, collector):
        """Success fees $3k, debt $5k → collect only $3k."""
        ctx = self._make_context(success_fees=3000, current_debt=5000, deferred=0)
        result = collector.collect(ctx)

        assert result.total_collected == Decimal("3000")
        assert result.regular_debt_collected == Decimal("3000")
        assert result.remaining_debt == Decimal("2000")

    def test_regular_debt_collected_before_deferred(self, collector):
        """Regular debt has priority over deferred."""
        ctx = self._make_context(success_fees=7000, current_debt=5000, deferred=5000)
        result = collector.collect(ctx)

        # Total debt is 10k, but only 7k available
        # Should collect all 5k regular, then 2k deferred
        assert result.total_collected == Decimal("7000")
        assert result.regular_debt_collected == Decimal("5000")
        assert result.deferred_collected == Decimal("2000")
        assert result.remaining_debt == Decimal("0")
        assert result.remaining_deferred == Decimal("3000")

    def test_deferred_only_when_no_regular_debt(self, collector):
        """Only deferred debt, no regular debt."""
        ctx = self._make_context(success_fees=10000, current_debt=0, deferred=3000)
        result = collector.collect(ctx)

        assert result.total_collected == Decimal("3000")
        assert result.regular_debt_collected == Decimal("0")
        assert result.deferred_collected == Decimal("3000")
        assert result.remaining_deferred == Decimal("0")

    def test_deferred_schedule_uses_correct_year(self, collector):
        """Multi-year deferred schedule selects correct year's amount."""
        ctx = self._make_context(
            success_fees=100000,
            current_debt=0,
            deferred=0,  # Will be overridden by schedule
            deferred_schedule=[
                DeferredEntry(year=1, amount=Decimal("1000")),
                DeferredEntry(year=2, amount=Decimal("2000")),
                DeferredEntry(year=3, amount=Decimal("3000")),
            ],
            contract_year=2,
        )
        result = collector.collect(ctx)

        # Year 2 deferred is 2000
        assert result.applicable_deferred == Decimal("2000")
        assert result.deferred_collected == Decimal("2000")

    def test_deferred_schedule_year_not_found_returns_zero(self, collector):
        """If current year not in schedule, deferred is 0."""
        ctx = self._make_context(
            success_fees=100000,
            current_debt=0,
            deferred=0,
            deferred_schedule=[
                DeferredEntry(year=1, amount=Decimal("1000")),
                DeferredEntry(year=2, amount=Decimal("2000")),
            ],
            contract_year=5,  # Not in schedule
        )
        result = collector.collect(ctx)

        assert result.applicable_deferred == Decimal("0")
        assert result.deferred_collected == Decimal("0")

    def _make_context(
        self,
        success_fees: float,
        current_debt: float,
        deferred: float = 0,
        deferred_schedule: list = None,
        contract_year: int = 1,
    ) -> ProcessingContext:
        """Helper to create ProcessingContext for debt tests."""
        deal = Deal(
            name="Test",
            success_fees=Decimal(str(success_fees)),
            deal_date="2026-01-15",
            is_distribution_fee=False,
            is_sourcing_fee=False,
            is_deal_exempt=False,
        )
        contract = Contract(
            rate_type="fixed",
            fixed_rate=Decimal("0.05"),
            accumulated_success_fees=Decimal("0"),
            contract_start_date="2025-01-01",
        )
        state = ContractState(
            current_credit=Decimal("0"),
            current_debt=Decimal(str(current_debt)),
            is_in_commissions_mode=False,
            deferred_subscription_fee=Decimal(str(deferred)),
            deferred_schedule=deferred_schedule or [],
        )
        ctx = ProcessingContext(deal=deal, contract=contract, initial_state=state, contract_year=contract_year)
        # Pre-populate fees (required for collect to work)
        ctx.fees = FeeCalculation(implied_total=Decimal("5000"))
        return ctx
