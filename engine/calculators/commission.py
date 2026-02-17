"""
Commission Calculator

Handles Finalis commission calculation for both Standard and PAYG contracts.
"""

from decimal import Decimal

from ..models import CommissionCalculation, ProcessingContext


class CommissionCalculator:
    """Calculates Finalis commissions based on contract type."""

    def calculate(self, ctx: ProcessingContext) -> CommissionCalculation:
        """
        Calculate Finalis commissions.

        Standard Contracts:
        - Commissions occur after contract is fully prepaid
        - Any remaining implied after subscription becomes commission

        PAYG Contracts:
        - Implied first fills the ARR bucket
        - Only after ARR is covered does implied become commission
        """
        contract = ctx.contract

        if contract.is_pay_as_you_go:
            return self._calculate_payg(ctx)

        return self._calculate_standard(ctx)

    def _calculate_standard(self, ctx: ProcessingContext) -> CommissionCalculation:
        """Calculate commissions for standard contracts."""
        state = ctx.initial_state
        subscription = ctx.subscription
        fees = ctx.fees

        is_in_commissions_mode = state.is_in_commissions_mode

        if is_in_commissions_mode:
            # Already in commissions mode - all implied becomes commission
            return CommissionCalculation(
                finalis_commissions_before_cap=fees.implied_total,
                finalis_commissions=fees.implied_total,
                entered_commissions_mode=False,
                new_commissions_mode=True,
                payg_arr_contribution=Decimal("0"),
            )

        if subscription.contract_fully_prepaid:
            # Just became fully prepaid - remaining implied becomes commission
            return CommissionCalculation(
                finalis_commissions_before_cap=subscription.implied_after_subscription,
                finalis_commissions=subscription.implied_after_subscription,
                entered_commissions_mode=True,
                new_commissions_mode=True,
                payg_arr_contribution=Decimal("0"),
            )

        # Not fully prepaid yet - no commissions
        return CommissionCalculation(
            finalis_commissions_before_cap=Decimal("0"),
            finalis_commissions=Decimal("0"),
            entered_commissions_mode=False,
            new_commissions_mode=False,
            payg_arr_contribution=Decimal("0"),
        )

    def _calculate_payg(self, ctx: ProcessingContext) -> CommissionCalculation:
        """
        Calculate commissions for Pay-As-You-Go contracts.

        Logic:
        - Implied first fills the ARR (annual_subscription) bucket
        - Once ARR is covered, additional implied becomes Finalis commission
        """
        contract = ctx.contract
        state = ctx.initial_state
        implied_total = ctx.fees.implied_total

        arr = contract.annual_subscription
        accumulated = state.payg_commissions_accumulated

        # How much ARR is left to cover?
        remaining_arr = max(Decimal("0"), arr - accumulated)

        if accumulated >= arr:
            # ARR already covered - all implied becomes commission
            return CommissionCalculation(
                finalis_commissions_before_cap=implied_total,
                finalis_commissions=implied_total,
                entered_commissions_mode=False,
                new_commissions_mode=True,
                payg_arr_contribution=Decimal("0"),
            )

        if implied_total < remaining_arr:
            # All implied goes to ARR (not enough to cover yet)
            return CommissionCalculation(
                finalis_commissions_before_cap=Decimal("0"),
                finalis_commissions=Decimal("0"),
                entered_commissions_mode=False,
                new_commissions_mode=False,
                payg_arr_contribution=implied_total,
            )

        # Implied covers remaining ARR (exactly or with excess)
        # Either way, we've entered commissions mode
        commission_amount = implied_total - remaining_arr

        return CommissionCalculation(
            finalis_commissions_before_cap=commission_amount,
            finalis_commissions=commission_amount,
            entered_commissions_mode=True,
            new_commissions_mode=True,
            payg_arr_contribution=remaining_arr,
        )
