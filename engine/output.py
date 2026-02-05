"""
Output Builder

Constructs the final API response from processing context.
"""

from decimal import Decimal
from typing import Optional
from .models import ProcessingContext, DealResult, PaygTracking


def to_money(value: Decimal) -> float:
    """Convert Decimal to float with 2 decimal places."""
    return round(float(value), 2)


def _fmt(value) -> str:
    """Format a number as currency string for descriptions."""
    return f"${value:,.2f}"


class OutputBuilder:
    """Builds the final output response."""

    def build(self, ctx: ProcessingContext) -> DealResult:
        """Construct the complete deal result from processing context."""
        return DealResult(
            deal_summary=self._build_deal_summary(ctx),
            calculations=self._build_calculations(ctx),
            state_changes=self._build_state_changes(ctx),
            updated_future_payments=ctx.subscription.updated_payments,
            updated_contract_state=self._build_updated_state(ctx),
            payg_tracking=self._build_payg_tracking(ctx)
        )

    def _build_deal_summary(self, ctx: ProcessingContext) -> dict:
        """Build deal summary section."""
        deal = ctx.deal
        return {
            "deal_name": deal.name,
            "success_fees": to_money(deal.success_fees),
            "external_retainer": to_money(deal.external_retainer),
            "retainer_included_in_fees": (
                deal.include_retainer_in_fees 
                if deal.has_external_retainer else None
            ),
            "total_deal_value": to_money(deal.total_for_calculations),
            "deal_date": deal.deal_date,
            "has_finra_fee": deal.has_finra_fee
        }

    def _build_calculations(self, ctx: ProcessingContext) -> dict:
        """Build calculations section with value and dynamic description for each field."""
        deal = ctx.deal
        contract = ctx.contract
        fees = ctx.fees
        debt = ctx.debt
        credit = ctx.credit
        subscription = ctx.subscription
        commission = ctx.commission
        
        # Key values for descriptions
        total_amount = to_money(deal.total_for_calculations)
        success_fees = to_money(deal.success_fees)
        retainer = to_money(deal.external_retainer)
        
        # Determine rate info for implied calculation
        if deal.has_preferred_rate and deal.preferred_rate:
            rate_desc = f"preferred rate ({float(deal.preferred_rate)*100:.2f}%)"
        elif deal.is_deal_exempt:
            rate_desc = "deal exempt rate (1.5%)"
        elif contract.rate_type == 'lehman':
            rate_desc = "Lehman tiered rates"
        else:
            rate_desc = f"fixed rate ({float(contract.fixed_rate)*100:.2f}%)" if contract.fixed_rate else "fixed rate"

        return {
            # Starting point - articulate success fee and retainer separately
            "success_fee": {
                "value": success_fees,
                "description": "Success fee from this deal"
            },
            "external_retainer": {
                "value": retainer,
                "description": f"External retainer {'included' if deal.include_retainer_in_fees else 'excluded'} in fee calculations" if deal.has_external_retainer else "No external retainer for this deal"
            },
            "total_for_calculations": {
                "value": total_amount,
                "description": f"success_fee ({_fmt(success_fees)}) + retainer ({_fmt(retainer)}) = {_fmt(total_amount)}" if deal.has_external_retainer and deal.include_retainer_in_fees else f"success_fee ({_fmt(success_fees)}) - basis for all fee calculations"
            },
            
            # Fee breakdown
            "finra_fee": {
                "value": to_money(fees.finra_fee),
                "description": f"0.4732% × {_fmt(total_amount)} = {_fmt(to_money(fees.finra_fee))}" if deal.has_finra_fee else "FINRA fee not applicable for this deal"
            },
            "distribution_fee": {
                "value": to_money(fees.distribution_fee),
                "description": f"10% × {_fmt(total_amount)} = {_fmt(to_money(fees.distribution_fee))}" if deal.is_distribution_fee else "Distribution fee not applicable"
            },
            "sourcing_fee": {
                "value": to_money(fees.sourcing_fee),
                "description": f"10% × {_fmt(total_amount)} = {_fmt(to_money(fees.sourcing_fee))}" if deal.is_sourcing_fee else "Sourcing fee not applicable"
            },
            "implied_total": {
                "value": to_money(fees.implied_total),
                "description": f"Broker-dealer cost using {rate_desc} on {_fmt(total_amount)}"
            },
            
            # Debt collection breakdown
            "debt_collected": {
                "value": to_money(debt.total_collected),
                "description": f"current_debt ({_fmt(to_money(debt.regular_debt_collected))}) + deferred_subscription ({_fmt(to_money(debt.deferred_collected))}) = {_fmt(to_money(debt.total_collected))}"
            },
            "current_debt_collected": {
                "value": to_money(debt.regular_debt_collected),
                "description": f"Outstanding debt balance owed to Finalis, collected from current_debt of {_fmt(to_money(ctx.initial_state.current_debt))}"
            },
            "deferred_subscription_collected": {
                "value": to_money(debt.deferred_collected),
                "description": f"Unpaid subscription fees deferred from previous periods, collected for contract year {ctx.contract_year}"
            },
            
            # Credit flow breakdown
            "credit_from_existing": {
                "value": to_money(ctx.initial_state.current_credit),
                "description": f"Pre-existing credit balance the member has accumulated from previous deals or payments, available to offset broker-dealer costs"
            },
            "credit_from_debt": {
                "value": to_money(credit.credit_from_debt),
                "description": f"When debt is collected from deal proceeds, 100% converts to credit that offsets broker-dealer costs. Collected {_fmt(to_money(debt.total_collected))} → {_fmt(to_money(credit.credit_from_debt))} credit"
            },
            "total_credit_available": {
                "value": to_money(credit.total_credit_available),
                "description": f"Total credit available to offset implied broker-dealer cost: existing ({_fmt(to_money(ctx.initial_state.current_credit))}) + from_debt ({_fmt(to_money(credit.credit_from_debt))}) = {_fmt(to_money(credit.total_credit_available))}"
            },
            "credit_used_for_implied": {
                "value": to_money(credit.credit_used),
                "description": f"Credit applied to reduce the implied broker-dealer cost. Uses the lesser of available credit or implied cost: min({_fmt(to_money(credit.total_credit_available))}, {_fmt(to_money(fees.implied_total))}) = {_fmt(to_money(credit.credit_used))}"
            },
            "implied_after_credit": {
                "value": to_money(credit.implied_after_credit),
                "description": f"Remaining broker-dealer cost after credit is applied: {_fmt(to_money(fees.implied_total))} - {_fmt(to_money(credit.credit_used))} = {_fmt(to_money(credit.implied_after_credit))}"
            },
            
            # Subscription breakdown
            "advance_fees_created": {
                "value": to_money(subscription.advance_fees_created),
                "description": f"Portion of remaining implied cost applied to prepay future subscription invoices. Reduces what the member owes on upcoming subscription payments."
            },
            "implied_after_subscription": {
                "value": to_money(subscription.implied_after_subscription),
                "description": f"Remaining broker-dealer cost after subscription prepayment: {_fmt(to_money(credit.implied_after_credit))} - {_fmt(to_money(subscription.advance_fees_created))} = {_fmt(to_money(subscription.implied_after_subscription))}. This becomes Finalis commission if contract is fully prepaid."
            },
            
            # Commission breakdown
            "finalis_commissions_before_cap": {
                "value": to_money(commission.finalis_commissions_before_cap),
                "description": f"Broker-dealer commission Finalis earns from this deal, calculated before any cost cap limits are applied. Only charged when contract subscription is fully prepaid."
            },
            "finalis_commissions": {
                "value": to_money(commission.finalis_commissions),
                "description": f"Final commission after applying {ctx.contract.cost_cap_type} cost cap of {_fmt(to_money(ctx.contract.cost_cap_amount))}: {_fmt(to_money(commission.finalis_commissions))}" if ctx.contract.cost_cap_type and commission.amount_not_charged_due_to_cap > 0 else f"Final broker-dealer commission charged to member. No cost cap limit was reached."
            },
            "amount_not_charged_due_to_cap": {
                "value": to_money(commission.amount_not_charged_due_to_cap),
                "description": f"Commission amount waived because the {ctx.contract.cost_cap_type} cost cap of {_fmt(to_money(ctx.contract.cost_cap_amount))} was exceeded" if ctx.contract.cost_cap_type and commission.amount_not_charged_due_to_cap > 0 else "No commission was waived - cost cap not reached or no cap configured"
            },
            
            # Final payout
            "net_payout_to_client": {
                "value": to_money(ctx.net_payout),
                "description": f"success_fees ({_fmt(success_fees)}) - debt ({_fmt(to_money(debt.total_collected))}) - finra ({_fmt(to_money(fees.finra_fee))}) - distribution ({_fmt(to_money(fees.distribution_fee))}) - sourcing ({_fmt(to_money(fees.sourcing_fee))}) - advance_fees ({_fmt(to_money(subscription.advance_fees_created))}) - commissions ({_fmt(to_money(commission.finalis_commissions))})"
            }
        }

    def _build_state_changes(self, ctx: ProcessingContext) -> dict:
        """Build state changes section."""
        state = ctx.initial_state
        debt = ctx.debt
        credit = ctx.credit
        subscription = ctx.subscription
        commission = ctx.commission

        return {
            "initial_credit": to_money(state.current_credit),
            "final_credit": to_money(credit.credit_remaining),
            "initial_debt": to_money(state.current_debt),
            "final_debt": to_money(debt.remaining_debt),
            "initial_deferred": to_money(debt.applicable_deferred),
            "final_deferred": to_money(debt.remaining_deferred),
            "contract_year": ctx.contract_year if ctx.contract.contract_start_date else None,
            "contract_fully_prepaid": subscription.contract_fully_prepaid,
            "entered_commissions_mode": commission.entered_commissions_mode
        }

    def _build_updated_state(self, ctx: ProcessingContext) -> dict:
        """Build updated contract state section."""
        contract = ctx.contract
        state = ctx.initial_state
        debt = ctx.debt
        credit = ctx.credit
        subscription = ctx.subscription
        commission = ctx.commission
        deal = ctx.deal

        # Calculate new accumulated fees
        # NOTE: Only accumulate actual success fees, NOT external retainers.
        # Retainers are paid directly to member by client (outside Finalis)
        # and should not count toward Lehman tier progression.
        new_accumulated = contract.accumulated_success_fees + deal.success_fees

        # Calculate new payment totals (for cost cap tracking)
        # Include PAYG ARR contributions so cost caps are properly enforced
        payg_contribution = commission.payg_arr_contribution if contract.is_pay_as_you_go else Decimal('0')
        
        new_paid_this_year = (
            state.total_paid_this_contract_year +
            subscription.advance_fees_created +
            commission.finalis_commissions +
            payg_contribution
        )
        new_paid_all_time = (
            state.total_paid_all_time +
            subscription.advance_fees_created +
            commission.finalis_commissions +
            payg_contribution
        )

        result = {
            "current_credit": to_money(credit.credit_remaining),
            "current_debt": to_money(debt.remaining_debt),
            "deferred_subscription_fee": to_money(debt.remaining_deferred),
            "is_in_commissions_mode": commission.new_commissions_mode,
            "accumulated_success_fees": to_money(new_accumulated),
            "total_paid_this_contract_year": to_money(new_paid_this_year),
            "total_paid_all_time": to_money(new_paid_all_time)
        }

        # Add PAYG tracking if applicable
        if contract.is_pay_as_you_go and ctx.payg_tracking:
            result["payg_commissions_accumulated"] = to_money(
                ctx.payg_tracking.commissions_accumulated
            )

        # Update deferred schedule if it exists
        if state.deferred_schedule:
            result["deferred_schedule"] = self._update_deferred_schedule(ctx)

        return result

    def _update_deferred_schedule(self, ctx: ProcessingContext) -> list:
        """Update the deferred schedule with remaining amounts."""
        state = ctx.initial_state
        debt = ctx.debt
        contract_year = ctx.contract_year

        updated = []
        for entry in state.deferred_schedule:
            if entry.year == contract_year:
                updated.append({
                    "year": entry.year,
                    "amount": to_money(debt.remaining_deferred)
                })
            else:
                updated.append({
                    "year": entry.year,
                    "amount": to_money(entry.amount)
                })
        return updated

    def _build_payg_tracking(self, ctx: ProcessingContext) -> Optional[dict]:
        """Build PAYG tracking section if applicable."""
        if not ctx.contract.is_pay_as_you_go or not ctx.payg_tracking:
            return None

        tracking = ctx.payg_tracking
        return {
            "arr_target": to_money(tracking.arr_target),
            "arr_contribution_this_deal": to_money(tracking.arr_contribution_this_deal),
            "finalis_commissions_this_deal": to_money(tracking.finalis_commissions_this_deal),
            "commissions_accumulated": to_money(tracking.commissions_accumulated),
            "remaining_to_cover_arr": to_money(tracking.remaining_to_cover_arr),
            "arr_coverage_percentage": tracking.arr_coverage_percentage
        }
