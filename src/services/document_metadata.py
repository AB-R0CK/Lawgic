from __future__ import annotations

import re
from typing import Any


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean(value: Any) -> str:
    """
    Clean a value and convert it to a string.
    """

    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _unique(values: list[str]) -> list[str]:
    """
    Remove duplicate strings while preserving order.
    """

    result: list[str] = []

    seen: set[str] = set()

    for value in values:

        value = _clean(value)

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)

        result.append(value)

    return result


def _first_match(
    text: str,
    patterns: list[str],
    flags: int = re.IGNORECASE,
) -> str | None:
    """
    Return the first regex match from a list of patterns.
    """

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags,
        )

        if match:

            if match.groups():
                return _clean(
                    match.group(1)
                )

            return _clean(
                match.group(0)
            )

    return None


# ============================================================
# DOCUMENT TYPE
# ============================================================

def detect_document_type(
    text: str,
    filename: str = "",
) -> str:
    """
    Detect the general type of legal document.
    """

    combined = (
        f"{filename}\n{text[:12000]}"
    ).lower()

    document_types = [
        (
            "Non-Disclosure Agreement",
            [
                "non disclosure agreement",
                "non-disclosure agreement",
                "nda",
            ],
        ),

        (
            "Employment Agreement",
            [
                "employment agreement",
                "employment contract",
                "letter of employment",
                "employee agreement",
            ],
        ),

        (
            "Lease Agreement",
            [
                "lease agreement",
                "rental agreement",
                "lease deed",
                "landlord",
                "tenant",
            ],
        ),

        (
            "Sale Agreement",
            [
                "sale agreement",
                "agreement for sale",
                "sale deed",
            ],
        ),

        (
            "Service Agreement",
            [
                "service agreement",
                "services agreement",
                "service contract",
            ],
        ),

        (
            "Partnership Agreement",
            [
                "partnership agreement",
                "partnership deed",
            ],
        ),

        (
            "Loan Agreement",
            [
                "loan agreement",
                "loan contract",
                "borrower",
                "lender",
            ],
        ),

        (
            "Vendor Agreement",
            [
                "vendor agreement",
                "supplier agreement",
                "vendor contract",
            ],
        ),

        (
            "Terms and Conditions",
            [
                "terms and conditions",
                "terms & conditions",
                "terms of service",
            ],
        ),

        (
            "Privacy Policy",
            [
                "privacy policy",
                "privacy notice",
            ],
        ),

        (
            "Power of Attorney",
            [
                "power of attorney",
                "attorney-in-fact",
            ],
        ),

        (
            "Memorandum of Understanding",
            [
                "memorandum of understanding",
                "mou",
            ],
        ),

        (
            "Affidavit",
            [
                "affidavit",
                "sworn statement",
            ],
        ),

        (
            "Legal Notice",
            [
                "legal notice",
                "notice to",
                "notice of demand",
            ],
        ),

        (
            "Court / Legal Document",
            [
                "in the court of",
                "before the court",
                "petition",
                "plaint",
                "respondent",
                "appellant",
            ],
        ),
    ]

    for document_type, keywords in document_types:

        for keyword in keywords:

            if keyword in combined:

                return document_type

    return "Legal Document"


# ============================================================
# DOCUMENT TITLE
# ============================================================

def extract_document_title(
    text: str,
    filename: str = "",
) -> str:
    """
    Extract a probable document title.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # --------------------------------------------------------
    # Look for explicit title
    # --------------------------------------------------------

    title_patterns = [
        r"^\s*(?:title|document title)\s*[:\-]\s*(.+)$",

        r"^\s*(?:agreement|deed|contract)\s+of\s+(.+)$",

        r"^\s*(.+agreement)\s*$",

        r"^\s*(.+contract)\s*$",

        r"^\s*(.+deed)\s*$",

        r"^\s*(.+policy)\s*$",
    ]

    for line in lines[:30]:

        for pattern in title_patterns:

            match = re.search(
                pattern,
                line,
                re.IGNORECASE,
            )

            if match:

                title = _clean(
                    match.group(1)
                    if match.groups()
                    else match.group(0)
                )

                if len(title) >= 4:
                    return title

    # --------------------------------------------------------
    # Use first meaningful line
    # --------------------------------------------------------

    for line in lines[:20]:

        clean_line = _clean(line)

        if not clean_line:
            continue

        if len(clean_line) < 4:
            continue

        if len(clean_line) > 150:
            continue

        # Skip obvious metadata
        if re.match(
            r"^(page|date|between|and)\b",
            clean_line,
            re.IGNORECASE,
        ):
            continue

        return clean_line

    # --------------------------------------------------------
    # Filename fallback
    # --------------------------------------------------------

    if filename:

        title = filename.rsplit(
            ".",
            1,
        )[0]

        title = re.sub(
            r"[_\-]+",
            " ",
            title,
        )

        return _clean(title)

    return "Legal Document"


# ============================================================
# PARTIES
# ============================================================

def extract_parties(
    text: str,
) -> list[str]:
    """
    Extract likely parties from legal document text.
    """

    parties: list[str] = []

    # --------------------------------------------------------
    # BETWEEN ... AND ...
    # --------------------------------------------------------

    between_patterns = [
        r"\bbetween\s+(.{2,200}?)\s+and\s+(.{2,200}?)(?:\.|,|\n|hereinafter)",

        r"\bbetween\s+(.{2,200}?)\s+and\s+(.{2,200}?)(?:\s+hereinafter)",
    ]

    for pattern in between_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if match:

            for group in match.groups():

                value = _clean(group)

                if value:

                    parties.append(value)

            break

    # --------------------------------------------------------
    # PARTY / PARTIES declarations
    # --------------------------------------------------------

    party_patterns = [
        r"(?:party|parties)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:first party)\s*[:\-]?\s*([^\n.;]{2,150})",

        r"(?:second party)\s*[:\-]?\s*([^\n.;]{2,150})",

        r"(?:employer)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:employee)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:landlord)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:tenant)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:buyer)\s*[:\-]\s*([^\n.;]{2,150})",

        r"(?:seller)\s*[:\-]\s*([^\n.;]{2,150})",
    ]

    for pattern in party_patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for match in matches:

            value = _clean(match)

            if value:
                parties.append(value)

    # --------------------------------------------------------
    # Remove noisy values
    # --------------------------------------------------------

    cleaned: list[str] = []

    for party in parties:

        if len(party) < 2:
            continue

        if len(party) > 200:
            continue

        cleaned.append(party)

    return _unique(cleaned)[:10]


# ============================================================
# EFFECTIVE DATE
# ============================================================

def extract_effective_date(
    text: str,
) -> str | None:
    """
    Extract the likely effective/agreement date.
    """

    patterns = [
        r"(?:effective date|effective from|effective as of)"
        r"\s*(?:is|:|-)?\s*"
        r"([A-Za-z0-9,\-/ ]{6,40})",

        r"(?:dated|date of agreement|agreement dated)"
        r"\s*(?:is|:|-)?\s*"
        r"([A-Za-z0-9,\-/ ]{6,40})",

        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",

        r"\b(\d{1,2}(?:st|nd|rd|th)?\s+"
        r"(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+\d{4})\b",

        r"\b((?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4})\b",
    ]

    result = _first_match(
        text,
        patterns,
    )

    return result


# ============================================================
# DURATION
# ============================================================

def extract_duration(
    text: str,
) -> str | None:
    """
    Extract agreement duration / validity period.
    """

    patterns = [
        r"(?:term|duration|validity)"
        r"\s*(?:of|is|:)?\s*"
        r"([^\n.;]{3,120})",

        r"\bfor\s+(\d+\s+"
        r"(?:days?|weeks?|months?|years?))\b",

        r"\b(\d+\s+"
        r"(?:days?|weeks?|months?|years?))\s+"
        r"(?:from|after|beginning)\b",

        r"\b(perpetual|indefinite|automatically renewable)\b",
    ]

    result = _first_match(
        text,
        patterns,
    )

    return result


# ============================================================
# JURISDICTION
# ============================================================

def extract_jurisdiction(
    text: str,
) -> str | None:
    """
    Extract governing law / jurisdiction.
    """

    patterns = [
        r"(?:governing law|governed by the laws of)"
        r"\s*(?:of|:)?\s*"
        r"([^\n.;]{3,150})",

        r"(?:jurisdiction)"
        r"\s*(?:of|:)?\s*"
        r"([^\n.;]{3,150})",

        r"(?:courts? of)"
        r"\s*"
        r"([^\n.;]{3,150})",
    ]

    result = _first_match(
        text,
        patterns,
    )

    return result


# ============================================================
# KEY TERMS
# ============================================================

def extract_key_terms(
    text: str,
) -> list[str]:
    """
    Extract important legal terms found in the document.
    """

    terms = [
        "confidentiality",
        "indemnification",
        "indemnity",
        "liability",
        "limitation of liability",
        "termination",
        "notice",
        "payment",
        "fees",
        "interest",
        "penalty",
        "liquidated damages",
        "intellectual property",
        "copyright",
        "trademark",
        "patent",
        "non-compete",
        "non-solicitation",
        "exclusivity",
        "arbitration",
        "mediation",
        "dispute resolution",
        "governing law",
        "jurisdiction",
        "warranty",
        "representation",
        "force majeure",
        "renewal",
        "assignment",
        "subcontracting",
        "data protection",
        "privacy",
        "personal data",
    ]

    text_lower = text.lower()

    found: list[str] = []

    for term in terms:

        if term.lower() in text_lower:

            found.append(term)

    return _unique(found)


# ============================================================
# DOCUMENT CITATIONS
# ============================================================

def build_document_citations(
    text: str,
    filename: str = "",
) -> list[dict[str, Any]]:
    """
    Build document-level and clause-level citations.
    """

    filename = (
        filename
        or "Uploaded Document"
    )

    citations: list[
        dict[str, Any]
    ] = []

    # --------------------------------------------------------
    # Document citation
    # --------------------------------------------------------

    citations.append(
        {
            "citation": filename,

            "section": "Document",

            "reference_type": (
                "uploaded_document"
            ),

            "score": None,

            "document_name": filename,
        }
    )

    # --------------------------------------------------------
    # Detect sections / clauses
    # --------------------------------------------------------

    section_patterns = [
        r"(?im)^\s*(?:section|clause|article)"
        r"\s+([A-Za-z0-9.\-]+)"
        r"\s*[:.\-]?\s*(.*)$",

        r"(?im)^\s*(\d+(?:\.\d+)*)"
        r"\s+([A-Z][^\n]{2,100})$",
    ]

    seen_sections: set[str] = set()

    for pattern in section_patterns:

        matches = re.finditer(
            pattern,
            text,
        )

        for match in matches:

            groups = match.groups()

            if not groups:
                continue

            section_number = _clean(
                groups[0]
            )

            section_title = ""

            if len(groups) > 1:
                section_title = _clean(
                    groups[1]
                )

            section = (
                f"Section {section_number}"
            )

            if section_title:
                section += (
                    f": {section_title}"
                )

            key = section.lower()

            if key in seen_sections:
                continue

            seen_sections.add(key)

            citations.append(
                {
                    "citation": filename,

                    "section": section,

                    "reference_type": (
                        "document_section"
                    ),

                    "score": None,

                    "document_name": filename,
                }
            )

            if len(citations) >= 50:
                return citations

    return citations


# ============================================================
# COMPLETE METADATA EXTRACTION
# ============================================================

def extract_document_metadata(
    text: str,
    filename: str = "",
) -> dict[str, Any]:
    """
    Extract all supported metadata from a legal document.
    """

    text = _clean(text)

    filename = (
        filename
        or "Uploaded Document"
    )

    metadata = {
        "document_type": detect_document_type(
            text,
            filename,
        ),

        "document_title": extract_document_title(
            text,
            filename,
        ),

        "parties_involved": extract_parties(
            text
        ),

        "effective_date": extract_effective_date(
            text
        ),

        "duration_validity": extract_duration(
            text
        ),

        "governing_law_jurisdiction": extract_jurisdiction(
            text
        ),

        "key_terms": extract_key_terms(
            text
        ),

        "filename": filename,
    }

    return metadata


# ============================================================
# FORMAT METADATA
# ============================================================

def format_document_metadata(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Normalize metadata for API / frontend output.
    """

    if metadata is None:
        metadata = {}

    result = {
        "document_type": metadata.get(
            "document_type",
            "Legal Document",
        ),

        "document_title": metadata.get(
            "document_title",
            "Untitled Document",
        ),

        "parties_involved": metadata.get(
            "parties_involved",
            [],
        ),

        "effective_date": metadata.get(
            "effective_date",
            None,
        ),

        "duration_validity": metadata.get(
            "duration_validity",
            None,
        ),

        "governing_law_jurisdiction": metadata.get(
            "governing_law_jurisdiction",
            None,
        ),

        "key_terms": metadata.get(
            "key_terms",
            [],
        ),

        "filename": metadata.get(
            "filename",
            None,
        ),
    }

    return result


# ============================================================
# DOCUMENT METADATA EXTRACTOR CLASS
# ============================================================

class DocumentMetadataExtractor:
    """
    Compatibility wrapper used by LegalAssistantService.

    The original metadata implementation uses functions.
    This class exposes those functions through a simple
    service interface.
    """

    def extract_metadata(
        self,
        text: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Extract metadata from a document.
        """

        metadata = extract_document_metadata(
            text=text,
            filename=filename or "Uploaded Document",
        )

        return format_document_metadata(
            metadata
        )

    def get_metadata(
        self,
        text: str,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Alias for extract_metadata().
        """

        return self.extract_metadata(
            text=text,
            filename=filename,
        )

    def build_citations(
        self,
        text: str,
        filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build citations for the document.
        """

        return build_document_citations(
            text=text,
            filename=filename or "Uploaded Document",
        )

    def format_metadata(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Format metadata for API output.
        """

        return format_document_metadata(
            metadata
        )


# ============================================================
# SIMPLE SERVICE FACTORY
# ============================================================

_metadata_extractor: (
    DocumentMetadataExtractor | None
) = None


def get_document_metadata_extractor() -> DocumentMetadataExtractor:
    """
    Return a shared DocumentMetadataExtractor instance.
    """

    global _metadata_extractor

    if _metadata_extractor is None:

        _metadata_extractor = (
            DocumentMetadataExtractor()
        )

    return _metadata_extractor