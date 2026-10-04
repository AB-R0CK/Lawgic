from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================
# DOCUMENT METADATA
# ============================================================

class DocumentMetadata(BaseModel):
    """
    Metadata extracted from an uploaded legal document.
    """

    document_type: str = "Legal Document"

    document_title: str = "Untitled Document"

    parties_involved: list[str] = Field(
        default_factory=list
    )

    # These fields are optional because a document may not
    # contain an identifiable date or duration.
    effective_date: str | None = None

    duration_validity: str | None = None

    governing_law_jurisdiction: str | None = None

    key_terms: list[str] = Field(
        default_factory=list
    )

    filename: str | None = None


# ============================================================
# RETRIEVED CHUNK
# ============================================================

class RetrievedChunk(BaseModel):
    text: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    score: float | None = None


# ============================================================
# CITATION
# ============================================================

class CitationItem(BaseModel):
    citation: str

    section: str

    reference_type: str = "legal_reference"

    score: float | None = None

    document_name: str | None = None


# ============================================================
# CLAUSE ANALYSIS
# ============================================================

class ClauseAnalysis(BaseModel):
    clause_id: int

    clause_text: str

    clause_type: str

    entities: list[dict[str, Any]] = Field(
        default_factory=list
    )

    confidence: float | None = None


# ============================================================
# RISK ASSESSMENT
# ============================================================

class RiskAssessment(BaseModel):
    clause_id: int

    clause_text: str

    clause_type: str

    risk_level: str

    triggers: list[str] = Field(
        default_factory=list
    )


# ============================================================
# UPLOAD RESPONSE
# ============================================================

class UploadResponse(BaseModel):
    filename: str

    total_clauses: int

    summary: str

    document_metadata: DocumentMetadata

    document_citations: list[CitationItem] = Field(
        default_factory=list
    )

    clauses: list[ClauseAnalysis] = Field(
        default_factory=list
    )

    risks: list[RiskAssessment] = Field(
        default_factory=list
    )


# ============================================================
# ASK REQUEST
# ============================================================

class AskRequest(BaseModel):
    question: str

    clause_text: str | None = None

    top_k: int | None = 5

    document_name: str | None = None


# ============================================================
# ASK RESPONSE
# ============================================================

class AskResponse(BaseModel):
    question: str

    answer: str

    retrieved_context: list[RetrievedChunk] = Field(
        default_factory=list
    )

    citations: list[CitationItem] = Field(
        default_factory=list
    )


# ============================================================
# HEALTH RESPONSE
# ============================================================

class HealthResponse(BaseModel):
    status: str