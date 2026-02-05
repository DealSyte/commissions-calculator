"""
Debt Collection Calculator

Handles collection of regular debt and deferred subscription fees.
"""

from decimal import Decimal
from datetime import datetime
from .fees import quantize_money
from ..models import ProcessingContext, DebtCollection, ContractState


class DebtCollector:
    """Collects debt from deal success fees."""

    def collect(self, ctx: ProcessingContext) -> DebtCollection:
        """
        Collect debt from the deal's success fees.
        
        Order of collection:
        1. Regular debt (current_debt)
        2. Deferred subscription fees (based on contract year)
        """
        state = ctx.initial_state
        deal = ctx.deal

        # Determine applicable deferred amount
        applicable_deferred = self._get_applicable_deferred(ctx)

        # Total debt available to collect
        total_debt = state.current_debt + applicable_deferred

        # Collect up to the success_fees amount
        total_collected = min(deal.success_fees, total_debt)

        # Split between regular and deferred (regular debt has priority)
        if total_collected > 0:
            regular_collected = min(total_collected, state.current_debt)
            deferred_collected = total_collected - regular_collected
        else:
            regular_collected = Decimal('0')
            deferred_collected = Decimal('0')

        return DebtCollection(
            total_collected=total_collected,
            regular_debt_collected=regular_collected,
            deferred_collected=deferred_collected,
            remaining_debt=state.current_debt - regular_collected,
            remaining_deferred=applicable_deferred - deferred_collected,
            applicable_deferred=applicable_deferred
        )

    def _get_applicable_deferred(self, ctx: ProcessingContext) -> Decimal:
        """
        Get the deferred amount applicable to the current contract year.
        
        Logic:
        - If deferred_schedule exists: use amount for current contract year
        - Else if deferred_subscription_fee exists (legacy): use that
        - Else: return 0
        """
        state = ctx.initial_state
        contract = ctx.contract

        # Check for multi-year deferred schedule
        if state.deferred_schedule:
            contract_year = ctx.contract_year
            for entry in state.deferred_schedule:
                if entry.year == contract_year:
                    return entry.amount
            return Decimal('0')

        # Fallback to legacy single deferred
        return state.deferred_subscription_fee

    @staticmethod
    def calculate_contract_year(contract_start_date: str, deal_date: str) -> int:
        """
        Calculate which contract year we're in.
        
        Uses fixed 365-day years (not calendar years) as per PRD:
        - Year 1 = days 0-364
        - Year 2 = days 365-729
        - etc.
        
        NOTE: This intentionally does NOT account for leap years.
        Contract years are fixed 365-day periods for consistency.
        """
        start = datetime.strptime(contract_start_date, "%Y-%m-%d")
        deal = datetime.strptime(deal_date, "%Y-%m-%d")
        days_diff = (deal - start).days
        return (days_diff // 365) + 1
