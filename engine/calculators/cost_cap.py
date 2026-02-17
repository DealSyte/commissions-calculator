"""
Cost Cap Enforcer

Applies cost cap limits to Finalis commissions.
"""

from decimal import Decimal

from ..models import CommissionCalculation, ProcessingContext


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

        For PAYG contracts, the cost cap applies to the TOTAL going to Finalis
        (ARR contribution + excess commissions), not just the excess.
        """
        contract = ctx.contract
        commission = ctx.commission

        # Check if cost cap exists
        if contract.cost_cap_type is None or contract.cost_cap_amount is None:
            return commission

        cap_amount = contract.cost_cap_amount
        state = ctx.initial_state
        advance_fees = ctx.subscription.advance_fees_created
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

        # For PAYG, the total to charge includes both ARR contribution and excess
        # For standard contracts, payg_arr_contribution is always 0
        payg_arr = commission.payg_arr_contribution
        excess_commissions = commission.finalis_commissions_before_cap
        total_finalis_before_cap = payg_arr + excess_commissions

        # Total we want to charge (advance fees + all Finalis amounts)
        total_to_charge = advance_fees + total_finalis_before_cap

        if total_to_charge <= available_space:
            # Everything fits - no change needed
            return commission

        # We exceed the cap - reduce Finalis amounts (advance fees have priority)
        space_for_finalis = max(Decimal('0'), available_space - advance_fees)

        # For PAYG, we need to re-split the capped total between ARR and excess
        # ARR has priority over excess commissions
        if contract.is_pay_as_you_go:
            # First allocate to ARR (up to the original ARR contribution)
            arr_after_cap = min(payg_arr, space_for_finalis)
            # Remainder goes to excess commissions
            excess_after_cap = max(Decimal('0'), space_for_finalis - arr_after_cap)

            # Recalculate entered_commissions_mode based on actual ARR coverage
            # If ARR contribution was reduced by cap, we may not have fully covered ARR
            if arr_after_cap < payg_arr:
                # ARR was capped, so not fully covered → don't enter commissions mode
                entered_commissions_mode = False
                new_commissions_mode = state.is_in_commissions_mode  # Keep current mode
            else:
                # ARR fully covered (post-cap), keep original determination
                entered_commissions_mode = commission.entered_commissions_mode
                new_commissions_mode = commission.new_commissions_mode
        else:
            # Standard contracts: no ARR, just commissions
            arr_after_cap = Decimal('0')
            excess_after_cap = min(excess_commissions, space_for_finalis)
            entered_commissions_mode = commission.entered_commissions_mode
            new_commissions_mode = commission.new_commissions_mode

        # Calculate amount not charged
        amount_not_charged = implied_total - (advance_fees + space_for_finalis)
        amount_not_charged = max(Decimal('0'), amount_not_charged)

        # Return updated commission with cap applied
        return CommissionCalculation(
            finalis_commissions_before_cap=excess_commissions,
            finalis_commissions=excess_after_cap,
            amount_not_charged_due_to_cap=amount_not_charged,
            entered_commissions_mode=entered_commissions_mode,
            new_commissions_mode=new_commissions_mode,
            payg_arr_contribution=arr_after_cap
        )
