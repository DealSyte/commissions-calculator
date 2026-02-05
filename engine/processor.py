"""
Deal Processor - Main Orchestrator

Coordinates the deal processing pipeline through discrete, testable steps.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

from .models import (
    DealInput, DealResult, ProcessingContext, PaygTracking
)
from .validators import InputValidator
from .calculators import (
    FeeCalculator,
    DebtCollector,
    CreditApplicator,
    SubscriptionApplicator,
    CommissionCalculator,
    CostCapEnforcer,
    PayoutCalculator
)
from .output import OutputBuilder


class DealProcessor:
    """
    Main orchestrator for deal processing.
    
    Implements a clear pipeline pattern:
    1. Validate Input
    2. Build Context
    3. Calculate Fees
    4. Collect Debt
    5. Apply Credit
    6. Apply Subscription Fees
    7. Calculate Commissions
    8. Apply Cost Cap
    9. Calculate Net Payout
    10. Build Output
    """

    def __init__(self):
        # Initialize all calculators
        self.validator = InputValidator()
        self.fee_calculator = FeeCalculator()
        self.debt_collector = DebtCollector()
        self.credit_applicator = CreditApplicator()
        self.subscription_applicator = SubscriptionApplicator()
        self.commission_calculator = CommissionCalculator()
        self.cost_cap_enforcer = CostCapEnforcer()
        self.payout_calculator = PayoutCalculator()
        self.output_builder = OutputBuilder()

    def process(self, input_data: DealInput) -> DealResult:
        """
        Process a deal through the complete pipeline.
        
        Args:
            input_data: Validated DealInput object
            
        Returns:
            DealResult with all calculations and state updates
        """
        # Step 1: Validate
        self.validator.validate(input_data)

        # Step 2: Build initial context
        ctx = self._build_context(input_data)

        # Step 3: Calculate fees (FINRA, Distribution, Sourcing, Implied)
        ctx.fees = self.fee_calculator.calculate(ctx)

        # Step 4: Collect debt
        ctx.debt = self.debt_collector.collect(ctx)

        # Step 5: Apply credit
        ctx.credit = self.credit_applicator.apply(ctx)

        # Step 6: Apply subscription fees
        ctx.subscription = self.subscription_applicator.apply(ctx)

        # Step 7: Calculate commissions
        ctx.commission = self.commission_calculator.calculate(ctx)

        # Step 8: Apply cost cap
        ctx.commission = self.cost_cap_enforcer.apply(ctx)

        # Step 9: Calculate net payout
        ctx.net_payout = self.payout_calculator.calculate(ctx)

        # Step 9b: Build PAYG tracking if applicable
        if input_data.contract.is_pay_as_you_go:
            ctx.payg_tracking = self._build_payg_tracking(ctx)

        # Step 10: Build output
        return self.output_builder.build(ctx)

    def process_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a deal from raw dictionary input.
        
        Convenience method for API usage.
        """
        input_data = DealInput.from_dict(data)
        result = self.process(input_data)
        return self._result_to_dict(result)

    def _build_context(self, input_data: DealInput) -> ProcessingContext:
        """Build the initial processing context."""
        contract_year = 1
        if input_data.contract.contract_start_date:
            contract_year = DebtCollector.calculate_contract_year(
                input_data.contract.contract_start_date,
                input_data.deal.deal_date
            )

        return ProcessingContext(
            deal=input_data.deal,
            contract=input_data.contract,
            initial_state=input_data.state,
            contract_year=contract_year
        )

    def _build_payg_tracking(self, ctx: ProcessingContext) -> PaygTracking:
        """Build PAYG tracking information."""
        contract = ctx.contract
        state = ctx.initial_state
        commission = ctx.commission

        arr = contract.annual_subscription
        
        # Total accumulated = previous + this deal's contribution
        total_accumulated = (
            state.payg_commissions_accumulated +
            commission.payg_arr_contribution +
            commission.finalis_commissions
        )

        # Calculate coverage percentage using Decimal arithmetic for precision
        if arr > 0:
            coverage_decimal = (total_accumulated / arr) * Decimal('100')
            coverage_pct = float(coverage_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            coverage_pct = 0.0

        return PaygTracking(
            arr_target=arr,
            arr_contribution_this_deal=commission.payg_arr_contribution,
            finalis_commissions_this_deal=commission.finalis_commissions,
            commissions_accumulated=total_accumulated,
            remaining_to_cover_arr=max(Decimal('0'), arr - total_accumulated),
            arr_coverage_percentage=coverage_pct
        )

    def _result_to_dict(self, result: DealResult) -> Dict[str, Any]:
        """Convert DealResult to dictionary for API response."""
        output = {
            "deal_summary": result.deal_summary,
            "calculations": result.calculations,
            "state_changes": result.state_changes,
            "updated_future_payments": result.updated_future_payments,
            "updated_contract_state": result.updated_contract_state
        }
        if result.payg_tracking:
            output["payg_tracking"] = result.payg_tracking
        return output


# =============================================================================
# CONVENIENCE FUNCTIONS (Backward Compatibility)
# =============================================================================

def process_deal_from_dict(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a deal from Python dict and return Python dict.
    Backward compatible with existing API.
    """
    processor = DealProcessor()
    return processor.process_from_dict(input_data)


def process_deal_from_json(json_input: str) -> str:
    """
    Process a deal from JSON string input and return JSON string output.
    Backward compatible with existing API.
    """
    import json
    
    try:
        input_data = json.loads(json_input)
        processor = DealProcessor()
        result = processor.process_from_dict(input_data)
        return json.dumps(result, indent=2)

    except ValueError as e:
        error_response = {"error": str(e), "status": "validation_failed"}
        return json.dumps(error_response, indent=2)

    except Exception as e:
        error_response = {"error": str(e), "status": "failed"}
        return json.dumps(error_response, indent=2)
