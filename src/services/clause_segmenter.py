from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """
    Clean and normalize extracted document text.
    """

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove excessive spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove spaces around newlines
    text = re.sub(r" *\n *", "\n", text)

    return text.strip()


def _rough_token_count(text: str) -> int:
    """
    Rough token estimation.

    This is intentionally lightweight and does not require
    a tokenizer/model.
    """

    if not text:
        return 0

    words = re.findall(
        r"\S+",
        text,
    )

    return len(words)


def _split_long_clauses(
    text: str,
    max_tokens: int,
) -> list[str]:
    """
    Split a clause that is too long into smaller pieces.
    """

    if not text:
        return []

    if max_tokens <= 0:
        return [text.strip()]

    words = text.split()

    if len(words) <= max_tokens:
        return [text.strip()]

    chunks: list[str] = []

    for start in range(
        0,
        len(words),
        max_tokens,
    ):
        chunk = " ".join(
            words[
                start:start + max_tokens
            ]
        ).strip()

        if chunk:
            chunks.append(chunk)

    return chunks


def _looks_like_heading(line: str) -> bool:
    """
    Determine whether a line looks like a legal
    section/clause heading.
    """

    line = line.strip()

    if not line:
        return False

    patterns = [
        # 1. Definitions
        r"^\d+(?:\.\d+)*[\.\)]?\s+.+",

        # 1.1 Definitions
        r"^\d+\.\d+\s+.+",

        # ARTICLE I
        r"^article\s+[ivxlcdm0-9]+",

        # SECTION 1
        r"^section\s+\d+",

        # CLAUSE 1
        r"^clause\s+\d+",

        # SCHEDULE 1
        r"^schedule\s+\d+",

        # ANNEXURE A
        r"^annexure\s+[a-z0-9]+",

        # EXHIBIT A
        r"^exhibit\s+[a-z0-9]+",

        # Common legal headings
        r"^(definitions|termination|confidentiality|"
        r"indemnity|indemnification|"
        r"limitation of liability|"
        r"governing law|jurisdiction|"
        r"dispute resolution|arbitration|"
        r"force majeure|"
        r"intellectual property|"
        r"payment|"
        r"representations and warranties|"
        r"warranties|"
        r"notice|"
        r"miscellaneous)\s*$",
    ]

    for pattern in patterns:
        if re.match(
            pattern,
            line,
            re.IGNORECASE,
        ):
            return True

    return False


def _split_by_numbered_clauses(
    text: str,
) -> list[str]:
    """
    Split text using numbered legal clauses such as:

        1. Definitions
        2. Confidentiality
        3. Termination

    or:

        1.1 Definitions
        1.2 Obligations
    """

    pattern = re.compile(
        r"(?m)^\s*"
        r"(?P<number>\d+(?:\.\d+)*"
        r"[\.\)]?)"
        r"\s+"
    )

    matches = list(
        pattern.finditer(text)
    )

    if not matches:
        return []

    clauses: list[str] = []

    for index, match in enumerate(matches):
        start = match.start()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        clause = text[start:end].strip()

        if clause:
            clauses.append(clause)

    return clauses


def _split_by_headings(
    text: str,
) -> list[str]:
    """
    Split a document when legal headings appear on separate lines.
    """

    lines = text.splitlines()

    clauses: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if current:
                current.append("")
            continue

        if _looks_like_heading(stripped):
            if current:
                previous = "\n".join(
                    current
                ).strip()

                if previous:
                    clauses.append(previous)

                current = []

            current.append(stripped)

        else:
            current.append(stripped)

    if current:
        final_clause = "\n".join(
            current
        ).strip()

        if final_clause:
            clauses.append(final_clause)

    return clauses


def _split_by_paragraphs(
    text: str,
) -> list[str]:
    """
    Fallback splitter based on paragraphs.
    """

    paragraphs = re.split(
        r"\n\s*\n",
        text,
    )

    return [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]


def split_into_clauses(
    text: str,
) -> list[str]:
    """
    Main clause segmentation function.

    The function tries:

    1. Numbered legal clauses
    2. Legal headings
    3. Paragraphs

    and returns a list of clause strings.
    """

    text = normalize_text(text)

    if not text:
        return []

    # ---------------------------------------------------------
    # First attempt: numbered clauses
    # ---------------------------------------------------------

    clauses = _split_by_numbered_clauses(
        text
    )

    # ---------------------------------------------------------
    # Second attempt: headings
    # ---------------------------------------------------------

    if len(clauses) < 2:
        heading_clauses = _split_by_headings(
            text
        )

        if len(heading_clauses) > len(clauses):
            clauses = heading_clauses

    # ---------------------------------------------------------
    # Third attempt: paragraphs
    # ---------------------------------------------------------

    if len(clauses) < 2:
        paragraph_clauses = _split_by_paragraphs(
            text
        )

        if len(paragraph_clauses) > len(clauses):
            clauses = paragraph_clauses

    # ---------------------------------------------------------
    # If everything is one block, use the entire document.
    # ---------------------------------------------------------

    if not clauses:
        clauses = [text]

    # ---------------------------------------------------------
    # Split very large clauses
    # ---------------------------------------------------------

    final_chunks: list[str] = []

    # Approximately 700 words per chunk.
    max_tokens = 700

    for clause in clauses:
        clause = clause.strip()

        if not clause:
            continue

        if _rough_token_count(
            clause
        ) > max_tokens:

            smaller_chunks = _split_long_clauses(
                clause,
                max_tokens,
            )

            final_chunks.extend(
                smaller_chunks
            )

        else:
            final_chunks.append(
                clause
            )

    # ---------------------------------------------------------
    # Remove duplicates
    # ---------------------------------------------------------

    unique_chunks: list[str] = []
    seen: set[str] = set()

    for chunk in final_chunks:
        normalized = re.sub(
            r"\s+",
            " ",
            chunk,
        ).strip()

        if not normalized:
            continue

        key = normalized.lower()

        if key in seen:
            continue

        seen.add(key)
        unique_chunks.append(
            chunk.strip()
        )

    return unique_chunks


# =============================================================
# Compatibility wrapper
# =============================================================

class ClauseSegmenter:
    """
    Compatibility wrapper around the existing
    split_into_clauses() function.

    LegalAssistantService can use this class without
    changing the existing segmentation implementation.
    """

    def segment(
        self,
        text: str,
    ) -> list[str]:
        return split_into_clauses(
            text
        )

    def segment_clauses(
        self,
        text: str,
    ) -> list[str]:
        return split_into_clauses(
            text
        )

    def extract_clauses(
        self,
        text: str,
    ) -> list[str]:
        return split_into_clauses(
            text
        )