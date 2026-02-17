"""
Fee Calculators for Finalis Contract Engine

Each calculator is responsible for a specific type of fee calculation.
All use Decimal for precision with ROUND_HALF_UP rounding.
"""

from decimal import ROUND_HALF_UP, Decimal

from ..models import FeeCalculation, LehmanTier, ProcessingContext


def quantize_money(value: Decimal) -> Decimal:
    """Round to 2 decimal places using banker's rounding."""
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class FeeCalculator:
    """Calculates all standard fees for a deal."""

    # Fee rates as class constants
    FINRA_RATE = Decimal('0.004732')
    DISTRIBUTION_RATE = Decimal('0.10')
    SOURCING_RATE = Decimal('0.10')
    DEAL_EXEMPT_RATE = Decimal('0.015')

    def calculate(self, ctx: ProcessingContext) -> FeeCalculation:
        """Calculate all fees and return FeeCalculation result."""
        deal = ctx.deal
        amount = deal.total_for_calculations
        dist_sourcing_amount = deal.amount_for_dist_sourcing

        return FeeCalculation(
            finra_fee=self._calculate_finra(amount, deal.has_finra_fee),
            distribution_fee=self._calculate_distribution(dist_sourcing_amount, deal.is_distribution_fee),
            sourcing_fee=self._calculate_sourcing(dist_sourcing_amount, deal.is_sourcing_fee),
            implied_total=self._calculate_implied(ctx)
        )

    def _calculate_finra(self, amount: Decimal, has_finra_fee: bool) -> Decimal:
        """Calculate FINRA/SIPC fee (0.4732%)."""
        if not has_finra_fee:
            return Decimal('0')
        return quantize_money(amount * self.FINRA_RATE)

    def _calculate_distribution(self, amount: Decimal, is_applicable: bool) -> Decimal:
        """Calculate distribution fee (10% if applicable)."""
        if not is_applicable:
            return Decimal('0')
        return quantize_money(amount * self.DISTRIBUTION_RATE)

    def _calculate_sourcing(self, amount: Decimal, is_applicable: bool) -> Decimal:
        """Calculate sourcing fee (10% if applicable)."""
        if not is_applicable:
            return Decimal('0')
        return quantize_money(amount * self.SOURCING_RATE)

    def _calculate_implied(self, ctx: ProcessingContext) -> Decimal:
        """
        Calculate IMPLIED (BD Cost).

        Priority order:
        1. Preferred Rate (deal-specific override)
        2. Deal Exempt (1.5%)
        3. Lehman Progressive Tiers
        4. Fixed Rate
        """
        deal = ctx.deal
        contract = ctx.contract
        amount = deal.total_for_calculations

        # Priority 1: Preferred Rate
        if deal.has_preferred_rate and deal.preferred_rate is not None:
            return quantize_money(amount * deal.preferred_rate)

        # Priority 2: Deal Exempt
        if deal.is_deal_exempt:
            return quantize_money(amount * self.DEAL_EXEMPT_RATE)

        # Priority 3: Lehman Tiers
        if contract.rate_type == 'lehman' and contract.lehman_tiers:
            return self._calculate_lehman(
                amount,
                contract.lehman_tiers,
                contract.accumulated_success_fees
            )

        # Priority 4: Fixed Rate
        if contract.fixed_rate is not None:
            return quantize_money(amount * contract.fixed_rate)

        raise ValueError("Invalid rate configuration - no applicable rate found")

    def _calculate_lehman(
        self,
        deal_amount: Decimal,
        tiers: list[LehmanTier],
        accumulated_before: Decimal
    ) -> Decimal:
        """
        Calculate implied using Lehman progressive tiers.

        Handles:
        - Historical accumulation (starts at correct tier)
        - Gaps between tiers (jumps to next tier)
        - Infinite upper bound on final tier
        """
        acc = accumulated_before
        remaining = deal_amount
        implied = Decimal('0')

        for tier in tiers:
            if remaining <= 0:
                break

            # Handle gap between current position and tier start
            if acc < tier.lower_bound:
                gap = tier.lower_bound - acc
                if gap <= remaining:
                    remaining -= gap
                    acc = tier.lower_bound
                else:
                    # Deal ends before reaching this tier
                    break

            # Calculate tier capacity
            if tier.upper_bound is None:
                # Infinite tier - allocate all remaining
                allocated = remaining
            else:
                used_in_tier = max(Decimal('0'), acc - tier.lower_bound)
                tier_capacity = tier.upper_bound - tier.lower_bound
                remaining_capacity = max(Decimal('0'), tier_capacity - used_in_tier)
                allocated = min(remaining_capacity, remaining)

            # Calculate commission for this allocation
            tier_commission = quantize_money(allocated * tier.rate)
            implied += tier_commission

            # Update tracking
            remaining -= allocated
            acc += allocated

        return implied
