"""
Unit Tests for Cost Cap Enforcer

Tests verify cost cap limits are applied correctly.
"""

from decimal import Decimal

import pytest

from engine.calculators.cost_cap import CostCapEnforcer
from engine.models import (
    CommissionCalculation,
    Contract,
    ContractState,
    Deal,
    FeeCalculation,
    ProcessingContext,
    SubscriptionApplication,
)


class TestCostCapEnforcement:
    """Test cost cap enforcement on commissions."""

    @pytest.fixture
    def enforcer(self):
        return CostCapEnforcer()

    def test_no_cap_configured_passes_through(self, enforcer):
        """When no cost cap, commissions pass through unchanged."""
        ctx = self._make_context(
            commissions=5000, advance_fees=3000, cost_cap_type=None, cost_cap_amount=None, total_paid=0
        )
        result = enforcer.apply(ctx)

        assert result.finalis_commissions == Decimal("5000")
        assert result.amount_not_charged_due_to_cap == Decimal("0")

    def test_under_annual_cap_passes_through(self, enforcer):
        """When under annual cap, commissions pass through."""
        ctx = self._make_context(
            commissions=5000,
            advance_fees=3000,
            cost_cap_type="annual",
            cost_cap_amount=20000,
            total_paid=0,  # Nothing paid yet this year
        )
        result = enforcer.apply(ctx)

        # 3000 + 5000 = 8000, under 20000 cap
        assert result.finalis_commissions == Decimal("5000")
        assert result.amount_not_charged_due_to_cap == Decimal("0")

    def test_annual_cap_limits_commissions(self, enforcer):
        """Annual cap reduces commissions when exceeded."""
        ctx = self._make_context(
            commissions=5000,
            advance_fees=3000,
            cost_cap_type="annual",
            cost_cap_amount=10000,
            total_paid=5000,  # Already paid 5000 this year
            implied_total=8000,  # 3000 + 5000 = total we'd want to charge
        )
        result = enforcer.apply(ctx)

        # Available space: 10000 - 5000 = 5000
        # Advance fees (3000) have priority
        # Space for commissions: 5000 - 3000 = 2000
        assert result.finalis_commissions == Decimal("2000")
        # 3000 of commissions not charged: 8000 - (3000 + 2000) = 3000
        assert result.amount_not_charged_due_to_cap == Decimal("3000")

    def test_total_cap_limits_commissions(self, enforcer):
        """Total (lifetime) cap works same as annual."""
        ctx = self._make_context(
            commissions=5000,
            advance_fees=0,
            cost_cap_type="total",
            cost_cap_amount=50000,
            total_paid=48000,  # Almost at lifetime cap
        )
        result = enforcer.apply(ctx)

        # Available space: 50000 - 48000 = 2000
        assert result.finalis_commissions == Decimal("2000")

    def test_advance_fees_have_priority_over_commissions(self, enforcer):
        """When cap exceeded, advance fees preserved, commissions reduced."""
        ctx = self._make_context(
            commissions=5000,
            advance_fees=4000,
            cost_cap_type="annual",
            cost_cap_amount=10000,
            total_paid=8000,  # Only 2000 space left
        )
        result = enforcer.apply(ctx)

        # Available: 10000 - 8000 = 2000
        # Advance fees: 4000 (already committed, exceeds space alone!)
        # Commissions get: max(0, 2000 - 4000) = 0
        assert result.finalis_commissions == Decimal("0")

    def test_cap_already_exceeded_zeros_commissions(self, enforcer):
        """When already at/over cap, no new commissions."""
        ctx = self._make_context(
            commissions=5000,
            advance_fees=0,
            cost_cap_type="annual",
            cost_cap_amount=10000,
            total_paid=10000,  # Already at cap
        )
        result = enforcer.apply(ctx)

        assert result.finalis_commissions == Decimal("0")

    def test_invalid_cap_type_ignored(self, enforcer):
        """Unknown cap type is treated as no cap."""
        ctx = self._make_context(
            commissions=5000, advance_fees=0, cost_cap_type="invalid", cost_cap_amount=1000, total_paid=0
        )
        result = enforcer.apply(ctx)

        # Invalid cap type = no cap
        assert result.finalis_commissions == Decimal("5000")

    def test_preserves_other_commission_fields(self, enforcer):
        """Non-commission fields are preserved through cap application."""
        ctx = self._make_context(
            commissions=5000, advance_fees=0, cost_cap_type="annual", cost_cap_amount=3000, total_paid=0
        )
        # Set some fields that should be preserved
        ctx.commission.entered_commissions_mode = True
        ctx.commission.new_commissions_mode = True
        # Note: payg_arr_contribution is not preserved for non-PAYG contracts
        # because non-PAYG contracts shouldn't have ARR contributions

        result = enforcer.apply(ctx)

        assert result.entered_commissions_mode
        assert result.new_commissions_mode
        # For non-PAYG, ARR contribution is always 0
        assert result.payg_arr_contribution == Decimal("0")
        # But commissions were capped
        assert result.finalis_commissions == Decimal("3000")

    def _make_context(
        self,
        commissions: float,
        advance_fees: float,
        cost_cap_type: str,
        cost_cap_amount: float,
        total_paid: float,
        implied_total: float = 5000,
    ) -> ProcessingContext:
        deal = Deal(
            name="Test",
            success_fees=Decimal("100000"),
            deal_date="2026-01-15",
            is_distribution_fee=False,
            is_sourcing_fee=False,
            is_deal_exempt=False,
        )
        contract = Contract(
            rate_type="fixed",
            fixed_rate=Decimal("0.05"),
            accumulated_success_fees=Decimal("0"),
            cost_cap_type=cost_cap_type,
            cost_cap_amount=Decimal(str(cost_cap_amount)) if cost_cap_amount else None,
        )
        state = ContractState(
            current_credit=Decimal("0"),
            current_debt=Decimal("0"),
            is_in_commissions_mode=False,
            total_paid_this_contract_year=Decimal(str(total_paid)),
            total_paid_all_time=Decimal(str(total_paid)),
        )
        ctx = ProcessingContext(deal=deal, contract=contract, initial_state=state)
        ctx.fees = FeeCalculation(implied_total=Decimal(str(implied_total)))
        ctx.subscription = SubscriptionApplication(advance_fees_created=Decimal(str(advance_fees)))
        ctx.commission = CommissionCalculation(
            finalis_commissions_before_cap=Decimal(str(commissions)), finalis_commissions=Decimal(str(commissions))
        )
        return ctx
