"""
Payout Calculator

Calculates the net payout to the client after all deductions.
"""

from decimal import ROUND_HALF_UP, Decimal

from ..models import ProcessingContext


class PayoutCalculator:
    """Calculates net payout to client."""

    def calculate(self, ctx: ProcessingContext) -> Decimal:
        """
        Calculate net payout after all deductions.

        Net Payout = Success Fees
                   - Debt Collected
                   - FINRA Fee
                   - Distribution Fee
                   - Sourcing Fee
                   - Advance Subscription Fees
                   - Finalis Commissions
                   - PAYG ARR Contribution (if applicable)
        """
        deal = ctx.deal
        fees = ctx.fees
        debt = ctx.debt
        subscription = ctx.subscription
        commission = ctx.commission

        net = deal.success_fees
        net -= debt.total_collected
        net -= fees.finra_fee
        net -= fees.distribution_fee
        net -= fees.sourcing_fee
        net -= subscription.advance_fees_created
        net -= commission.finalis_commissions
        net -= commission.payg_arr_contribution

        return net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
