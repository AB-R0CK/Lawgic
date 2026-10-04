from __future__ import annotations

import re
from collections.abc import Iterator

from src.models.schemas import CitationItem, RetrievedChunk
from src.services.llm.providers import get_llm_client
from src.services.retriever import LegalRetriever
from src.utils.jurisdiction import (
    detect_chunk_state,
    infer_state,
    is_central_reference,
)


# ============================================================
# CASUAL CHAT
# ============================================================

CASUAL_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "hii",
    "hiii",
    "hi there",
    "hello there",
    "hey there",
    "good morning",
    "good afternoon",
    "good evening",
    "whatsapp",
    "thanks",
    "thank you",
    "thx",
    "bye",
    "goodbye",
    "who are you",
    "what can you do",
}


def _is_casual_message(question: str) -> bool:
    normalized = (
        question
        .strip()
        .lower()
        .rstrip("!?,.")
    )

    return normalized in CASUAL_MESSAGES


def _casual_response(question: str) -> str:
    normalized = (
        question
        .strip()
        .lower()
    )

    if "morning" in normalized:
        return (
            "Good morning! 👋 "
            "I'm Lawgic. Upload and analyze a legal "
            "document, and I'll help you understand "
            "its clauses, risks, obligations, and "
            "important details."
        )

    if "afternoon" in normalized:
        return (
            "Good afternoon! 👋 "
            "I'm Lawgic. Upload a legal PDF whenever "
            "you're ready and we can go through it."
        )

    if "evening" in normalized:
        return (
            "Good evening! 👋 "
            "I'm Lawgic. Upload your legal document "
            "and ask me anything about it."
        )

    if normalized in {"thanks", "thank you", "thx"}:
        return "You're welcome! 😊"

    if normalized in {"bye", "goodbye"}:
        return "Goodbye! 👋"

    if normalized in {"who are you", "what can you do"}:
        return (
            "I'm Lawgic, your legal document assistant. "
            "Upload a PDF, analyze it, and ask me questions "
            "about its contents."
        )

    return (
        "Hello! 👋 I'm Lawgic, your legal document "
        "assistant. Upload and analyze a PDF, then "
        "ask me questions about the document."
    )


# ============================================================
# HELPERS
# ============================================================

def _safe_metadata_value(
    metadata: dict,
    keys: list[str],
    fallback: str,
) -> str:
    """
    Return the first non-empty metadata value.
    """

    for key in keys:
        value = metadata.get(key)

        if value is None:
            continue

        value = str(value).strip()

        if value:
            return value

    return fallback


# ============================================================
# RAG SERVICE
# ============================================================

class RAGService:

    def __init__(self) -> None:
        """
        Initialize the document retriever and LLM client.

        IMPORTANT:
        Use the current provider system:
            src.services.llm.providers
        """

        self.retriever = LegalRetriever()
        self.llm = get_llm_client()

    # ========================================================
    # PROMPT BUILDER
    # ========================================================

    @staticmethod
    def _build_prompt(
        *,
        question: str,
        clause_text: str | None,
        chunks: list[RetrievedChunk],
    ) -> str:

        context_parts: list[str] = []

        # ----------------------------------------------------
        # Uploaded document context
        # ----------------------------------------------------

        if clause_text:
            context_parts.append(
                "UPLOADED DOCUMENT CONTEXT:\n"
                f"{clause_text}"
            )

        # ----------------------------------------------------
        # Retrieved context
        # ----------------------------------------------------

        if chunks:

            retrieved_lines: list[str] = []

            for index, chunk in enumerate(
                chunks,
                start=1,
            ):

                metadata = chunk.metadata or {}

                document_name = (
                    metadata.get("document_name")
                    or "Unknown document"
                )

                section = (
                    metadata.get("section")
                    or metadata.get("clause")
                    or metadata.get("section_number")
                    or metadata.get("article")
                    or "Not found"
                )

                retrieved_lines.append(
                    "\n".join(
                        [
                            f"[Source {index}]",
                            f"Document: {document_name}",
                            f"Section/Clause: {section}",
                            f"Text: {chunk.text}",
                        ]
                    )
                )

            context_parts.append(
                "RETRIEVED LEGAL CONTEXT:\n"
                + "\n\n".join(retrieved_lines)
            )

        # ----------------------------------------------------
        # Final context
        # ----------------------------------------------------

        context = (
            "\n\n".join(context_parts)
            if context_parts
            else "No document context available."
        )

        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        return f"""
You are Lawgic, an AI legal-document assistant.

Your job is to answer the user's question using the
uploaded document and the retrieved legal context.

IMPORTANT RULES:

1. Focus on the currently uploaded document.

2. Do not invent facts.

3. Do not invent:
   - sections
   - clauses
   - dates
   - parties
   - citations
   - legal provisions

4. If something is not present in the supplied context,
   say:
   "Not found in provided context."

5. Clearly distinguish information found in the document
   from general legal explanation.

6. Do not present uncertain interpretations as facts.

7. Use simple and professional English.

8. Avoid unnecessary legal jargon.

9. Use headings and bullet points where useful.

10. When discussing a clause or provision, mention its
    section/clause number whenever available.

11. Answer the user's actual question directly.

12. Do not create information simply because the user
    expects an answer.

RESPONSE STRUCTURE:

1. Document Metadata

Include only information supported by the context:

- Document Type
- Document Title
- Parties Involved
- Effective Date
- Document Duration / Validity
- Governing Law / Jurisdiction
- Key Terms

2. Background Context

Briefly explain the relevant background from the
document.

3. Legal Issues, Statutes, Arguments, and Takeaways

Answer the user's question using the supplied context.

Where applicable:

- identify relevant clauses
- identify relevant dates
- identify obligations
- identify important legal provisions
- identify important events
- explain practical implications

4. Follow-up Questions

Provide 2-4 useful questions based specifically on
the current document.

Do not ask questions unrelated to the uploaded document.

DOCUMENT / RETRIEVAL CONTEXT:

{context}

USER QUESTION:

{question}

Remember:
Use the supplied document context as the primary source.
Do not invent missing information.
""".strip()

    # ========================================================
    # CITATIONS
    # ========================================================

    @staticmethod
    def _build_citations(
        chunks: list[RetrievedChunk],
        *,
        question: str,
        clause_text: str | None,
        document_name: str | None,
    ) -> list[CitationItem]:

        max_citations = min(
            10,
            len(chunks),
        )

        if max_citations <= 0:
            return []

        target_state = infer_state(
            f"{question}\n{clause_text or ''}"
        )

        citations: list[CitationItem] = []

        seen_keys: set[tuple[str, str]] = set()

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            if len(citations) >= max_citations:
                break

            metadata = chunk.metadata or {}

            chunk_document = metadata.get(
                "document_name"
            )

            # ------------------------------------------------
            # HARD DOCUMENT FILTER
            # ------------------------------------------------

            if document_name:

                if (
                    chunk_document
                    and str(chunk_document) != str(document_name)
                ):
                    continue

            # ------------------------------------------------
            # Jurisdiction information
            # ------------------------------------------------

            chunk_state = detect_chunk_state(
                metadata,
                chunk.text,
            )

            if (
                target_state
                and chunk_state
                and chunk_state != target_state
            ):
                continue

            # ------------------------------------------------
            # Citation name
            # ------------------------------------------------

            citation = _safe_metadata_value(
                metadata,
                [
                    "citation",
                    "act_name",
                    "title",
                    "source",
                    "document_name",
                ],
                document_name or f"Reference {index}",
            )

            # ------------------------------------------------
            # Section
            # ------------------------------------------------

            section = _safe_metadata_value(
                metadata,
                [
                    "section",
                    "section_number",
                    "article",
                    "clause",
                    "provision",
                ],
                "Not found",
            )

            # ------------------------------------------------
            # Reference type
            # ------------------------------------------------

            reference_type = _safe_metadata_value(
                metadata,
                [
                    "reference_type",
                    "doc_type",
                    "type",
                    "category",
                ],
                "legal_reference",
            )

            if document_name:
                reference_type = "uploaded_document"

            elif (
                target_state
                and chunk_state == target_state
            ):
                reference_type = (
                    f"{target_state}_state_act"
                )

            elif is_central_reference(
                metadata,
                chunk.text,
            ):
                reference_type = "central_act"

            # ------------------------------------------------
            # Actual document name
            # ------------------------------------------------

            actual_document_name = (
                str(chunk_document)
                if chunk_document
                else document_name
            )

            # ------------------------------------------------
            # Remove duplicate citations
            # ------------------------------------------------

            dedupe_key = (
                citation.strip().lower(),
                section.strip().lower(),
            )

            if dedupe_key in seen_keys:
                continue

            seen_keys.add(dedupe_key)

            # ------------------------------------------------
            # Add citation
            # ------------------------------------------------

            citations.append(
                CitationItem(
                    citation=citation,
                    section=section,
                    reference_type=reference_type,
                    score=chunk.score,
                    document_name=actual_document_name,
                )
            )

        return citations

    # ========================================================
    # RETRIEVAL QUERY
    # ========================================================

    @staticmethod
    def _build_retrieval_query(
        question: str,
        clause_text: str | None,
    ) -> str:

        retrieval_query = question.strip()

        # If jurisdiction is already present,
        # don't add another one.
        if infer_state(question):
            return retrieval_query

        derived_state = infer_state(
            clause_text or ""
        )

        if derived_state:
            retrieval_query = (
                f"{retrieval_query} "
                f"{derived_state}"
            )

        return retrieval_query

    # ========================================================
    # NORMAL ANSWER
    # ========================================================

    def answer(
        self,
        *,
        question: str,
        clause_text: str | None = None,
        top_k: int | None = None,
        document_name: str | None = None,
    ) -> tuple[
        str,
        list[RetrievedChunk],
        list[CitationItem],
    ]:

        # ----------------------------------------------------
        # Casual chat
        # ----------------------------------------------------

        if _is_casual_message(question):

            return (
                _casual_response(question),
                [],
                [],
            )

        # ----------------------------------------------------
        # Build retrieval query
        # ----------------------------------------------------

        retrieval_query = self._build_retrieval_query(
            question,
            clause_text,
        )

        # ----------------------------------------------------
        # Document-scoped retrieval
        # ----------------------------------------------------

        raw_chunks = self.retriever.query(
            retrieval_query,
            top_k=top_k,
            document_name=document_name,
        )

        chunks = [
            RetrievedChunk(
                text=item.text,
                metadata=item.metadata,
                score=item.score,
            )
            for item in raw_chunks
        ]

        # ----------------------------------------------------
        # Build prompt
        # ----------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            clause_text=clause_text,
            chunks=chunks,
        )

        # ----------------------------------------------------
        # Generate answer
        # ----------------------------------------------------

        answer = self.llm.generate(
            prompt
        )

        # ----------------------------------------------------
        # Build citations
        # ----------------------------------------------------

        citations = self._build_citations(
            chunks,
            question=question,
            clause_text=clause_text,
            document_name=document_name,
        )

        return (
            answer,
            chunks,
            citations,
        )

    # ========================================================
    # STREAMING ANSWER
    # ========================================================

    def answer_stream(
        self,
        *,
        question: str,
        clause_text: str | None = None,
        top_k: int | None = None,
        document_name: str | None = None,
    ) -> tuple[
        Iterator[str],
        list[RetrievedChunk],
        list[CitationItem],
    ]:

        # ----------------------------------------------------
        # Casual chat
        # ----------------------------------------------------

        if _is_casual_message(question):

            response = _casual_response(
                question
            )

            def casual_stream() -> Iterator[str]:
                yield response

            return (
                casual_stream(),
                [],
                [],
            )

        # ----------------------------------------------------
        # Build retrieval query
        # ----------------------------------------------------

        retrieval_query = self._build_retrieval_query(
            question,
            clause_text,
        )

        # ----------------------------------------------------
        # Document-scoped retrieval
        # ----------------------------------------------------

        raw_chunks = self.retriever.query(
            retrieval_query,
            top_k=top_k,
            document_name=document_name,
        )

        chunks = [
            RetrievedChunk(
                text=item.text,
                metadata=item.metadata,
                score=item.score,
            )
            for item in raw_chunks
        ]

        # ----------------------------------------------------
        # Build prompt
        # ----------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            clause_text=clause_text,
            chunks=chunks,
        )

        # ----------------------------------------------------
        # Stream answer
        # ----------------------------------------------------

        stream = self.llm.stream_generate(
            prompt
        )

        # ----------------------------------------------------
        # Build citations
        # ----------------------------------------------------

        citations = self._build_citations(
            chunks,
            question=question,
            clause_text=clause_text,
            document_name=document_name,
        )

        return (
            stream,
            chunks,
            citations,
        )


# ============================================================
# OPTIONAL SINGLETON
# ============================================================

_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """
    Return a cached RAGService instance.
    """

    global _rag_service

    if _rag_service is None:
        _rag_service = RAGService()

    return _rag_service