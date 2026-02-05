"""
Unit Tests for Commission Calculator

Tests verify commission calculation for Standard and PAYG contracts.
"""

import pytest
from decimal import Decimal
from engine.calculators.commission import CommissionCalculator
from engine.models import (
    Deal, Contract, ContractState, ProcessingContext,
    FeeCalculation, DebtCollection, CreditApplication, SubscriptionApplication
)


class TestStandardContractCommissions:
    """Test commission calculation for standard contracts."""

    @pytest.fixture
    def calculator(self):
        return CommissionCalculator()

    def test_no_commission_when_not_fully_prepaid(self, calculator):
        """Before contract is fully prepaid, no commissions."""
        ctx = self._make_standard_context(
            implied_total=5000,
            implied_after_subscription=0,  # All went to subscription
            contract_fully_prepaid=False,
            is_in_commissions_mode=False
        )
        result = calculator.calculate(ctx)
        
        assert result.finalis_commissions == Decimal('0')
        assert result.new_commissions_mode == False
        assert result.entered_commissions_mode == False

    def test_commission_when_becomes_fully_prepaid(self, calculator):
        """When contract becomes fully prepaid, remaining implied becomes commission."""
        ctx = self._make_standard_context(
            implied_total=5000,
            implied_after_subscription=2000,  # 3000 to subscription, 2000 remains
            contract_fully_prepaid=True,
            is_in_commissions_mode=False
        )
        result = calculator.calculate(ctx)
        
        assert result.finalis_commissions == Decimal('2000')
        assert result.new_commissions_mode == True
        assert result.entered_commissions_mode == True

    def test_all_implied_is_commission_when_already_in_commissions_mode(self, calculator):
        """Once in commissions mode, all implied becomes commission."""
        ctx = self._make_standard_context(
            implied_total=5000,
            implied_after_subscription=0,  # Ignored in commissions mode
            contract_fully_prepaid=True,
            is_in_commissions_mode=True
        )
        result = calculator.calculate(ctx)
        
        # All implied goes to commission, not subscription
        assert result.finalis_commissions == Decimal('5000')
        assert result.new_commissions_mode == True
        assert result.entered_commissions_mode == False  # Already was in mode

    def test_zero_implied_means_zero_commission(self, calculator):
        """Edge case: no implied cost."""
        ctx = self._make_standard_context(
            implied_total=0,
            implied_after_subscription=0,
            contract_fully_prepaid=True,
            is_in_commissions_mode=True
        )
        result = calculator.calculate(ctx)
        
        assert result.finalis_commissions == Decimal('0')

    def _make_standard_context(
        self,
        implied_total: float,
        implied_after_subscription: float,
        contract_fully_prepaid: bool,
        is_in_commissions_mode: bool
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
            is_pay_as_you_go=False
        )
        state = ContractState(
            current_credit=Decimal('0'),
            current_debt=Decimal('0'),
            is_in_commissions_mode=is_in_commissions_mode
        )
        ctx = ProcessingContext(deal=deal, contract=contract, initial_state=state)
        ctx.fees = FeeCalculation(implied_total=Decimal(str(implied_total)))
        ctx.subscription = SubscriptionApplication(
            contract_fully_prepaid=contract_fully_prepaid,
            implied_after_subscription=Decimal(str(implied_after_subscription))
        )
        return ctx


class TestPaygCommissions:
    """Test commission calculation for Pay-As-You-Go contracts."""

    @pytest.fixture
    def calculator(self):
        return CommissionCalculator()

    def test_all_implied_to_arr_when_arr_not_covered(self, calculator):
        """When ARR not yet covered, all implied goes to ARR, no commission."""
        ctx = self._make_payg_context(
            implied_total=5000,
            arr=10000,
            accumulated=0
        )
        result = calculator.calculate(ctx)
        
        assert result.payg_arr_contribution == Decimal('5000')
        assert result.finalis_commissions == Decimal('0')
        assert result.new_commissions_mode == False

    def test_all_implied_to_commission_when_arr_already_covered(self, calculator):
        """When ARR fully covered, all implied becomes commission."""
        ctx = self._make_payg_context(
            implied_total=5000,
            arr=10000,
            accumulated=10000  # ARR already met
        )
        result = calculator.calculate(ctx)
        
        assert result.payg_arr_contribution == Decimal('0')
        assert result.finalis_commissions == Decimal('5000')
        assert result.new_commissions_mode == True

    def test_partial_arr_partial_commission(self, calculator):
        """When deal partially covers remaining ARR."""
        ctx = self._make_payg_context(
            implied_total=5000,
            arr=10000,
            accumulated=8000  # 2000 remaining to cover
        )
        result = calculator.calculate(ctx)
        
        # 2000 fills ARR, 3000 becomes commission
        assert result.payg_arr_contribution == Decimal('2000')
        assert result.finalis_commissions == Decimal('3000')
        assert result.new_commissions_mode == True
        assert result.entered_commissions_mode == True

    def test_exactly_covers_arr(self, calculator):
        """Deal exactly covers remaining ARR."""
        ctx = self._make_payg_context(
            implied_total=5000,
            arr=10000,
            accumulated=5000  # Exactly 5000 remaining
        )
        result = calculator.calculate(ctx)
        
        assert result.payg_arr_contribution == Decimal('5000')
        assert result.finalis_commissions == Decimal('0')
        assert result.new_commissions_mode == False  # No commissions generated

    def test_arr_over_covered(self, calculator):
        """Accumulated already exceeds ARR."""
        ctx = self._make_payg_context(
            implied_total=5000,
            arr=10000,
            accumulated=15000  # Way over ARR
        )
        result = calculator.calculate(ctx)
        
        assert result.payg_arr_contribution == Decimal('0')
        assert result.finalis_commissions == Decimal('5000')

    def _make_payg_context(
        self,
        implied_total: float,
        arr: float,
        accumulated: float
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
            is_pay_as_you_go=True,
            annual_subscription=Decimal(str(arr))
        )
        state = ContractState(
            current_credit=Decimal('0'),
            current_debt=Decimal('0'),
            is_in_commissions_mode=False,
            payg_commissions_accumulated=Decimal(str(accumulated))
        )
        ctx = ProcessingContext(deal=deal, contract=contract, initial_state=state)
        ctx.fees = FeeCalculation(implied_total=Decimal(str(implied_total)))
        ctx.subscription = SubscriptionApplication(
            contract_fully_prepaid=True,
            implied_after_subscription=Decimal(str(implied_total))
        )
        return ctx
