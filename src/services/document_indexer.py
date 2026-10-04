from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import chromadb

from src.core.config import settings


# ============================================================
# TEXT CHUNKING
# ============================================================

def _chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """
    Split long legal text into overlapping chunks.

    chunk_size and overlap are character-based.
    """

    if not text:
        return []

    text = str(text).strip()

    if not text:
        return []

    if chunk_size <= 0:
        return [text]

    if overlap < 0:
        overlap = 0

    if overlap >= chunk_size:
        overlap = max(
            0,
            chunk_size // 5,
        )

    chunks: list[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


# ============================================================
# CHROMA CLIENT
# ============================================================

def _get_chroma_client():
    """
    Create or return a persistent Chroma client.
    """

    db_path = Path(
        settings.vector_db_path
    )

    if not db_path.is_absolute():
        db_path = (
            Path.cwd()
            / db_path
        )

    db_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return chromadb.PersistentClient(
        path=str(db_path)
    )


# ============================================================
# COLLECTION
# ============================================================

def get_or_create_collection():
    """
    Get the configured Chroma collection.

    If it does not exist, create it.
    """

    client = _get_chroma_client()

    collection = (
        client.get_or_create_collection(
            name=settings.chroma_collection
        )
    )

    return collection


# ============================================================
# VALUE HELPERS
# ============================================================

def _get_value(
    item: Any,
    key: str,
    default: Any = None,
) -> Any:
    """
    Safely read a value from either:

    - dictionary
    - Pydantic model
    - normal Python object
    """

    if item is None:
        return default

    if isinstance(
        item,
        dict,
    ):
        return item.get(
            key,
            default,
        )

    return getattr(
        item,
        key,
        default,
    )


# ============================================================
# INDEX DOCUMENT
# ============================================================

def index_document(
    filename: str,
    clauses: list[Any],
) -> int:
    """
    Index an uploaded legal document into Chroma.

    Parameters
    ----------
    filename:
        Name of the uploaded PDF/document.

    clauses:
        List of clause strings or ClauseAnalysis objects.

    Returns
    -------
    int
        Number of chunks indexed.
    """

    if not clauses:
        return 0

    collection = (
        get_or_create_collection()
    )

    # Check if document already exists to skip re-indexing
    existing = collection.get(
        where={"document_name": filename},
        limit=1
    )
    if existing and existing.get("ids"):
        print(f"[Lawgic] Document {filename} already indexed, skipping")
        return len(existing["ids"])

    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    ids: list[str] = []

    # --------------------------------------------------------
    # Process every clause
    # --------------------------------------------------------

    for clause_index, clause in enumerate(
        clauses,
        start=1,
    ):

        # ----------------------------------------------------
        # Extract clause information
        # ----------------------------------------------------

        if isinstance(
            clause,
            str,
        ):

            clause_id = clause_index

            clause_text = clause

            clause_type = (
                "Legal Clause"
            )

        else:

            clause_id = _get_value(
                clause,
                "clause_id",
                clause_index,
            )

            clause_text = _get_value(
                clause,
                "clause_text",
                "",
            )

            clause_type = _get_value(
                clause,
                "clause_type",
                "Legal Clause",
            )

        clause_text = str(
            clause_text or ""
        ).strip()

        if not clause_text:
            continue

        # ----------------------------------------------------
        # Split large clauses
        # ----------------------------------------------------

        chunks = _chunk_text(
            clause_text,
            chunk_size=1200,
            overlap=200,
        )

        # ----------------------------------------------------
        # Store each chunk
        # ----------------------------------------------------

        for chunk_index, chunk in enumerate(
            chunks,
            start=1,
        ):

            if not chunk.strip():
                continue

            # Stable unique ID
            raw_id = (
                f"{filename}|"
                f"clause_{clause_id}|"
                f"chunk_{chunk_index}"
            )

            record_id = hashlib.sha256(
                raw_id.encode(
                    "utf-8"
                )
            ).hexdigest()

            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            metadata = {
                "filename": str(
                    filename
                ),

                "document_name": str(
                    filename
                ),

                "clause_id": int(
                    clause_id
                ),

                "section": (
                    f"Clause {clause_id}"
                ),

                "clause": (
                    f"Clause {clause_id}"
                ),

                "clause_type": str(
                    clause_type
                    or "Legal Clause"
                ),

                "chunk_index": int(
                    chunk_index
                ),

                "citation": str(
                    filename
                ),

                "source": str(
                    filename
                ),

                "reference_type": (
                    "uploaded_document"
                ),
            }

            documents.append(
                chunk
            )

            metadatas.append(
                metadata
            )

            ids.append(
                record_id
            )

    # --------------------------------------------------------
    # Nothing to index
    # --------------------------------------------------------

    if not documents:
        return 0

    # --------------------------------------------------------
    # Upsert into Chroma
    #
    # Upsert is important because the same PDF may be
    # uploaded again after code changes.
    # --------------------------------------------------------

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return len(documents)