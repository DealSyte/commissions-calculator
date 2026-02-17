"""
Subscription Fee Calculator

Handles advance subscription fee creation from remaining implied costs.
"""

from decimal import Decimal

from ..models import FuturePayment, ProcessingContext, SubscriptionApplication


def to_money(value: Decimal) -> float:
    """Convert Decimal to float with 2 decimal places."""
    return round(float(value), 2)


class SubscriptionApplicator:
    """Manages advance subscription fee application."""

    def apply(self, ctx: ProcessingContext) -> SubscriptionApplication:
        """
        Apply remaining implied cost to future subscription payments.

        For Standard Contracts:
        - Implied cost after credit is applied to future payments
        - Payments are applied in chronological order

        For PAYG Contracts:
        - No subscription system - skip entirely
        """
        contract = ctx.contract

        if contract.is_pay_as_you_go:
            return SubscriptionApplication(
                advance_fees_created=Decimal('0'),
                contract_fully_prepaid=True,  # PAYG is always "prepaid"
                updated_payments=[],
                implied_after_subscription=ctx.credit.implied_after_credit
            )

        return self._apply_standard(
            implied_remaining=ctx.credit.implied_after_credit,
            future_payments=ctx.initial_state.future_payments
        )

    def _apply_standard(
        self,
        implied_remaining: Decimal,
        future_payments: list[FuturePayment]
    ) -> SubscriptionApplication:
        """Apply implied cost to future subscription payments."""

        if implied_remaining <= 0:
            # No advance fees needed
            updated = self._format_payments_unchanged(future_payments)
            return SubscriptionApplication(
                advance_fees_created=Decimal('0'),
                contract_fully_prepaid=len(future_payments) == 0,
                updated_payments=updated,
                implied_after_subscription=Decimal('0')
            )

        # Calculate total owed across all future payments
        total_owed = sum(p.amount_owed for p in future_payments)

        # Advance fees cannot exceed total owed
        advance_created = min(implied_remaining, total_owed)

        # Apply to payments in chronological order
        updated_payments, remaining = self._apply_to_payments(
            future_payments, advance_created
        )

        # Check if fully prepaid
        fully_prepaid = all(
            Decimal(str(p['remaining'])) == Decimal('0')
            for p in updated_payments
        )

        # Special case: no future payments = fully prepaid
        if len(future_payments) == 0:
            fully_prepaid = True

        implied_after = implied_remaining - advance_created

        return SubscriptionApplication(
            advance_fees_created=advance_created,
            contract_fully_prepaid=fully_prepaid,
            updated_payments=updated_payments,
            implied_after_subscription=implied_after
        )

    def _apply_to_payments(
        self,
        payments: list[FuturePayment],
        advance_amount: Decimal
    ) -> tuple[list[dict], Decimal]:
        """
        Apply advance amount to payments in chronological order.
        Returns (updated_payments, remaining_advance).
        """
        # Sort by due date
        sorted_payments = sorted(payments, key=lambda p: p.due_date)

        remaining = advance_amount
        updated = []

        for payment in sorted_payments:
            owed = payment.amount_owed

            if remaining >= owed:
                # Fully cover this payment
                new_paid = payment.amount_paid + owed
                remaining -= owed
            elif remaining > 0:
                # Partially cover
                new_paid = payment.amount_paid + remaining
                remaining = Decimal('0')
            else:
                # No advance left
                new_paid = payment.amount_paid

            updated.append({
                "payment_id": payment.payment_id,
                "due_date": payment.due_date,
                "original_amount": to_money(payment.amount_due),
                "amount_paid": to_money(new_paid),
                "remaining": to_money(payment.amount_due - new_paid)
            })

        return updated, remaining

    def _format_payments_unchanged(self, payments: list[FuturePayment]) -> list[dict]:
        """Format payments without changes."""
        return [
            {
                "payment_id": p.payment_id,
                "due_date": p.due_date,
                "original_amount": to_money(p.amount_due),
                "amount_paid": to_money(p.amount_paid),
                "remaining": to_money(p.amount_owed)
            }
            for p in payments
        ]
