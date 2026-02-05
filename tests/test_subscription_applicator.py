"""
Unit Tests for Subscription Applicator

Tests verify advance subscription fee application logic.
"""

import pytest
from decimal import Decimal
from engine.calculators.subscription import SubscriptionApplicator
from engine.models import (
    Deal, Contract, ContractState, ProcessingContext,
    FeeCalculation, DebtCollection, CreditApplication, FuturePayment
)


class TestAdvanceFeeApplication:
    """Test advance subscription fee creation."""

    @pytest.fixture
    def applicator(self):
        return SubscriptionApplicator()

    def test_no_implied_creates_no_advance_fees(self, applicator):
        """When implied after credit is 0, no advance fees created."""
        ctx = self._make_context(
            implied_after_credit=0,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('0'))
            ]
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('0')
        assert result.contract_fully_prepaid == False

    def test_implied_fully_covers_single_payment(self, applicator):
        """Implied $5000 covers payment of $5000 exactly."""
        ctx = self._make_context(
            implied_after_credit=5000,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('0'))
            ]
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('5000')
        assert result.contract_fully_prepaid == True
        assert result.updated_payments[0]['remaining'] == 0

    def test_implied_partially_covers_payment(self, applicator):
        """Implied $3000 partially covers payment of $5000."""
        ctx = self._make_context(
            implied_after_credit=3000,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('0'))
            ]
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('3000')
        assert result.contract_fully_prepaid == False
        assert result.updated_payments[0]['amount_paid'] == 3000
        assert result.updated_payments[0]['remaining'] == 2000

    def test_implied_exceeds_total_owed(self, applicator):
        """Implied $10000 but only $5000 owed → only $5000 advance fees."""
        ctx = self._make_context(
            implied_after_credit=10000,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('0'))
            ]
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('5000')
        assert result.implied_after_subscription == Decimal('5000')
        assert result.contract_fully_prepaid == True

    def test_multiple_payments_chronological_order(self, applicator):
        """Payments are applied in chronological order."""
        ctx = self._make_context(
            implied_after_credit=4000,
            payments=[
                FuturePayment("p2", "2026-09-01", Decimal('3000'), Decimal('0')),
                FuturePayment("p1", "2026-06-01", Decimal('2000'), Decimal('0')),
                FuturePayment("p3", "2026-12-01", Decimal('5000'), Decimal('0'))
            ]
        )
        result = applicator.apply(ctx)
        
        # Should apply to p1 (June) first, then p2 (Sept)
        # 4000 covers: p1 fully (2000) + p2 partially (2000)
        assert result.advance_fees_created == Decimal('4000')
        
        # Find payments by ID
        payments_by_id = {p['payment_id']: p for p in result.updated_payments}
        assert payments_by_id['p1']['remaining'] == 0  # Fully paid
        assert payments_by_id['p2']['remaining'] == 1000  # 2000 of 3000 paid
        assert payments_by_id['p3']['remaining'] == 5000  # Untouched

    def test_partially_paid_payment_considered(self, applicator):
        """Already partially paid payments are handled correctly."""
        ctx = self._make_context(
            implied_after_credit=3000,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('2000'))
            ]
        )
        result = applicator.apply(ctx)
        
        # Owed: 5000 - 2000 = 3000
        # Implied covers exactly 3000
        assert result.advance_fees_created == Decimal('3000')
        assert result.updated_payments[0]['amount_paid'] == 5000
        assert result.updated_payments[0]['remaining'] == 0
        assert result.contract_fully_prepaid == True

    def test_no_payments_is_fully_prepaid(self, applicator):
        """No future payments = contract fully prepaid."""
        ctx = self._make_context(
            implied_after_credit=5000,
            payments=[]
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('0')
        assert result.contract_fully_prepaid == True
        assert result.implied_after_subscription == Decimal('5000')

    def test_payg_skips_subscription_entirely(self, applicator):
        """PAYG contracts don't use subscription system."""
        ctx = self._make_context(
            implied_after_credit=5000,
            payments=[
                FuturePayment("p1", "2026-06-01", Decimal('5000'), Decimal('0'))
            ],
            is_payg=True
        )
        result = applicator.apply(ctx)
        
        assert result.advance_fees_created == Decimal('0')
        assert result.contract_fully_prepaid == True
        assert result.updated_payments == []

    def _make_context(
        self,
        implied_after_credit: float,
        payments: list,
        is_payg: bool = False
    ) -> ProcessingContext:
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
            current_credit=Decimal('0'),
            current_debt=Decimal('0'),
            is_in_commissions_mode=False,
            future_payments=payments
        )
        ctx = ProcessingContext(deal=deal, contract=contract, initial_state=state)
        ctx.fees = FeeCalculation(implied_total=Decimal('5000'))
        ctx.credit = CreditApplication(
            implied_after_credit=Decimal(str(implied_after_credit))
        )
        return ctx
