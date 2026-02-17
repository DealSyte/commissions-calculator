"""
Unit Tests for Credit Applicator

Tests verify credit generation and application logic.
"""

from decimal import Decimal

import pytest

from engine.calculators.credit import CreditApplicator
from engine.models import Contract, ContractState, Deal, DebtCollection, FeeCalculation, ProcessingContext


class TestCreditGeneration:
    """Test credit generation from collected debt."""

    @pytest.fixture
    def applicator(self):
        return CreditApplicator()

    def test_debt_collected_becomes_credit(self, applicator):
        """Collected debt generates equal credit."""
        ctx = _make_credit_context(
            current_credit=0,
            debt_collected=5000,
            implied_total=3000,
            is_in_commissions_mode=False
        )
        result = applicator.apply(ctx)

        assert result.credit_from_debt == Decimal('5000')
        assert result.total_credit_available == Decimal('5000')

    def test_existing_credit_plus_new_credit(self, applicator):
        """Existing credit + debt collected = total available."""
        ctx = _make_credit_context(
            current_credit=2000,
            debt_collected=3000,
            implied_total=4000,
            is_in_commissions_mode=False
        )
        result = applicator.apply(ctx)

        assert result.credit_from_debt == Decimal('3000')
        assert result.total_credit_available == Decimal('5000')

    def test_payg_generates_no_credit(self, applicator):
        """PAYG contracts don't generate credit from debt."""
        ctx = _make_credit_context(
            current_credit=0,
            debt_collected=5000,
            implied_total=3000,
            is_payg=True
        )
        result = applicator.apply(ctx)

        assert result.credit_from_debt == Decimal('0')
        assert result.total_credit_available == Decimal('0')


class TestCreditApplication:
    """Test credit application against implied cost."""

    @pytest.fixture
    def applicator(self):
        return CreditApplicator()

    def test_credit_absorbs_implied_fully(self, applicator):
        """Credit $5000, implied $3000 → use $3000, remain $2000."""
        ctx = _make_credit_context(
            current_credit=5000,
            debt_collected=0,
            implied_total=3000,
            is_in_commissions_mode=False
        )
        result = applicator.apply(ctx)

        assert result.credit_used == Decimal('3000')
        assert result.credit_remaining == Decimal('2000')
        assert result.implied_after_credit == Decimal('0')

    def test_credit_partially_absorbs_implied(self, applicator):
        """Credit $2000, implied $5000 → use $2000, implied remaining $3000."""
        ctx = _make_credit_context(
            current_credit=2000,
            debt_collected=0,
            implied_total=5000,
            is_in_commissions_mode=False
        )
        result = applicator.apply(ctx)

        assert result.credit_used == Decimal('2000')
        assert result.credit_remaining == Decimal('0')
        assert result.implied_after_credit == Decimal('3000')

    def test_no_credit_leaves_implied_unchanged(self, applicator):
        """No credit → implied passes through unchanged."""
        ctx = _make_credit_context(
            current_credit=0,
            debt_collected=0,
            implied_total=5000,
            is_in_commissions_mode=False
        )
        result = applicator.apply(ctx)

        assert result.credit_used == Decimal('0')
        assert result.implied_after_credit == Decimal('5000')

    def test_commissions_mode_skips_credit_usage(self, applicator):
        """In commissions mode, credit is NOT used."""
        ctx = _make_credit_context(
            current_credit=5000,
            debt_collected=0,
            implied_total=3000,
            is_in_commissions_mode=True
        )
        result = applicator.apply(ctx)

        # Credit not used, implied unchanged
        assert result.credit_used == Decimal('0')
        assert result.credit_remaining == Decimal('5000')
        assert result.implied_after_credit == Decimal('3000')

    def test_payg_skips_credit_entirely(self, applicator):
        """PAYG contracts don't use credit system at all."""
        ctx = _make_credit_context(
            current_credit=0,  # PAYG can't have credit anyway
            debt_collected=5000,
            implied_total=3000,
            is_payg=True
        )
        result = applicator.apply(ctx)

        assert result.credit_used == Decimal('0')
        assert result.credit_remaining == Decimal('0')
        assert result.implied_after_credit == Decimal('3000')


def _make_credit_context(
    current_credit: float,
    debt_collected: float,
    implied_total: float,
    is_in_commissions_mode: bool = False,
    is_payg: bool = False
) -> ProcessingContext:
    """Helper to create ProcessingContext for credit tests."""
    deal = Deal(
        name="Test",
        success_fees=Decimal('100000'),
        deal_date="2026-01-15",
        is_distribution_fee=False,
        is_sourcing_fee=False,
        is_deal_exempt=False
    )
    contract = Contract(
        rate_type='fixed',
        fixed_rate=Decimal('0.05'),
        accumulated_success_fees=Decimal('0'),
        is_pay_as_you_go=is_payg
    )
    state = ContractState(
        current_credit=Decimal(str(current_credit)),
        current_debt=Decimal('0'),
        is_in_commissions_mode=is_in_commissions_mode
    )
    ctx = ProcessingContext(
        deal=deal,
        contract=contract,
        initial_state=state
    )
    ctx.fees = FeeCalculation(implied_total=Decimal(str(implied_total)))
    ctx.debt = DebtCollection(total_collected=Decimal(str(debt_collected)))
    return ctx
