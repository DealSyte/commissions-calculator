"""
Cost Cap Enforcer

Applies cost cap limits to Finalis commissions.
"""

from decimal import Decimal
from ..models import ProcessingContext, CommissionCalculation


class CostCapEnforcer:
    """Enforces cost cap limits on commissions."""

    def apply(self, ctx: ProcessingContext) -> CommissionCalculation:
        """
        Apply cost cap if configured.
        
        Cost cap types:
        - "annual": Limits total_paid_this_contract_year
        - "total": Limits total_paid_all_time
        
        Priority: Advance fees take priority over commissions.
        If cap is exceeded, commissions are reduced first.
        """
        contract = ctx.contract
        commission = ctx.commission

        # Check if cost cap exists
        if contract.cost_cap_type is None or contract.cost_cap_amount is None:
            return commission

        cap_amount = contract.cost_cap_amount
        state = ctx.initial_state
        advance_fees = ctx.subscription.advance_fees_created
        commissions_before_cap = commission.finalis_commissions_before_cap
        implied_total = ctx.fees.implied_total

        # Get appropriate tracking amount
        if contract.cost_cap_type == "annual":
            total_paid = state.total_paid_this_contract_year
        elif contract.cost_cap_type == "total":
            total_paid = state.total_paid_all_time
        else:
            # Invalid cap type - no cap applies
            return commission

        # Calculate available space under cap
        available_space = max(Decimal('0'), cap_amount - total_paid)

        # Total we want to charge
        total_to_charge = advance_fees + commissions_before_cap

        if total_to_charge <= available_space:
            # Everything fits - no change needed
            return commission

        # We exceed the cap - reduce commissions (advance fees have priority)
        space_for_commissions = max(Decimal('0'), available_space - advance_fees)
        commissions_after_cap = min(commissions_before_cap, space_for_commissions)

        # Calculate amount not charged
        amount_not_charged = implied_total - (advance_fees + commissions_after_cap)
        amount_not_charged = max(Decimal('0'), amount_not_charged)

        # Return updated commission with cap applied
        return CommissionCalculation(
            finalis_commissions_before_cap=commissions_before_cap,
            finalis_commissions=commissions_after_cap,
            amount_not_charged_due_to_cap=amount_not_charged,
            entered_commissions_mode=commission.entered_commissions_mode,
            new_commissions_mode=commission.new_commissions_mode,
            payg_arr_contribution=commission.payg_arr_contribution
        )
