from __future__ import annotations

import re

from src.models.schemas import (
    ClauseAnalysis,
    RiskAssessment,
)


# ============================================================
# INR / MONEY EXTRACTION
# ============================================================

def _extract_inr_amounts(text: str) -> list[float]:
    """
    Extract Indian Rupee amounts from legal text.

    Examples:
        ₹50,000
        Rs. 50000
        INR 1,50,000
        Rs 5 lakh
        ₹2 crore
    """

    if not text:
        return []

    amounts: list[float] = []

    # --------------------------------------------------------
    # Crore / Lakh amounts
    # --------------------------------------------------------

    unit_pattern = re.compile(
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,]+(?:\.\d+)?)\s*"
        r"(crore|crores|lakh|lakhs)",
        re.IGNORECASE,
    )

    for match in unit_pattern.finditer(text):
        number_text = match.group(1)
        unit = match.group(2).lower()

        try:
            number = float(
                number_text.replace(",", "")
            )

            if "crore" in unit:
                number *= 10_000_000

            elif "lakh" in unit:
                number *= 100_000

            amounts.append(number)

        except ValueError:
            continue

    # --------------------------------------------------------
    # Normal currency amounts
    # --------------------------------------------------------

    currency_pattern = re.compile(
        r"(?:₹|rs\.?|inr)\s*"
        r"([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    for match in currency_pattern.finditer(text):
        number_text = match.group(1)

        try:
            number = float(
                number_text.replace(",", "")
            )

            amounts.append(number)

        except ValueError:
            continue

    return amounts


# ============================================================
# KEYWORD HELPERS
# ============================================================

def _contains_any(
    text: str,
    keywords: list[str],
) -> bool:
    """
    Check whether any keyword exists in the text.
    """

    text_lower = text.lower()

    return any(
        keyword.lower() in text_lower
        for keyword in keywords
    )


def _matched_keywords(
    text: str,
    keywords: list[str],
) -> list[str]:
    """
    Return the keywords that were found.
    """

    text_lower = text.lower()

    return [
        keyword
        for keyword in keywords
        if keyword.lower() in text_lower
    ]


# ============================================================
# RISK ANALYSIS FOR A SINGLE CLAUSE
# ============================================================

def _risk_from_clause(
    analysis: ClauseAnalysis,
) -> tuple[str, list[str]]:
    """
    Determine the risk level and risk triggers for one clause.

    The result is:

        (risk_level, triggers)

    Risk levels:
        Low
        Medium
        High
    """

    text = (
        analysis.clause_text
        or ""
    ).strip()

    text_lower = text.lower()

    triggers: list[str] = []

    # --------------------------------------------------------
    # HIGH-RISK TERMS
    # --------------------------------------------------------

    high_risk_groups = {
        "Unlimited liability": [
            "unlimited liability",
            "without limitation",
            "without any limitation",
            "liable for all losses",
        ],

        "Broad indemnification": [
            "indemnify",
            "indemnification",
            "hold harmless",
        ],

        "Severe penalty": [
            "penalty",
            "liquidated damages",
            "punitive damages",
        ],

        "Automatic termination": [
            "immediate termination",
            "terminate immediately",
            "termination without notice",
        ],

        "Broad non-compete": [
            "non-compete",
            "non compete",
            "shall not compete",
        ],

        "Broad exclusivity": [
            "exclusive",
            "exclusively",
            "sole and exclusive",
        ],

        "Arbitration obligation": [
            "mandatory arbitration",
            "binding arbitration",
        ],
    }

    high_matches = 0

    for name, keywords in high_risk_groups.items():
        matches = _matched_keywords(
            text,
            keywords,
        )

        if matches:
            high_matches += len(matches)

            triggers.append(
                f"{name}: "
                + ", ".join(matches)
            )

    # --------------------------------------------------------
    # MEDIUM-RISK TERMS
    # --------------------------------------------------------

    medium_risk_groups = {
        "Termination clause": [
            "termination",
            "terminate",
            "terminated",
        ],

        "Confidentiality obligation": [
            "confidential",
            "confidentiality",
            "non-disclosure",
            "nondisclosure",
        ],

        "Liability provision": [
            "liability",
            "liable",
            "damages",
        ],

        "Indemnity provision": [
            "indemnity",
            "indemnify",
            "indemnification",
        ],

        "Dispute resolution": [
            "dispute",
            "arbitration",
            "mediation",
        ],

        "Intellectual property restriction": [
            "intellectual property",
            "copyright",
            "patent",
            "trademark",
            "ownership",
        ],

        "Payment obligation": [
            "payment",
            "payable",
            "fee",
            "fees",
            "interest",
        ],

        "Renewal obligation": [
            "renewal",
            "renew",
            "automatically renew",
        ],

        "Warranty obligation": [
            "warranty",
            "warranties",
            "warrants",
        ],

        "Notice requirement": [
            "notice",
            "written notice",
            "notice period",
        ],
    }

    medium_matches = 0

    for name, keywords in medium_risk_groups.items():
        matches = _matched_keywords(
            text,
            keywords,
        )

        if matches:
            medium_matches += len(matches)

            triggers.append(
                f"{name}: "
                + ", ".join(matches)
            )

    # --------------------------------------------------------
    # FINANCIAL RISK
    # --------------------------------------------------------

    amounts = _extract_inr_amounts(
        text
    )

    if amounts:
        maximum_amount = max(
            amounts
        )

        if maximum_amount >= 10_000_000:
            triggers.append(
                "High-value financial obligation "
                f"detected: ₹{maximum_amount:,.0f}"
            )

            high_matches += 1

        elif maximum_amount >= 1_000_000:
            triggers.append(
                "Significant financial obligation "
                f"detected: ₹{maximum_amount:,.0f}"
            )

            medium_matches += 1

    # --------------------------------------------------------
    # PERCENTAGE / INTEREST RISK
    # --------------------------------------------------------

    percentages = re.findall(
        r"\b\d+(?:\.\d+)?\s*%",
        text,
    )

    if percentages:
        for percentage in percentages:
            triggers.append(
                f"Percentage-based obligation: "
                f"{percentage}"
            )

        medium_matches += 1

    # --------------------------------------------------------
    # LONG-TERM OBLIGATION
    # --------------------------------------------------------

    long_term_patterns = [
        r"\b\d+\s+years?\b",
        r"\b\d+\s+months?\b",
        r"perpetual",
        r"indefinite",
        r"automatically renew",
    ]

    long_term_found = any(
        re.search(
            pattern,
            text_lower,
        )
        for pattern in long_term_patterns
    )

    if long_term_found:
        triggers.append(
            "Long-term or continuing obligation detected."
        )

        medium_matches += 1

    # --------------------------------------------------------
    # ONE-SIDED / BROAD WORDING
    # --------------------------------------------------------

    broad_terms = [
        "sole discretion",
        "absolute discretion",
        "at its discretion",
        "without prior notice",
        "at any time",
        "for any reason",
        "without cause",
        "unconditionally",
    ]

    broad_matches = _matched_keywords(
        text,
        broad_terms,
    )

    if broad_matches:
        triggers.append(
            "Broad or unilateral wording: "
            + ", ".join(
                broad_matches
            )
        )

        medium_matches += len(
            broad_matches
        )

    # --------------------------------------------------------
    # FINAL RISK LEVEL
    # --------------------------------------------------------

    if high_matches >= 1:
        risk_level = "High"

    elif medium_matches >= 2:
        risk_level = "Medium"

    elif medium_matches == 1:
        risk_level = "Medium"

    else:
        risk_level = "Low"

    # --------------------------------------------------------
    # LOW-RISK INFORMATION
    # --------------------------------------------------------

    if not triggers:
        triggers.append(
            "No major predefined risk trigger detected."
        )

    return (
        risk_level,
        triggers,
    )


# ============================================================
# RISK DETECTION FOR ALL CLAUSES
# ============================================================

def detect_risks(
    analyses: list[ClauseAnalysis],
) -> list[RiskAssessment]:
    """
    Analyze all detected clauses and return
    RiskAssessment objects.
    """

    results: list[RiskAssessment] = []

    for analysis in analyses:
        risk_level, triggers = (
            _risk_from_clause(
                analysis
            )
        )

        results.append(
            RiskAssessment(
                clause_id=analysis.clause_id,
                clause_text=analysis.clause_text,
                clause_type=analysis.clause_type,
                risk_level=risk_level,
                triggers=triggers,
            )
        )

    return results


# ============================================================
# RISK ENGINE CLASS
# ============================================================

class RiskEngine:
    """
    Compatibility class for LegalAssistantService.

    The original project exposes detect_risks(),
    while LegalAssistantService expects a RiskEngine class.

    This class supports both approaches.
    """

    def assess(
        self,
        clause_text: str,
        clause_id: int = 0,
        clause_type: str = "General Legal Clause",
    ) -> dict:
        """
        Assess a single clause.
        """

        if not clause_text:
            return {
                "risk_level": "Low",
                "triggers": [],
            }

        analysis = ClauseAnalysis(
            clause_id=clause_id,
            clause_text=clause_text,
            clause_type=clause_type,
            entities=[],
            confidence=None,
        )

        results = detect_risks(
            [analysis]
        )

        if not results:
            return {
                "risk_level": "Low",
                "triggers": [],
            }

        result = results[0]

        return {
            "risk_level": result.risk_level,
            "triggers": result.triggers,
        }

    def analyze(
        self,
        clause_text: str,
        clause_id: int = 0,
        clause_type: str = "General Legal Clause",
    ) -> dict:
        """
        Alias for assess().
        """

        return self.assess(
            clause_text=clause_text,
            clause_id=clause_id,
            clause_type=clause_type,
        )

    def assess_clause(
        self,
        clause_text: str,
        clause_id: int = 0,
        clause_type: str = "General Legal Clause",
    ) -> dict:
        """
        Alias for assess().
        """

        return self.assess(
            clause_text=clause_text,
            clause_id=clause_id,
            clause_type=clause_type,
        )

    def detect_risks(
        self,
        analyses: list[ClauseAnalysis],
    ) -> list[RiskAssessment]:
        """
        Class-based access to the original
        detect_risks() function.
        """

        return detect_risks(
            analyses
        )


# ============================================================
# SINGLETON
# ============================================================

_risk_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    """
    Return a shared RiskEngine instance.
    """

    global _risk_engine

    if _risk_engine is None:
        _risk_engine = RiskEngine()

    return _risk_engine