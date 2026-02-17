"""
Input Validation for Finalis Contract Engine

Validates all input data before processing begins.
Raises ValueError with clear messages for any constraint violations.
"""

from .models import Contract, ContractState, Deal, DealInput


class InputValidator:
    """Validates deal input according to business rules."""

    def validate(self, input_data: DealInput) -> None:
        """
        Run all validations. Raises ValueError if any check fails.
        """
        self._validate_deal(input_data.deal)
        self._validate_state(input_data.state)
        self._validate_contract(input_data.contract, input_data.deal, input_data.state)
        self._validate_payg_constraints(input_data.contract, input_data.state)

    def _validate_deal(self, deal: Deal) -> None:
        """Validate deal-level constraints."""
        if deal.success_fees <= 0:
            raise ValueError(f"success_fees must be positive, got: {deal.success_fees}")

        if deal.external_retainer < 0:
            raise ValueError(f"external_retainer cannot be negative, got: {deal.external_retainer}")

        if deal.has_external_retainer:
            # DESIGN DECISION: include_retainer_in_fees defaults to True in the model.
            # We don't validate its presence here because:
            # 1. If omitted from API request, it defaults to True (include retainer in fees)
            # 2. If explicitly set to False, the retainer is excluded from fee calculations
            # 3. Both are valid use cases - no validation error needed
            if deal.external_retainer <= 0:
                raise ValueError(
                    f"external_retainer must be positive when has_external_retainer=True, "
                    f"got: {deal.external_retainer}"
                )

        if deal.has_preferred_rate:
            if deal.preferred_rate is None:
                raise ValueError("preferred_rate is required when has_preferred_rate=True")
            if not (0 <= deal.preferred_rate <= 1):
                raise ValueError(f"preferred_rate must be between 0 and 1, got: {deal.preferred_rate}")

    def _validate_state(self, state: ContractState) -> None:
        """Validate state-level constraints."""
        if state.current_credit < 0:
            raise ValueError(f"current_credit cannot be negative, got: {state.current_credit}")

        if state.current_debt < 0:
            raise ValueError(f"current_debt cannot be negative, got: {state.current_debt}")

        for payment in state.future_payments:
            if payment.amount_due < 0:
                raise ValueError(f"amount_due cannot be negative: {payment}")
            if payment.amount_paid < 0:
                raise ValueError(f"amount_paid cannot be negative: {payment}")
            if payment.amount_paid > payment.amount_due:
                raise ValueError(f"amount_paid cannot exceed amount_due: {payment}")

    def _validate_contract(self, contract: Contract, deal: Deal, state: ContractState) -> None:
        """Validate contract-level constraints."""
        if contract.rate_type not in ['fixed', 'lehman']:
            raise ValueError(f"Invalid rate_type: {contract.rate_type}. Must be 'fixed' or 'lehman'")

        if contract.rate_type == 'fixed':
            if contract.fixed_rate is None:
                raise ValueError("fixed_rate is required when rate_type='fixed'")
            if not (0 <= contract.fixed_rate <= 1):
                raise ValueError(f"fixed_rate must be between 0 and 1, got: {contract.fixed_rate}")

        if contract.rate_type == 'lehman':
            if not contract.lehman_tiers:
                raise ValueError("lehman_tiers is required when rate_type='lehman'")

            for i, tier in enumerate(contract.lehman_tiers):
                if not (0 <= tier.rate <= 1):
                    raise ValueError(f"Tier {i} rate must be between 0 and 1, got: {tier.rate}")

    def _validate_payg_constraints(self, contract: Contract, state: ContractState) -> None:
        """Validate Pay-As-You-Go specific constraints."""
        if not contract.is_pay_as_you_go:
            return

        if state.current_credit > 0:
            raise ValueError(
                "Pay-As-You-Go contracts cannot have credit. "
                "PAYG contracts have no credit system."
            )

        if len(state.future_payments) > 0:
            raise ValueError(
                "Pay-As-You-Go contracts cannot have future subscription fees. "
                "PAYG has no subscription prepayments."
            )
