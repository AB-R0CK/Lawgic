from __future__ import annotations

from dataclasses import dataclass

import chromadb
from sentence_transformers import SentenceTransformer

from src.core.config import get_settings
from src.utils.hf_paths import resolve_hf_model_path


QUERY_PREFIX = "search_query: "
DOCUMENT_PREFIX = "search_document: "


@dataclass
class RetrievedResult:
    text: str
    metadata: dict
    score: float | None = None


class LegalRetriever:

    def __init__(self) -> None:

        settings = get_settings()

        self.settings = settings

        self.client = chromadb.PersistentClient(
            path=str(
                settings.vector_db_path
            )
        )

        collections = self.client.list_collections()

        if not collections:
            raise ValueError(
                "No Chroma collections found in "
                f"{settings.vector_db_path}. "
                "Add data or set CHROMA_COLLECTION correctly."
            )

        try:
            self.collection = (
                self.client.get_collection(
                    name=settings.chroma_collection
                )
            )

        except Exception:

            # Fall back to the first collection if
            # configured collection is unavailable.
            self.collection = (
                self.client.get_collection(
                    name=collections[0].name
                    if hasattr(
                        collections[0],
                        "name",
                    )
                    else str(collections[0])
                )
            )

        # Lazy load embedding model to speed up startup
        self.embedding_model = None

    # =========================================================
    # EMBEDDING
    # =========================================================

    def _get_embedding_model(self):
        """Lazy load embedding model only when needed"""
        if self.embedding_model is None:
            model_source = (
                self.settings.embedding_model_local_path
                or self.settings.embedding_model_name
            )
            print("[Lawgic] Loading embedding model...")
            self.embedding_model = SentenceTransformer(
                resolve_hf_model_path(model_source)
            )
            print("[Lawgic] Embedding model loaded")
        return self.embedding_model

    def _embed_query(
        self,
        query: str,
    ):
        model = self._get_embedding_model()
        return model.encode(
            f"{QUERY_PREFIX}{query}",
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()

    # =========================================================
    # QUERY
    # =========================================================

    def query(
        self,
        query: str,
        top_k: int | None = None,
        document_name: str | None = None,
    ) -> list[RetrievedResult]:

        k = (
            top_k
            or self.settings.retrieval_top_k
            if hasattr(
                self.settings,
                "retrieval_top_k",
            )
            else top_k or 5
        )

        embedding = self._embed_query(
            query
        )

        # -----------------------------------------------------
        # DOCUMENT FILTER
        # -----------------------------------------------------
        #
        # When document_name is supplied, Chroma is forced to
        # search only chunks belonging to that uploaded PDF.
        #
        # This is the important document-scoping fix.
        # -----------------------------------------------------

        where = None

        if document_name:
            where = {
                "document_name": document_name
            }

        result = self.collection.query(
            query_embeddings=[
                embedding
            ],
            n_results=k,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        documents = (
            result.get("documents", [[]])[0]
        )

        metadatas = (
            result.get("metadatas", [[]])[0]
        )

        distances = (
            result.get("distances", [[]])[0]
        )

        retrieved: list[
            RetrievedResult
        ] = []

        for index, document in enumerate(
            documents
        ):

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            score = None

            if distance is not None:
                try:
                    score = 1.0 / (
                        1.0 + float(distance)
                    )
                except Exception:
                    score = None

            retrieved.append(
                RetrievedResult(
                    text=document,
                    metadata=metadata or {},
                    score=score,
                )
            )

        return retrieved