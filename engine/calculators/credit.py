"""
Credit Application Calculator

Handles conversion of collected debt to credit and application against implied costs.
"""

from decimal import Decimal
from ..models import ProcessingContext, CreditApplication


class CreditApplicator:
    """Manages credit generation and application."""

    def apply(self, ctx: ProcessingContext) -> CreditApplication:
        """
        Process credit for the deal.
        
        For Standard Contracts:
        - Collected debt generates credit
        - Credit is applied against implied cost (unless in commissions mode)
        
        For PAYG Contracts:
        - No credit system - debt does not generate credit
        """
        contract = ctx.contract
        state = ctx.initial_state
        debt = ctx.debt
        implied_total = ctx.fees.implied_total

        if contract.is_pay_as_you_go:
            return self._apply_payg(implied_total)

        return self._apply_standard(
            current_credit=state.current_credit,
            debt_collected=debt.total_collected,
            implied_total=implied_total,
            is_in_commissions_mode=state.is_in_commissions_mode
        )

    def _apply_payg(self, implied_total: Decimal) -> CreditApplication:
        """PAYG contracts have no credit system."""
        return CreditApplication(
            credit_from_debt=Decimal('0'),
            total_credit_available=Decimal('0'),
            credit_used=Decimal('0'),
            credit_remaining=Decimal('0'),
            implied_after_credit=implied_total
        )

    def _apply_standard(
        self,
        current_credit: Decimal,
        debt_collected: Decimal,
        implied_total: Decimal,
        is_in_commissions_mode: bool
    ) -> CreditApplication:
        """
        Standard contract credit logic.
        
        - All collected debt (regular + deferred) generates credit
        - Credit absorbs implied cost unless already in commissions mode
        """
        # Debt collected becomes credit
        credit_from_debt = debt_collected
        total_available = current_credit + credit_from_debt

        if is_in_commissions_mode:
            # In commissions mode, credit is not used
            return CreditApplication(
                credit_from_debt=credit_from_debt,
                total_credit_available=total_available,
                credit_used=Decimal('0'),
                credit_remaining=total_available,
                implied_after_credit=implied_total
            )

        # Normal case: credit absorbs implied
        credit_used = min(implied_total, total_available)
        
        return CreditApplication(
            credit_from_debt=credit_from_debt,
            total_credit_available=total_available,
            credit_used=credit_used,
            credit_remaining=total_available - credit_used,
            implied_after_credit=implied_total - credit_used
        )
