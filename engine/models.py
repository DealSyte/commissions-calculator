"""
Domain Models for Finalis Contract Engine

These dataclasses provide type-safe representations of all business entities.
All monetary values use Decimal for precision.
"""

from dataclasses import dataclass, field
from decimal import Decimal

# =============================================================================
# INPUT MODELS
# =============================================================================


@dataclass
class LehmanTier:
    """A single tier in a Lehman fee structure."""

    lower_bound: Decimal
    upper_bound: Decimal | None  # None = infinite
    rate: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> "LehmanTier":
        return cls(
            lower_bound=Decimal(str(data["lower_bound"])),
            upper_bound=Decimal(str(data["upper_bound"])) if data.get("upper_bound") else None,
            rate=Decimal(str(data["rate"])),
        )


@dataclass
class FuturePayment:
    """A scheduled future subscription payment."""

    payment_id: str
    due_date: str
    amount_due: Decimal
    amount_paid: Decimal

    @property
    def amount_owed(self) -> Decimal:
        return self.amount_due - self.amount_paid

    @classmethod
    def from_dict(cls, data: dict) -> "FuturePayment":
        return cls(
            payment_id=data["payment_id"],
            due_date=data["due_date"],
            amount_due=Decimal(str(data["amount_due"])),
            amount_paid=Decimal(str(data["amount_paid"])),
        )


@dataclass
class DeferredEntry:
    """A year-specific deferred subscription fee."""

    year: int
    amount: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> "DeferredEntry":
        return cls(year=data["year"], amount=Decimal(str(data["amount"])))


@dataclass
class Deal:
    """The new deal being processed."""

    name: str
    success_fees: Decimal
    deal_date: str
    is_distribution_fee: bool
    is_sourcing_fee: bool
    is_deal_exempt: bool
    external_retainer: Decimal = Decimal("0")
    has_external_retainer: bool = False
    include_retainer_in_fees: bool = True
    has_finra_fee: bool = True
    has_preferred_rate: bool = False
    preferred_rate: Decimal | None = None

    @property
    def total_for_calculations(self) -> Decimal:
        """Calculate the total value used for fee calculations.

        When retainer is deducted (include_retainer_in_fees=True), all fees
        are calculated on the total including retainer for consistency.
        """
        if self.has_external_retainer and self.include_retainer_in_fees:
            return self.success_fees + self.external_retainer
        return self.success_fees

    @property
    def amount_for_dist_sourcing(self) -> Decimal:
        """Calculate the amount used for distribution/sourcing fee calculations.

        When retainer is deducted, dist/sourcing use the same total as all other fees
        for consistency (Lehman, FINRA, etc. all use total_for_calculations).
        """
        return self.total_for_calculations

    @classmethod
    def from_dict(cls, data: dict) -> "Deal":
        preferred = data.get("preferred_rate")
        return cls(
            name=data["deal_name"],
            success_fees=Decimal(str(data["success_fees"])),
            deal_date=data["deal_date"],
            is_distribution_fee=data["is_distribution_fee_true"],
            is_sourcing_fee=data["is_sourcing_fee_true"],
            is_deal_exempt=data["is_deal_exempt"],
            external_retainer=Decimal(str(data.get("external_retainer", 0))),
            has_external_retainer=data.get("has_external_retainer", False),
            # Support both 'include_retainer_in_fees' and legacy 'is_external_retainer_deducted'
            # When retainer is "deducted" from client payout, it means it's included in fee calculations
            include_retainer_in_fees=data.get(
                "include_retainer_in_fees", data.get("is_external_retainer_deducted", True)
            ),
            has_finra_fee=data.get("has_finra_fee", True),
            has_preferred_rate=data.get("has_preferred_rate", False),
            preferred_rate=Decimal(str(preferred)) if preferred is not None else None,
        )


@dataclass
class Contract:
    """Contract configuration and rules."""

    rate_type: str  # 'fixed' or 'lehman'
    accumulated_success_fees: Decimal
    is_pay_as_you_go: bool = False
    fixed_rate: Decimal | None = None
    lehman_tiers: list[LehmanTier] = field(default_factory=list)
    contract_start_date: str | None = None
    annual_subscription: Decimal = Decimal("0")
    cost_cap_type: str | None = None  # 'annual', 'total', or None
    cost_cap_amount: Decimal | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Contract":
        tiers = [LehmanTier.from_dict(t) for t in data.get("lehman_tiers", [])]
        cap_amount = data.get("cost_cap_amount")
        fixed = data.get("fixed_rate")
        return cls(
            rate_type=data["rate_type"],
            accumulated_success_fees=Decimal(str(data["accumulated_success_fees_before_this_deal"])),
            is_pay_as_you_go=data.get("is_pay_as_you_go", False),
            fixed_rate=Decimal(str(fixed)) if fixed is not None else None,
            lehman_tiers=tiers,
            contract_start_date=data.get("contract_start_date"),
            annual_subscription=Decimal(str(data.get("annual_subscription", 0))),
            cost_cap_type=data.get("cost_cap_type"),
            cost_cap_amount=Decimal(str(cap_amount)) if cap_amount is not None else None,
        )


@dataclass
class ContractState:
    """Current state of the contract (mutable over time)."""

    current_credit: Decimal
    current_debt: Decimal
    is_in_commissions_mode: bool
    future_payments: list[FuturePayment] = field(default_factory=list)
    deferred_schedule: list[DeferredEntry] = field(default_factory=list)
    deferred_subscription_fee: Decimal = Decimal("0")  # Legacy single deferred
    total_paid_this_contract_year: Decimal = Decimal("0")
    total_paid_all_time: Decimal = Decimal("0")
    payg_commissions_accumulated: Decimal = Decimal("0")

    @classmethod
    def from_dict(cls, data: dict) -> "ContractState":
        payments = [FuturePayment.from_dict(p) for p in data.get("future_subscription_fees", [])]
        deferred = [DeferredEntry.from_dict(d) for d in data.get("deferred_schedule", [])]
        return cls(
            current_credit=Decimal(str(data.get("current_credit", 0))),
            current_debt=Decimal(str(data.get("current_debt", 0))),
            is_in_commissions_mode=data.get("is_in_commissions_mode", False),
            future_payments=payments,
            deferred_schedule=deferred,
            deferred_subscription_fee=Decimal(str(data.get("deferred_subscription_fee", 0))),
            total_paid_this_contract_year=Decimal(str(data.get("total_paid_this_contract_year", 0))),
            total_paid_all_time=Decimal(str(data.get("total_paid_all_time", 0))),
            payg_commissions_accumulated=Decimal(str(data.get("payg_commissions_accumulated", 0))),
        )


@dataclass
class DealInput:
    """Complete input for processing a deal."""

    deal: Deal
    contract: Contract
    state: ContractState

    @classmethod
    def from_dict(cls, data: dict) -> "DealInput":
        return cls(
            deal=Deal.from_dict(data["deal"]),
            contract=Contract.from_dict(data["contract"]),
            state=ContractState.from_dict(data["state"]),
        )


# =============================================================================
# OUTPUT / RESULT MODELS
# =============================================================================


@dataclass
class FeeCalculation:
    """Results of fee calculations."""

    finra_fee: Decimal = Decimal("0")
    distribution_fee: Decimal = Decimal("0")
    sourcing_fee: Decimal = Decimal("0")
    implied_total: Decimal = Decimal("0")


@dataclass
class DebtCollection:
    """Results of debt collection step."""

    total_collected: Decimal = Decimal("0")
    regular_debt_collected: Decimal = Decimal("0")
    deferred_collected: Decimal = Decimal("0")
    remaining_debt: Decimal = Decimal("0")
    remaining_deferred: Decimal = Decimal("0")
    applicable_deferred: Decimal = Decimal("0")


@dataclass
class CreditApplication:
    """Results of credit application step."""

    credit_from_debt: Decimal = Decimal("0")
    total_credit_available: Decimal = Decimal("0")
    credit_used: Decimal = Decimal("0")
    credit_remaining: Decimal = Decimal("0")
    implied_after_credit: Decimal = Decimal("0")


@dataclass
class SubscriptionApplication:
    """Results of advance subscription fee application."""

    advance_fees_created: Decimal = Decimal("0")
    contract_fully_prepaid: bool = False
    updated_payments: list[dict] = field(default_factory=list)
    implied_after_subscription: Decimal = Decimal("0")


@dataclass
class CommissionCalculation:
    """Results of commission calculation."""

    finalis_commissions_before_cap: Decimal = Decimal("0")
    finalis_commissions: Decimal = Decimal("0")
    amount_not_charged_due_to_cap: Decimal = Decimal("0")
    entered_commissions_mode: bool = False
    new_commissions_mode: bool = False
    # PAYG specific
    payg_arr_contribution: Decimal = Decimal("0")


@dataclass
class PaygTracking:
    """PAYG-specific tracking information.

    Note: finalis_commissions_this_deal represents EXCESS commissions only
    (after ARR is covered). It does NOT include arr_contribution_this_deal.
    To calculate total Finalis charge, ADD arr_contribution_this_deal.
    """

    arr_target: Decimal = Decimal("0")
    arr_contribution_this_deal: Decimal = Decimal("0")
    finalis_commissions_this_deal: Decimal = Decimal("0")  # Excess only (does not include ARR)
    commissions_accumulated: Decimal = Decimal("0")
    remaining_to_cover_arr: Decimal = Decimal("0")
    arr_coverage_percentage: float = 0.0


@dataclass
class ProcessingContext:
    """
    Holds all intermediate state during deal processing.
    This is the "bag" that flows through the pipeline.
    """

    # Input (immutable during processing)
    deal: Deal
    contract: Contract
    initial_state: ContractState
    contract_year: int = 1

    # Step results (populated as we go)
    fees: FeeCalculation = field(default_factory=FeeCalculation)
    debt: DebtCollection = field(default_factory=DebtCollection)
    credit: CreditApplication = field(default_factory=CreditApplication)
    subscription: SubscriptionApplication = field(default_factory=SubscriptionApplication)
    commission: CommissionCalculation = field(default_factory=CommissionCalculation)

    # Final outputs
    net_payout: Decimal = Decimal("0")
    payg_tracking: PaygTracking | None = None


@dataclass
class DealResult:
    """Final output of deal processing."""

    deal_summary: dict
    calculations: dict
    state_changes: dict
    updated_future_payments: list
    updated_contract_state: dict
    payg_tracking: dict | None = None
