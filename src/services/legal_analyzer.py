from __future__ import annotations

import re
from typing import Any

from src.models.schemas import ClauseAnalysis
from src.core.config import get_settings


# ============================================================
# Entity extraction
# ============================================================

def _extract_entities(clause_text: str) -> list[dict]:
    """
    Extract basic legal entities from a clause.

    This intentionally uses lightweight pattern matching so that
    document analysis can work even when the optional legal model
    is unavailable.
    """

    entities: list[dict] = []

    if not clause_text:
        return entities

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b",
    ]

    for pattern in date_patterns:
        for match in re.finditer(
            pattern,
            clause_text,
            re.IGNORECASE,
        ):
            entities.append(
                {
                    "text": match.group(0),
                    "label": "DATE",
                }
            )

    # --------------------------------------------------------
    # Money
    # --------------------------------------------------------

    money_pattern = (
        r"(?:₹|Rs\.?|INR|USD|\$|€|£)\s*"
        r"[\d,]+(?:\.\d+)?"
        r"(?:\s*(?:crore|lakh|million|billion))?"
    )

    for match in re.finditer(
        money_pattern,
        clause_text,
        re.IGNORECASE,
    ):
        entities.append(
            {
                "text": match.group(0),
                "label": "MONEY",
            }
        )

    # --------------------------------------------------------
    # Percentages
    # --------------------------------------------------------

    percentage_pattern = r"\b\d+(?:\.\d+)?\s*%"

    for match in re.finditer(
        percentage_pattern,
        clause_text,
    ):
        entities.append(
            {
                "text": match.group(0),
                "label": "PERCENT",
            }
        )

    # --------------------------------------------------------
    # Durations
    # --------------------------------------------------------

    duration_pattern = (
        r"\b\d+(?:\.\d+)?\s+"
        r"(?:days?|weeks?|months?|years?)\b"
    )

    for match in re.finditer(
        duration_pattern,
        clause_text,
        re.IGNORECASE,
    ):
        entities.append(
            {
                "text": match.group(0),
                "label": "DURATION",
            }
        )

    # --------------------------------------------------------
    # Legal acts / statutes
    # --------------------------------------------------------

    act_pattern = (
        r"\b(?:Indian Penal Code|IPC|"
        r"Code of Criminal Procedure|CrPC|"
        r"Code of Civil Procedure|CPC|"
        r"Indian Contract Act|"
        r"Companies Act|"
        r"Information Technology Act|"
        r"Arbitration and Conciliation Act|"
        r"Consumer Protection Act|"
        r"Transfer of Property Act|"
        r"Negotiable Instruments Act|"
        r"Constitution of India)\b"
    )

    for match in re.finditer(
        act_pattern,
        clause_text,
        re.IGNORECASE,
    ):
        entities.append(
            {
                "text": match.group(0),
                "label": "LAW",
            }
        )

    # --------------------------------------------------------
    # Sections
    # --------------------------------------------------------

    section_pattern = (
        r"\bsection\s+"
        r"\d+[A-Za-z]?"
        r"(?:\(\d+\))?"
        r"(?:\([a-z]\))?"
    )

    for match in re.finditer(
        section_pattern,
        clause_text,
        re.IGNORECASE,
    ):
        entities.append(
            {
                "text": match.group(0),
                "label": "SECTION",
            }
        )

    # --------------------------------------------------------
    # Remove duplicate entities
    # --------------------------------------------------------

    unique_entities: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for entity in entities:
        key = (
            entity["text"].lower(),
            entity["label"],
        )

        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)

    return unique_entities


# ============================================================
# Legal clause classifier
# ============================================================

class LegalClauseAnalyzer:
    """
    Performs legal clause classification.

    The class name is intentionally kept compatible with the
    existing Lawgic project.
    """

    def __init__(self) -> None:
        self.settings = get_settings()

        self.model = None
        self.tokenizer = None

        # Skip ML model loading for faster document processing
        # Rule-based classifier will be used instead
        print("[Lawgic] Using rule-based legal classification (fast mode)")

    # --------------------------------------------------------
    # Optional ML model
    # --------------------------------------------------------

    def _load_classifier(self) -> None:
        """
        Try to load the configured legal model.

        The application does not fail if the model cannot be
        loaded. In that case, the rule-based classifier below
        is used.
        """

        try:
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            model_name = (
                self.settings.legal_model_local_path
                or self.settings.legal_model_name
            )

            self.tokenizer = (
                AutoTokenizer.from_pretrained(
                    model_name
                )
            )

            self.model = (
                AutoModelForSequenceClassification
                .from_pretrained(
                    model_name
                )
            )

            self.model.eval()

        except Exception as exc:
            print(
                "[Lawgic] Legal model could not be loaded. "
                f"Using rule-based classification. Reason: {exc}"
            )

            self.model = None
            self.tokenizer = None

    # --------------------------------------------------------
    # Rule-based classifier
    # --------------------------------------------------------

    @staticmethod
    def _heuristic_label(
        clause_text: str,
    ) -> tuple[str, float]:
        """
        Classify a legal clause using keywords.
        """

        text = clause_text.lower()

        categories: dict[str, list[str]] = {
            "Confidentiality": [
                "confidential",
                "confidentiality",
                "non-disclosure",
                "nondisclosure",
                "secret information",
                "proprietary information",
            ],

            "Termination": [
                "termination",
                "terminate",
                "terminated",
                "termination for cause",
                "termination for convenience",
            ],

            "Payment": [
                "payment",
                "payable",
                "invoice",
                "fee",
                "fees",
                "salary",
                "compensation",
                "consideration",
                "rent",
            ],

            "Liability": [
                "liability",
                "liable",
                "limitation of liability",
                "loss or damage",
                "damages",
            ],

            "Indemnity": [
                "indemnify",
                "indemnification",
                "indemnity",
            ],

            "Intellectual Property": [
                "intellectual property",
                "copyright",
                "trademark",
                "patent",
                "ownership",
                "proprietary rights",
            ],

            "Dispute Resolution": [
                "dispute",
                "disputes",
                "dispute resolution",
                "arbitration",
                "mediation",
            ],

            "Governing Law": [
                "governing law",
                "governed by the laws",
                "laws of",
                "jurisdiction",
            ],

            "Force Majeure": [
                "force majeure",
                "act of god",
                "natural disaster",
                "earthquake",
                "flood",
                "war",
            ],

            "Warranty": [
                "warranty",
                "warranties",
                "warrants",
                "representation",
                "representations",
            ],

            "Privacy / Data Protection": [
                "personal data",
                "personal information",
                "data protection",
                "privacy",
                "data processing",
                "sensitive information",
            ],

            "Non-Compete": [
                "non-compete",
                "non compete",
                "competition",
                "compete",
            ],

            "Non-Solicitation": [
                "non-solicitation",
                "non solicitation",
                "solicit",
                "solicitation",
            ],

            "Notice": [
                "notice",
                "written notice",
                "notice period",
            ],

            "Renewal": [
                "renewal",
                "renew",
                "automatically renew",
            ],

            "Compliance": [
                "compliance",
                "comply with",
                "applicable law",
                "applicable laws",
                "regulatory",
            ],

            "Definitions": [
                "means",
                "shall mean",
                "definition",
                "defined as",
            ],
        }

        best_label = "General Legal Clause"
        best_score = 0

        for label, keywords in categories.items():
            score = 0

            for keyword in keywords:
                if keyword in text:
                    score += 1

            if score > best_score:
                best_score = score
                best_label = label

        if best_score == 0:
            confidence = 0.40
        elif best_score == 1:
            confidence = 0.65
        elif best_score == 2:
            confidence = 0.80
        else:
            confidence = 0.90

        return best_label, confidence

    # --------------------------------------------------------
    # ML prediction
    # --------------------------------------------------------

    def _predict_with_model(
        self,
        clause_text: str,
    ) -> tuple[str, float] | None:
        """
        Attempt prediction with the configured transformer model.

        If the model does not provide usable label mappings,
        return None and let the heuristic classifier handle it.
        """

        if (
            self.model is None
            or self.tokenizer is None
        ):
            return None

        try:
            import torch

            inputs = self.tokenizer(
                clause_text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )

            with torch.no_grad():
                outputs = self.model(
                    **inputs
                )

            probabilities = torch.softmax(
                outputs.logits,
                dim=-1,
            )

            confidence, index = torch.max(
                probabilities,
                dim=-1,
            )

            label_index = int(
                index.item()
            )

            confidence_value = float(
                confidence.item()
            )

            id2label = getattr(
                self.model.config,
                "id2label",
                {},
            )

            label = id2label.get(
                label_index,
                f"LABEL_{label_index}",
            )

            return (
                str(label),
                confidence_value,
            )

        except Exception as exc:
            print(
                "[Lawgic] Legal model prediction failed: "
                f"{exc}"
            )

            return None

    # --------------------------------------------------------
    # Single clause analysis
    # --------------------------------------------------------

    def analyze_single_clause(
        self,
        clause_text: str,
    ) -> ClauseAnalysis:
        """
        Analyze one clause.
        """

        label_and_confidence = (
            self._predict_with_model(
                clause_text
            )
        )

        if label_and_confidence is None:
            label_and_confidence = (
                self._heuristic_label(
                    clause_text
                )
            )

        label, confidence = (
            label_and_confidence
        )

        entities = _extract_entities(
            clause_text
        )

        return ClauseAnalysis(
            clause_id=0,
            clause_text=clause_text,
            clause_type=label,
            entities=entities,
            confidence=confidence,
        )

    # --------------------------------------------------------
    # Analyze all clauses
    # --------------------------------------------------------

    def analyze_clauses(
        self,
        clauses: list[str],
    ) -> list[ClauseAnalysis]:
        """
        Analyze a list of clauses.
        """

        results: list[ClauseAnalysis] = []

        for index, clause_text in enumerate(
            clauses,
            start=1,
        ):
            if not clause_text:
                continue

            clause_text = str(
                clause_text
            ).strip()

            if not clause_text:
                continue

            result = self.analyze_single_clause(
                clause_text
            )

            result.clause_id = index

            results.append(
                result
            )

        return results


# ============================================================
# Backward-compatible alias
# ============================================================

# Your new LegalAssistantService expects LegalAnalyzer.
# Your existing project uses LegalClauseAnalyzer.
#
# Both names now refer to the same implementation.

LegalAnalyzer = LegalClauseAnalyzer


# ============================================================
# Singleton
# ============================================================

_legal_analyzer: LegalClauseAnalyzer | None = None


def get_legal_analyzer() -> LegalClauseAnalyzer:
    """
    Return the shared legal analyzer instance.
    """

    global _legal_analyzer

    if _legal_analyzer is None:
        _legal_analyzer = LegalClauseAnalyzer()

    return _legal_analyzer