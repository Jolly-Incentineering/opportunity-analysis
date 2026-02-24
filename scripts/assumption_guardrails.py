"""
ASSUMPTION GUARDRAILS VALIDATOR
Validates financial assumptions based on source (Gong vs. web research).

Rules:
- Gong-sourced assumptions bypass ALL guardrails
- Web/manual assumptions must pass ROPS and accretion checks
- Total EBITDA accretion across all campaigns ≤ 15% of annual EBITDA
"""

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional
from enum import Enum


class AssumptionSource(str, Enum):
    """Source of financial assumption"""
    GONG = "gong"
    WEB = "web"
    MANUAL = "manual"


@dataclass
class ValidationResult:
    """Result of assumption validation"""
    valid: bool
    source: str
    field_name: str
    value: float
    rops: Optional[float] = None
    accretion_pct: Optional[float] = None
    action: Literal["accept", "flag", "adjust"] = "accept"
    reason: str = ""
    suggestion: Optional[str] = None


class AssumptionGuardrails:
    """Validates financial assumptions with guardrail enforcement"""

    # ROPS guardrails (unless from Gong)
    ROPS_MIN = 10.0
    ROPS_MAX = 30.0

    # Total EBITDA accretion ceiling
    EBITDA_ACCRETION_MAX_PCT = 15.0

    # Cost reasonableness thresholds
    COST_MIN = 0.01  # $0.01 minimum
    COST_MAX_QSR = 5000  # QSR hiring: ~$3,500 capped
    COST_MAX_MANUFACTURING = 10000  # Manufacturing hiring can be higher

    def __init__(self, industry: Literal["qsr", "manufacturing"] = "qsr"):
        self.industry = industry
        self.cost_max = (
            self.COST_MAX_QSR
            if industry == "qsr"
            else self.COST_MAX_MANUFACTURING
        )

    def validate_assumption(
        self,
        field_name: str,
        value: float,
        source: str,
        cost_assumption: Optional[float] = None,
        incentive_cost: Optional[float] = None,
    ) -> ValidationResult:
        """
        Validate a single assumption.

        Args:
            field_name: Name of the assumption (e.g., "Campaign 1 Uplift %")
            value: The assumption value
            source: "gong", "web", or "manual"
            cost_assumption: The cost associated with this assumption (for ROPS calc)
            incentive_cost: Per-unit incentive cost (if applicable)

        Returns:
            ValidationResult with validity, ROPS, and action
        """
        source_lower = source.lower()

        # Rule 1: Gong data bypasses ALL guardrails
        if source_lower == "gong" or source_lower == AssumptionSource.GONG.value:
            return ValidationResult(
                valid=True,
                source="gong",
                field_name=field_name,
                value=value,
                rops=None,
                action="accept",
                reason="Gong-sourced assumption — accepted without validation",
            )

        # Rule 2: Web/manual data must pass ROPS check
        rops = None
        if incentive_cost is not None and cost_assumption is not None:
            rops = self._calculate_rops(cost_assumption, incentive_cost)

            if not (self.ROPS_MIN <= rops <= self.ROPS_MAX):
                # Check if cost is unreasonable (exception)
                if self._is_cost_unreasonable(incentive_cost):
                    return ValidationResult(
                        valid=False,
                        source=source_lower,
                        field_name=field_name,
                        value=value,
                        rops=rops,
                        action="flag",
                        reason=f"ROPS {rops:.1f}x outside 10-30x range",
                        suggestion=f"Cost assumption ${incentive_cost:.2f} flagged as unreasonable for {self.industry} ({self.cost_max} max). Review assumption.",
                    )
                return ValidationResult(
                    valid=False,
                    source=source_lower,
                    field_name=field_name,
                    value=value,
                    rops=rops,
                    action="flag",
                    reason=f"ROPS {rops:.1f}x outside 10-30x guardrail",
                    suggestion=f"Adjust value or cost assumption. Target ROPS: 10-30x",
                )

            return ValidationResult(
                valid=True,
                source=source_lower,
                field_name=field_name,
                value=value,
                rops=rops,
                action="accept",
                reason=f"ROPS {rops:.1f}x within 10-30x range",
            )

        # If no ROPS calculation possible, accept
        return ValidationResult(
            valid=True,
            source=source_lower,
            field_name=field_name,
            value=value,
            action="accept",
            reason="No ROPS data available, accepting",
        )

    def validate_total_ebitda_accretion(
        self,
        total_accretion: float,
        last_annual_ebitda: float,
        assumption_sources: Dict[str, str],
    ) -> ValidationResult:
        """
        Validate total EBITDA accretion across all campaigns.

        Args:
            total_accretion: Total net EBITDA impact ($)
            last_annual_ebitda: Company's last annual EBITDA ($)
            assumption_sources: Dict of {"field_name": "gong|web|manual", ...}

        Returns:
            ValidationResult for total accretion
        """
        # Rule: If ALL assumptions are Gong-sourced, bypass accretion check
        gong_count = sum(
            1 for s in assumption_sources.values()
            if s.lower() in ("gong", AssumptionSource.GONG.value)
        )

        if gong_count == len(assumption_sources):
            accretion_pct = (total_accretion / last_annual_ebitda) * 100
            return ValidationResult(
                valid=True,
                source="gong",
                field_name="Total EBITDA Accretion",
                value=total_accretion,
                accretion_pct=accretion_pct,
                action="accept",
                reason="All assumptions Gong-sourced — accretion check bypassed",
            )

        # Otherwise, enforce 15% ceiling
        accretion_pct = (total_accretion / last_annual_ebitda) * 100

        if accretion_pct > self.EBITDA_ACCRETION_MAX_PCT:
            return ValidationResult(
                valid=False,
                source="mixed",
                field_name="Total EBITDA Accretion",
                value=total_accretion,
                accretion_pct=accretion_pct,
                action="flag",
                reason=f"Total accretion {accretion_pct:.1f}% exceeds 15% ceiling",
                suggestion=f"Reduce assumption values or campaign count. Max: ${last_annual_ebitda * 0.15:,.0f}",
            )

        return ValidationResult(
            valid=True,
            source="mixed",
            field_name="Total EBITDA Accretion",
            value=total_accretion,
            accretion_pct=accretion_pct,
            action="accept",
            reason=f"Total accretion {accretion_pct:.1f}% within 15% guardrail",
        )

    @staticmethod
    def _calculate_rops(revenue_impact: float, incentive_cost: float) -> float:
        """Calculate ROPS (Return on Promotion Spend)"""
        if incentive_cost <= 0:
            return 0
        return revenue_impact / incentive_cost

    def _is_cost_unreasonable(self, cost: float) -> bool:
        """Check if cost assumption is outside reasonable bounds"""
        return cost < self.COST_MIN or cost > self.cost_max


class AssumptionValidator:
    """High-level validator that processes batches of assumptions"""

    def __init__(self, industry: Literal["qsr", "manufacturing"] = "qsr"):
        self.guardrails = AssumptionGuardrails(industry)
        self.validation_log: List[ValidationResult] = []

    def validate_campaign_assumptions(
        self,
        campaign_name: str,
        assumptions: Dict[str, Dict],
        last_annual_ebitda: float,
    ) -> Dict:
        """
        Validate all assumptions for a campaign.

        Args:
            campaign_name: Name of the campaign (e.g., "Loyalty Rewards")
            assumptions: Dict of {
                "uplift_pct": {"value": 5, "source": "web", "incentive_cost": 0.25},
                ...
            }
            last_annual_ebitda: Company EBITDA for accretion calc

        Returns:
            {
                "campaign": str,
                "valid": bool,
                "results": [ValidationResult, ...],
                "total_accretion": float (if calculable),
                "accretion_pct": float (if calculable)
            }
        """
        results = []
        sources = {}

        for field, data in assumptions.items():
            value = data.get("value")
            source = data.get("source", "manual")
            cost = data.get("incentive_cost")

            # For ROPS: use incentive_cost as the cost basis
            result = self.guardrails.validate_assumption(
                field_name=f"{campaign_name}: {field}",
                value=value,
                source=source,
                cost_assumption=value if isinstance(value, (int, float)) else None,
                incentive_cost=cost,
            )
            results.append(result)
            sources[field] = source

        # Check if all validations passed
        all_valid = all(r.valid for r in results)

        return {
            "campaign": campaign_name,
            "valid": all_valid,
            "results": results,
            "sources": sources,
        }

    def format_validation_report(self, results: List[ValidationResult]) -> str:
        """Format validation results as a readable report"""
        report = []
        report.append("\n" + "=" * 70)
        report.append("ASSUMPTION VALIDATION REPORT")
        report.append("=" * 70)

        for result in results:
            status = "✓ ACCEPT" if result.valid else "⚠ FLAG"
            report.append(f"\n{status} | {result.field_name}")
            report.append(f"  Source: {result.source.upper()}")
            report.append(f"  Value: {result.value}")
            if result.rops is not None:
                report.append(f"  ROPS: {result.rops:.1f}x (target: 10-30x)")
            report.append(f"  {result.reason}")
            if result.suggestion:
                report.append(f"  → {result.suggestion}")

        report.append("\n" + "=" * 70)
        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    # QSR Example
    guardrails = AssumptionGuardrails(industry="qsr")

    # Test 1: Gong assumption (should pass)
    result = guardrails.validate_assumption(
        field_name="Campaign 1: Beverage Uplift %",
        value=5.0,
        source="gong",
        cost_assumption=5000,
        incentive_cost=0.25,
    )
    print(f"Gong assumption: {result.reason}")

    # Test 2: Web assumption with good ROPS
    result = guardrails.validate_assumption(
        field_name="Campaign 2: Food Uplift %",
        value=12.0,
        source="web",
        cost_assumption=12000,
        incentive_cost=0.50,
    )
    print(f"Web assumption (good ROPS): {result.reason}")

    # Test 3: Web assumption with bad ROPS
    result = guardrails.validate_assumption(
        field_name="Campaign 3: Retention %",
        value=2.0,
        source="web",
        cost_assumption=200,
        incentive_cost=50.0,
    )
    print(f"Web assumption (bad ROPS): {result.reason}")

    # Test 4: Total accretion check
    sources = {
        "uplift": "web",
        "retention": "web",
    }
    result = guardrails.validate_total_ebitda_accretion(
        total_accretion=1_200_000,  # $1.2M accretion
        last_annual_ebitda=10_000_000,  # $10M EBITDA
        assumption_sources=sources,
    )
    print(f"Total accretion: {result.reason}")
