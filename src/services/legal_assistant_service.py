from __future__ import annotations

from typing import Any

from src.services.clause_segmenter import ClauseSegmenter
from src.services.legal_analyzer import LegalAnalyzer
from src.services.risk_engine import RiskEngine
from src.services.document_indexer import index_document


class LegalAssistantService:
    """
    Main service for Lawgic.

    Document flow:

        PDF
        ↓
        Clause Segmentation
        ↓
        Legal Analysis
        ↓
        Chroma Indexing
        ↓
        Risk Analysis
        ↓
        Metadata Extraction
        ↓
        Frontend

    Chat flow:

        User Question
        ↓
        RAG Service
        ↓
        Relevant Document Chunks
        ↓
        AI Answer
        ↓
        Citations
    """

    def __init__(self) -> None:

        # =====================================================
        # CLAUSE SEGMENTER
        # =====================================================

        self.clause_segmenter = ClauseSegmenter()

        # =====================================================
        # LEGAL ANALYZER
        # =====================================================

        self.legal_analyzer = LegalAnalyzer()

        # =====================================================
        # RISK ENGINE
        # =====================================================

        self.risk_engine = RiskEngine()

        # =====================================================
        # DOCUMENT METADATA
        # =====================================================

        self.document_metadata = None

        try:

            from src.services.document_metadata import (
                DocumentMetadataExtractor
            )

            self.document_metadata = (
                DocumentMetadataExtractor()
            )

        except Exception as exc:

            print(
                "[Lawgic] Metadata service initialization warning:",
                exc
            )

    # =========================================================
    # PROCESS DOCUMENT
    # =========================================================

    def process_document(
        self,
        text: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Process an uploaded legal document.
        """

        if not text or not text.strip():

            raise ValueError(
                "The uploaded document contains no readable text."
            )

        text = text.strip()

        filename = (
            filename
            or "Uploaded Document"
        )

        print(
            f"[Lawgic] Processing document: {filename}"
        )

        # =====================================================
        # STEP 1 - CLAUSE SEGMENTATION
        # =====================================================

        print(
            "[Lawgic] Step 1: Segmenting document..."
        )

        try:

            clauses = (
                self.clause_segmenter.segment(
                    text
                )
            )

        except Exception as exc:

            print(
                "[Lawgic] Clause segmentation failed:",
                exc
            )

            clauses = []

        # Fallback
        if not clauses:

            clauses = [
                text
            ]

        clauses = [
            str(clause).strip()
            for clause in clauses
            if clause
            and str(clause).strip()
        ]

        print(
            f"[Lawgic] Found {len(clauses)} clauses."
        )

        # =====================================================
        # STEP 2 - LEGAL CLAUSE ANALYSIS
        # =====================================================

        print(
            "[Lawgic] Step 2: Analyzing clauses..."
        )

        try:

            clause_analyses = (
                self.legal_analyzer.analyze_clauses(
                    clauses
                )
            )

        except Exception as exc:

            print(
                "[Lawgic] Legal analysis failed:",
                exc
            )

            raise

        # Ensure clause IDs
        for index, analysis in enumerate(
            clause_analyses,
            start=1
        ):

            try:

                analysis.clause_id = index

            except Exception:

                pass

        print(
            "[Lawgic] Clause analysis completed."
        )

        # =====================================================
        # STEP 3 - INDEX DOCUMENT
        # =====================================================

        print(
            "[Lawgic] Step 3: Indexing document..."
        )

        try:

            indexed_count = index_document(
                filename=filename,
                clauses=clauses,
            )

            print(
                f"[Lawgic] Indexed {indexed_count} chunks."
            )

        except Exception as exc:

            # Indexing failure should not prevent the
            # document analysis result from being returned.
            print(
                "[Lawgic] Document indexing warning:",
                exc
            )

        # =====================================================
        # STEP 4 - RISK ANALYSIS
        # =====================================================

        print(
            "[Lawgic] Step 4: Detecting risks..."
        )

        try:

            risks = (
                self.risk_engine.detect_risks(
                    clause_analyses
                )
            )

        except Exception as exc:

            print(
                "[Lawgic] Risk analysis failed:",
                exc
            )

            risks = []

        print(
            f"[Lawgic] Risk analysis completed. "
            f"{len(risks)} assessments."
        )

        # =====================================================
        # STEP 5 - METADATA
        # =====================================================

        print(
            "[Lawgic] Step 5: Extracting metadata..."
        )

        document_metadata = (
            self._extract_metadata(
                text=text,
                filename=filename,
            )
        )

        # =====================================================
        # STEP 6 - CITATIONS
        # =====================================================

        document_citations = (
            self._build_document_citations(
                filename=filename,
                analyses=clause_analyses,
            )
        )

        # =====================================================
        # STEP 7 - SUMMARY
        # =====================================================

        summary = (
            self._build_document_summary(
                clause_analyses,
                risks,
            )
        )

        # =====================================================
        # FINAL RESPONSE
        # =====================================================

        result = {

            "filename": filename,

            "total_clauses": len(
                clause_analyses
            ),

            "summary": summary,

            "document_metadata": (
                document_metadata
            ),

            "document_citations": (
                document_citations
            ),

            "clauses": clause_analyses,

            "risks": risks,
        }

        print(
            "[Lawgic] Document processing completed."
        )

        return result

    # =========================================================
    # METADATA
    # =========================================================

    def _extract_metadata(
        self,
        text: str,
        filename: str,
    ) -> dict[str, Any]:

        default_metadata = {

            "document_type":
                "Legal Document",

            "document_title":
                (
                    filename.rsplit(
                        ".",
                        1
                    )[0]
                    if filename
                    else "Legal Document"
                ),

            "parties_involved": [],

            "effective_date": None,

            "duration_validity": None,

            "governing_law_jurisdiction":
                None,

            "key_terms": [],

            "filename": filename,
        }

        if self.document_metadata is None:

            return default_metadata

        service = (
            self.document_metadata
        )

        # -----------------------------------------------------
        # extract_metadata()
        # -----------------------------------------------------

        if hasattr(
            service,
            "extract_metadata"
        ):

            try:

                metadata = (
                    service.extract_metadata(
                        text=text,
                        filename=filename,
                    )
                )

                return self._normalize_metadata(
                    metadata,
                    default_metadata,
                )

            except TypeError:

                try:

                    metadata = (
                        service.extract_metadata(
                            text,
                            filename,
                        )
                    )

                    return self._normalize_metadata(
                        metadata,
                        default_metadata,
                    )

                except Exception as exc:

                    print(
                        "[Lawgic] Metadata warning:",
                        exc
                    )

            except Exception as exc:

                print(
                    "[Lawgic] Metadata warning:",
                    exc
                )

        # -----------------------------------------------------
        # get_metadata()
        # -----------------------------------------------------

        if hasattr(
            service,
            "get_metadata"
        ):

            try:

                metadata = (
                    service.get_metadata(
                        text=text,
                        filename=filename,
                    )
                )

                return self._normalize_metadata(
                    metadata,
                    default_metadata,
                )

            except Exception as exc:

                print(
                    "[Lawgic] Metadata warning:",
                    exc
                )

        return default_metadata

    # =========================================================
    # NORMALIZE METADATA
    # =========================================================

    @staticmethod
    def _normalize_metadata(
        metadata: Any,
        default_metadata: dict[str, Any],
    ) -> dict[str, Any]:

        if metadata is None:

            return default_metadata

        # Pydantic model
        if hasattr(
            metadata,
            "model_dump"
        ):

            try:

                metadata = (
                    metadata.model_dump()
                )

            except Exception:

                pass

        # Older Pydantic
        elif hasattr(
            metadata,
            "dict"
        ):

            try:

                metadata = (
                    metadata.dict()
                )

            except Exception:

                pass

        # Normal object
        if not isinstance(
            metadata,
            dict
        ):

            result: dict[str, Any] = {}

            for key in default_metadata:

                if hasattr(
                    metadata,
                    key
                ):

                    result[key] = getattr(
                        metadata,
                        key
                    )

            metadata = result

        result = dict(
            default_metadata
        )

        result.update(
            metadata
        )

        return result

    # =========================================================
    # CITATIONS
    # =========================================================

    def _build_document_citations(
        self,
        filename: str,
        analyses: list[Any],
    ) -> list[dict[str, Any]]:

        citations = []

        for index, analysis in enumerate(
            analyses,
            start=1
        ):

            clause_id = getattr(
                analysis,
                "clause_id",
                index
            )

            citations.append(
                {
                    "citation": filename,

                    "section":
                        f"Clause {clause_id}",

                    "reference_type":
                        "document_clause",

                    "score": None,

                    "document_name":
                        filename,
                }
            )

        return citations

    # =========================================================
    # SUMMARY
    # =========================================================

    def _build_document_summary(
        self,
        clause_analyses: list[Any],
        risks: list[Any],
    ) -> str:

        total_clauses = len(
            clause_analyses
        )

        high_risk = 0
        medium_risk = 0
        low_risk = 0

        # -----------------------------------------------------
        # Count risks
        # -----------------------------------------------------

        for risk in risks:

            level = str(
                getattr(
                    risk,
                    "risk_level",
                    "Low"
                )
            ).lower()

            if level == "high":

                high_risk += 1

            elif level == "medium":

                medium_risk += 1

            else:

                low_risk += 1

        # -----------------------------------------------------
        # Clause categories
        # -----------------------------------------------------

        clause_types = {}

        for clause in clause_analyses:

            clause_type = getattr(
                clause,
                "clause_type",
                None
            )

            clause_type = (
                clause_type
                or "General Legal Clause"
            )

            clause_types[
                clause_type
            ] = (
                clause_types.get(
                    clause_type,
                    0
                )
                + 1
            )

        if clause_types:

            category_text = ", ".join(
                f"{name}: {count}"
                for name, count
                in clause_types.items()
            )

        else:

            category_text = (
                "General Legal Clauses"
            )

        return (
            f"The document contains "
            f"{total_clauses} analyzed legal clauses. "
            f"Risk distribution: "
            f"{high_risk} high, "
            f"{medium_risk} medium, and "
            f"{low_risk} low-risk clauses. "
            f"Clause categories identified: "
            f"{category_text}."
        )

    # =========================================================
    # NORMAL AI QUESTION
    # =========================================================

    def answer_question(
        self,
        request,
    ):
        """
        Answer a normal legal question using RAG.
        """

        from src.services.rag_service import RAGService

        rag_service = RAGService()

        question = getattr(
            request,
            "question",
            "",
        )

        clause_text = getattr(
            request,
            "clause_text",
            None,
        )

        top_k = getattr(
            request,
            "top_k",
            5,
        )

        document_name = getattr(
            request,
            "document_name",
            None,
        )

        return rag_service.answer(
            question=question,
            clause_text=clause_text,
            top_k=top_k,
            document_name=document_name,
        )

    # =========================================================
    # STREAMING AI QUESTION
    # =========================================================

    def answer_question_stream(
        self,
        request,
    ):
        """
        Stream an AI answer using the RAG service.

        Returns:

            stream
            retrieved chunks
            citations
        """

        from src.services.rag_service import RAGService

        rag_service = RAGService()

        question = getattr(
            request,
            "question",
            "",
        )

        clause_text = getattr(
            request,
            "clause_text",
            None,
        )

        top_k = getattr(
            request,
            "top_k",
            5,
        )

        document_name = getattr(
            request,
            "document_name",
            None,
        )

        return rag_service.answer_stream(
            question=question,
            clause_text=clause_text,
            top_k=top_k,
            document_name=document_name,
        )

    # =========================================================
    # ALIAS
    # =========================================================

    def analyze_document(
        self,
        text: str,
        filename: str | None = None,
    ) -> dict[str, Any]:

        return self.process_document(
            text=text,
            filename=filename,
        )


# =============================================================
# SINGLETON
# =============================================================

_legal_assistant_service = None


def get_legal_assistant_service() -> LegalAssistantService:

    global _legal_assistant_service

    if _legal_assistant_service is None:

        _legal_assistant_service = (
            LegalAssistantService()
        )

    return _legal_assistant_service