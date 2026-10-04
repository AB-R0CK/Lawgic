from collections.abc import Iterator
import re

from src.services.llm.base import LLMClient


class LocalLLMClient(LLMClient):
    """
    Ollama-free fallback LLM.

    This version does NOT make any external network request.
    It generates an answer directly from the supplied document context.
    """

    def generate(self, prompt: str) -> str:
        return self._answer(prompt)

    def stream_generate(self, prompt: str) -> Iterator[str]:
        answer = self._answer(prompt)

        # Stream in small chunks so the frontend behaves like ChatGPT.
        words = answer.split()

        buffer = []

        for word in words:
            buffer.append(word)

            if len(buffer) >= 6:
                yield " ".join(buffer) + " "
                buffer = []

        if buffer:
            yield " ".join(buffer) + " "

    def _answer(self, prompt: str) -> str:
        context = self._extract_context(prompt)
        question = self._extract_question(prompt)

        # If no document context is available, provide general legal knowledge
        if not context.strip() or context == "No document context available.":
            general_answer = self._get_general_legal_knowledge(question)
            if general_answer:
                return f"**{question}**\n\n{general_answer}"
            return (
                f"**{question}**\n\n"
                "I couldn't find document context for this question. "
                "Please upload and analyze a legal PDF first, or ask a general legal question."
            )

        # Document context is available - answer ONLY from the document
        # Extract document name from context
        document_name = self._extract_document_name(context)
        
        # Extract section/clause numbers from question to check if they exist
        requested_section = self._extract_requested_section(question)
        
        # Check if the requested section exists in the context
        if requested_section and not self._section_exists_in_context(context, requested_section):
            return (
                f"**{question}**\n\n"
                f"I couldn't find {requested_section} in the uploaded document. "
                f"Please verify the section number or ask about other sections mentioned in the document.\n\n"
                f"**Source:** {document_name}"
            )

        # Extract legal acts and statutes from context
        legal_acts = self._extract_legal_acts(context)
        
        # Extract document metadata
        metadata = self._extract_metadata(context, question)
        
        # Find relevant text based on question
        relevant = self._find_relevant_text(
            context=context,
            question=question,
        )

        if not relevant:
            return (
                f"**{question}**\n\n"
                "I couldn't find this information in the uploaded document.\n\n"
                f"**Source:** {document_name}"
            )

        # Extract relevant section/clause from the relevant text
        relevant_section = self._extract_section_from_text(relevant)

        # Build structured response following the expected format
        response_parts = []
        
        # Direct Answer
        response_parts.append(f"### Direct Answer\n\n{relevant}")
        
        # Explanation (simplified version of the answer)
        response_parts.append(f"\n### Explanation\n\nThis information is based on the uploaded document content.")
        
        # Relevant Section/Clause
        if relevant_section:
            response_parts.append(f"\n### Relevant Section/Clause\n\n**{relevant_section}**")
        
        # Source
        response_parts.append(f"\n### Source\n\n**{document_name}**")
        
        return "\n".join(response_parts)

    @staticmethod
    def _extract_document_name(context: str) -> str:
        """Extract document name from context"""
        # Look for "Document: filename" pattern in context
        doc_match = re.search(r"Document:\s*([^\n]+)", context, re.IGNORECASE)
        if doc_match:
            return doc_match.group(1).strip()
        return "Uploaded Document"

    @staticmethod
    def _extract_requested_section(question: str) -> str | None:
        """Extract section/clause number from question"""
        # Match patterns like "section 50", "clause 5", "article 10"
        section_match = re.search(r"(?:section|clause|article)\s+(\d+)", question, re.IGNORECASE)
        if section_match:
            section_num = section_match.group(1)
            prefix = "Section" if "section" in question.lower() else "Clause" if "clause" in question.lower() else "Article"
            return f"{prefix} {section_num}"
        return None

    @staticmethod
    def _section_exists_in_context(context: str, section: str) -> bool:
        """Check if a specific section exists in the context"""
        # Look for the section number in context
        section_num = re.search(r"\d+", section)
        if section_num:
            # Check for patterns like "Section 50", "Section 50:", "50."
            patterns = [
                rf"section\s+{section_num.group()}",
                rf"clause\s+{section_num.group()}",
                rf"article\s+{section_num.group()}",
                rf"{section_num.group()}[\.\)]",
            ]
            for pattern in patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    return True
        return False

    @staticmethod
    def _extract_section_from_text(text: str) -> str | None:
        """Extract section/clause reference from the relevant text"""
        # Look for section/clause patterns at the beginning of the text
        section_match = re.search(r"^(?:Section|Clause|Article)\s+\d+", text, re.IGNORECASE)
        if section_match:
            return section_match.group(0)
        return None

    @staticmethod
    def _wants_document_answer(question: str) -> bool:
        # This method is no longer used - kept for compatibility
        # All questions now use document context when available
        return True

    @staticmethod
    def _get_general_legal_knowledge(question: str) -> str:
        """Provide general legal knowledge for questions not tied to a specific document"""
        question_lower = question.lower()
        
        # IT Act 2000
        if "it act" in question_lower or "information technology act" in question_lower:
            return """
The Information Technology Act, 2000 is an Indian law that provides legal recognition for electronic transactions and digital signatures.

**Key Provisions:**

• **Section 65**: Tampering with computer source documents - punishable with imprisonment up to 3 years or fine up to ₹2 lakh or both
• **Section 66**: Computer-related offenses - punishable with imprisonment up to 3 years or fine up to ₹5 lakh or both
• **Section 66A**: Sending offensive messages through communication service (struck down by Supreme Court in 2015)
• **Section 66B**: Dishonestly receiving stolen computer resource or communication device
• **Section 66C**: Punishment for identity theft - imprisonment up to 3 years and fine up to ₹1 lakh
• **Section 66D**: Cheating by personation by using computer resource
• **Section 66E**: Punishment for violation of privacy - imprisonment up to 3 years or fine up to ₹2 lakh
• **Section 66F**: Cyber terrorism - punishable with imprisonment which may extend to life
• **Section 67**: Publishing obscene material in electronic form - imprisonment up to 3 years on first conviction, up to 5 years on second conviction
• **Section 67A**: Publishing sexually explicit material in electronic form
• **Section 67B**: Publishing material depicting children in sexually explicit act in electronic form
• **Section 67C**: Preservation of records by intermediaries
• **Section 69**: Power to issue directions for interception or monitoring or decryption of any information
• **Section 69A**: Power to issue directions for blocking for public access of any information
• **Section 72**: Penalty for breach of confidentiality and privacy
• **Section 72A**: Punishment for disclosure of information in breach of lawful contract

**Amendment 2008:**
The Act was amended in 2008 to include provisions for:
- Cyber cafes regulation
- Data protection
- Intermediary liability
- Examination of electronic evidence

**Purpose:**
- To provide legal framework for electronic commerce
- To facilitate electronic filing of documents
- To give legal recognition to digital signatures
- To prevent cyber crimes and provide penalties
"""
        
        # Indian Penal Code
        if "ipc" in question_lower or "indian penal code" in question_lower:
            return """
The Indian Penal Code (IPC) is the official criminal code of India, enacted in 1860.

**Key Sections:**

• **Section 299**: Definition of culpable homicide
• **Section 300**: Murder - punishable with death or life imprisonment
• **Section 302**: Punishment for murder - death or life imprisonment and fine
• **Section 304**: Punishment for culpable homicide not amounting to murder
• **Section 304A**: Causing death by negligence - imprisonment up to 2 years or fine or both
• **Section 375**: Definition of rape
• **Section 376**: Punishment for rape - imprisonment not less than 7 years
• **Section 376D**: Gang rape - imprisonment not less than 20 years
• **Section 377**: Unnatural offenses
• **Section 420**: Cheating and dishonestly inducing delivery of property - imprisonment up to 7 years and fine
• **Section 467**: Forgery of valuable security - imprisonment up to 10 years and fine
• **Section 468**: Forgery for purpose of cheating - imprisonment up to 7 years and fine
• **Section 471**: Using forged document as genuine
• **Section 498A**: Husband or relative of husband subjecting woman to cruelty
• **Section 503**: Criminal intimidation
• **Section 506**: Punishment for criminal intimidation

**Purpose:**
- To define crimes and prescribe punishments
- To provide a uniform penal code for India
- To cover all substantive aspects of criminal law
"""
        
        # Contract Act
        if "contract act" in question_lower or "indian contract act" in question_lower:
            return """
The Indian Contract Act, 1872 governs contract law in India.

**Key Sections:**

• **Section 2(h)**: Definition of contract - an agreement enforceable by law
• **Section 10**: All agreements are contracts if made by free consent of parties competent to contract, for lawful consideration and lawful object
• **Section 11**: Who are competent to contract - persons of age of majority, sound mind, not disqualified from contracting
• **Section 12**: Definition of sound mind
• **Section 13**: Definition of consent - when two or more persons agree upon the same thing in the same sense
• **Section 14**: Free consent - consent not caused by coercion, undue influence, fraud, misrepresentation, or mistake
• **Section 15**: Coercion - committing or threatening to commit any act forbidden by IPC
• **Section 16**: Undue influence - where one party is in a position to dominate the will of the other
• **Section 17**: Fraud - any act committed to deceive
• **Section 18**: Misrepresentation - innocent or negligent misstatement
• **Section 19**: Voidability of agreements without free consent
• **Section 23**: What considerations and objects are unlawful
• **Section 56**: Agreement to do impossible act - void
• **Section 73**: Compensation for loss or damage caused by breach of contract
• **Section 74**: Compensation for breach of contract where penalty stipulated
• **Section 75**: Party rightfully rescinding contract entitled to compensation

**Types of Contracts:**
- Valid contract
- Void contract
- Voidable contract
- Unenforceable contract
"""
        
        # Companies Act
        if "companies act" in question_lower:
            return """
The Companies Act, 2013 is the primary legislation governing companies in India.

**Key Provisions:**

• **Section 2(20)**: Definition of company
• **Section 2(45)**: Definition of private company
• **Section 2(68)**: Definition of public company
• **Section 2(71)**: Definition of one person company
• **Section 2(85)**: Definition of subsidiary company
• **Section 2(87)**: Definition of holding company
• **Section 3**: Formation of companies
• **Section 4**: Incorporation of company
• **Section 12**: Registered office of company
• **Section 21**: Name of company
• **Section 149**: Board of directors - minimum 3 directors for public company, 2 for private
• **Section 152**: Appointment of directors
• **Section 156**: Vacation of office of director
• **Section 167**: Disqualification of directors
• **Section 173**: Board meetings - at least 4 meetings in a year
• **Section 179**: Powers of Board
• **Section 201**: Audit of accounts
• **Section 211**: Books of account
• **Section 213**: Financial statements
• **Section 219**: Directors' responsibility statement
• **Section 320**: Statutory audit
• **Section 447**: Fraud - punishable with imprisonment up to 10 years and fine

**Types of Companies:**
- Private Limited Company
- Public Limited Company
- One Person Company
- Limited Liability Partnership (LLP)
- Section 8 Company (Non-profit)
"""
        
        # Consumer Protection Act
        if "consumer protection act" in question_lower:
            return """
The Consumer Protection Act, 2019 protects consumer rights in India.

**Key Provisions:**

• **Section 2(7)**: Definition of consumer
• **Section 2(9)**: Definition of complaint
• **Section 2(11)**: Definition of defect
• **Section 2(34)**: Definition of unfair trade practice
• **Section 2(47)**: Definition of unfair contract
• **Section 6**: Consumer Rights
  - Right to be informed
  - Right to choose
  - Right to be heard
  - Right to redressal
  - Right to consumer education
  - Right to seek compensation
• **Section 8**: Consumer Protection Councils
• **Section 9**: Central Consumer Protection Authority
• **Section 10**: Investigation powers
• **Section 11**: Recall of goods
• **Section 12**: Withdrawal of services
• **Section 35**: Consumer Disputes Redressal Commissions
• **Section 38**: District Consumer Disputes Redressal Commission
• **Section 39**: State Consumer Disputes Redressal Commission
• **Section 40**: National Consumer Disputes Redressal Commission

**Pecuniary Jurisdiction:**
- District Commission: Up to ₹1 crore
- State Commission: ₹1 crore to ₹10 crore
- National Commission: Above ₹10 crore
"""
        
        # GST Act
        if "gst act" in question_lower or "goods and services tax" in question_lower:
            return """
The Goods and Services Tax (GST) is a comprehensive indirect tax in India.

**Key Features:**

• **CGST (Central GST)**: Collected by Central Government
• **SGST (State GST)**: Collected by State Government
• **IGST (Integrated GST)**: Collected on inter-state transactions
• **UTGST (Union Territory GST)**: Collected in Union Territories

**Tax Rates:**
- 0% (Essential goods)
- 5% (Basic necessities)
- 12% (Standard rate)
- 18% (Standard rate)
- 28% (Luxury goods)

**Registration Threshold:**
- ₹40 lakh for goods
- ₹20 lakh for services
- ₹10 lakh for special category states

**Key Sections:**
- Section 9: Levy and collection of CGST
- Section 10: Levy and collection of SGST
- Section 11: Levy and collection of IGST
- Section 16: Input Tax Credit
- Section 31: Issue of tax invoice
- Section 39: Return of tax
- Section 42: Payment of tax
"""
        
        # Default response for other legal questions
        return """
I can provide general information about Indian legal acts. Please specify which act you're interested in:

• Information Technology Act, 2000
• Indian Penal Code, 1860
• Indian Contract Act, 1872
• Companies Act, 2013
• Consumer Protection Act, 2019
• Goods and Services Tax (GST)

For document-specific answers, include keywords like "document", "section", "clause", or "article" in your question.
"""

    @staticmethod
    def _extract_context(prompt: str) -> str:
        markers = [
            ("Context:", "User Clause"),
            ("RETRIEVED LEGAL CONTEXT:", "USER QUESTION:"),
            ("DOCUMENT / RETRIEVAL CONTEXT:", "USER QUESTION:"),
        ]

        for start_marker, end_marker in markers:
            if start_marker in prompt:
                text = prompt.split(start_marker, 1)[1]

                if end_marker in text:
                    text = text.split(end_marker, 1)[0]

                return text.strip()

        return prompt

    @staticmethod
    def _extract_question(prompt: str) -> str:
        markers = [
            "User Query:",
            "USER QUESTION:",
            "Question:",
        ]

        for marker in markers:
            if marker in prompt:
                return prompt.split(marker, 1)[1].strip()

        return ""

    @staticmethod
    def _find_relevant_text(
        context: str,
        question: str,
    ) -> str:
        if not question.strip():
            return context[:5000]

        question_lower = question.lower()
        
        # Check for specific question types and extract targeted content
        if "bye law" in question_lower or "byelaw" in question_lower or "bye-law" in question_lower:
            return LocalLLMClient._extract_bye_laws(context)
        
        if "section" in question_lower:
            return LocalLLMClient._extract_sections(context, question)
        
        if "clause" in question_lower:
            return LocalLLMClient._extract_clauses(context, question)
        
        if "obligation" in question_lower or "duty" in question_lower or "responsibility" in question_lower:
            return LocalLLMClient._extract_obligations(context)
        
        if "right" in question_lower:
            return LocalLLMClient._extract_rights(context)
        
        # Default: use word matching
        question_words = {
            word.lower()
            for word in re.findall(
                r"[A-Za-z]{4,}",
                question,
            )
        }

        if not question_words:
            return context[:5000]

        paragraphs = re.split(
            r"\n\s*\n",
            context,
        )

        scored = []

        for paragraph in paragraphs:
            words = {
                word.lower()
                for word in re.findall(
                    r"[A-Za-z]{4,}",
                    paragraph,
                )
            }

            score = len(question_words.intersection(words))

            if score > 0:
                scored.append(
                    (
                        score,
                        paragraph.strip(),
                    )
                )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        if not scored:
            return context[:5000]

        selected = []

        for _, paragraph in scored[:5]:
            if paragraph:
                selected.append(paragraph)

        return "\n\n".join(selected)[:7000]

    @staticmethod
    def _extract_bye_laws(context: str) -> str:
        """Extract bye laws from context"""
        bye_laws = []
        
        # Look for bye law sections
        patterns = [
            r"(?:bye[-\s]?law|byelaw|bye[-\s]?law\s+no\.?\s*\d+)[\s:]+([^\n]{20,500})",
            r"(?:article|article\s+\d+)[\s:]+([^\n]{20,500})",
            r"(?:rule|rule\s+\d+)[\s:]+([^\n]{20,500})",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip() not in bye_laws:
                    bye_laws.append(match.strip())
        
        if not bye_laws:
            # Fallback: look for numbered sections that might be bye laws
            numbered_sections = re.findall(
                r"(?:\d+[\.\)]\s+[A-Z][^\n]{20,300})",
                context
            )
            bye_laws = numbered_sections[:5]
        
        if bye_laws:
            return "\n".join([f"• {law}" for law in bye_laws[:8]])
        
        return "No specific bye laws found in the document context."

    @staticmethod
    def _extract_sections(context: str, question: str) -> str:
        """Extract specific sections mentioned in question"""
        # Extract section numbers from question
        section_nums = re.findall(r"section\s+(\d+)", question, re.IGNORECASE)
        
        if section_nums:
            results = []
            for num in section_nums:
                pattern = rf"section\s+{num}[\s:]+([^\n]{{20,500}})"
                matches = re.findall(pattern, context, re.IGNORECASE)
                for match in matches:
                    results.append(f"Section {num}: {match.strip()}")
            
            if results:
                return "\n".join(results)
        
        # If no specific section numbers, return all section references
        sections = re.findall(
            r"section\s+\d+[\s:]+([^\n]{20,300})",
            context,
            re.IGNORECASE
        )
        
        if sections:
            return "\n".join([f"• {s.strip()}" for s in sections[:5]])
        
        return "No specific sections found matching your query."

    @staticmethod
    def _extract_clauses(context: str, question: str) -> str:
        """Extract specific clauses"""
        clause_nums = re.findall(r"clause\s+(\d+)", question, re.IGNORECASE)
        
        if clause_nums:
            results = []
            for num in clause_nums:
                pattern = rf"clause\s+{num}[\s:]+([^\n]{{20,500}})"
                matches = re.findall(pattern, context, re.IGNORECASE)
                for match in matches:
                    results.append(f"Clause {num}: {match.strip()}")
            
            if results:
                return "\n".join(results)
        
        # Return all clauses
        clauses = re.findall(
            r"clause\s+\d+[\s:]+([^\n]{20,300})",
            context,
            re.IGNORECASE
        )
        
        if clauses:
            return "\n".join([f"• {c.strip()}" for c in clauses[:5]])
        
        return "No specific clauses found matching your query."

    @staticmethod
    def _extract_obligations(context: str) -> str:
        """Extract obligations, duties, responsibilities"""
        obligation_patterns = [
            r"(?:shall|must|required to|obligated to)\s+([^\n.]{10,200})",
            r"(?:responsibility|duty|obligation)[\s:]+([^\n.]{10,200})",
        ]
        
        obligations = []
        for pattern in obligation_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip() not in obligations:
                    obligations.append(match.strip())
        
        if obligations:
            return "\n".join([f"• {o}" for o in obligations[:8]])
        
        return "No specific obligations found in the document context."

    @staticmethod
    def _extract_rights(context: str) -> str:
        """Extract rights"""
        right_patterns = [
            r"(?:right|entitled to|has the right to)\s+([^\n.]{10,200})",
        ]
        
        rights = []
        for pattern in right_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                if match.strip() and match.strip() not in rights:
                    rights.append(match.strip())
        
        if rights:
            return "\n".join([f"• {r}" for r in rights[:8]])
        
        return "No specific rights found in the document context."

    @staticmethod
    def _extract_legal_acts(context: str) -> list[str]:
        """Extract legal acts and statutes mentioned in the document"""
        legal_acts = []
        
        # Common Indian legal acts and statutes
        act_patterns = [
            r"Indian Penal Code(?:,?\s*\d{4})?",
            r"IPC(?:\s+Section\s+\d+)?",
            r"Code of Criminal Procedure(?:,?\s*\d{4})?",
            r"CrPC(?:\s+Section\s+\d+)?",
            r"Code of Civil Procedure(?:,?\s*\d{4})?",
            r"CPC(?:\s+Section\s+\d+)?",
            r"Indian Contract Act(?:,?\s*\d{4})?",
            r"Contract Act(?:,?\s*\d{4})?",
            r"Companies Act(?:,?\s*\d{4})?",
            r"Information Technology Act(?:,?\s*\d{4})?",
            r"IT Act(?:,?\s*\d{4})?",
            r"Arbitration and Conciliation Act(?:,?\s*\d{4})?",
            r"Consumer Protection Act(?:,?\s*\d{4})?",
            r"Transfer of Property Act(?:,?\s*\d{4})?",
            r"Negotiable Instruments Act(?:,?\s*\d{4})?",
            r"Constitution of India",
            r"Industrial Disputes Act(?:,?\s*\d{4})?",
            r"Factories Act(?:,?\s*\d{4})?",
            r"Payment of Wages Act(?:,?\s*\d{4})?",
            r"Payment of Bonus Act(?:,?\s*\d{4})?",
            r"Employees' Provident Fund Act(?:,?\s*\d{4})?",
            r"Employees' State Insurance Act(?:,?\s*\d{4})?",
            r"Workmen's Compensation Act(?:,?\s*\d{4})?",
            r"Maternity Benefit Act(?:,?\s*\d{4})?",
            r"Minimum Wages Act(?:,?\s*\d{4})?",
            r"Shops and Establishments Act(?:,?\s*\d{4})?",
            r"Sales Tax Act(?:,?\s*\d{4})?",
            r"Goods and Services Tax Act(?:,?\s*\d{4})?",
            r"GST Act(?:,?\s*\d{4})?",
            r"Income Tax Act(?:,?\s*\d{4})?",
            r"Securities and Exchange Board of India Act(?:,?\s*\d{4})?",
            r"SEBI Act(?:,?\s*\d{4})?",
            r"Foreign Exchange Management Act(?:,?\s*\d{4})?",
            r"FEMA(?:,?\s*\d{4})?",
            r"Competition Act(?:,?\s*\d{4})?",
            r"Intellectual Property Rights(?:,?\s*\d{4})?",
            r"Copyright Act(?:,?\s*\d{4})?",
            r"Patents Act(?:,?\s*\d{4})?",
            r"Trademarks Act(?:,?\s*\d{4})?",
            r"Designs Act(?:,?\s*\d{4})?",
            r"Geographical Indications of Goods Act(?:,?\s*\d{4})?",
            r"Protection of Plant Varieties and Farmers' Rights Act(?:,?\s*\d{4})?",
            r"Biological Diversity Act(?:,?\s*\d{4})?",
            r"Environment Protection Act(?:,?\s*\d{4})?",
            r"Air Act(?:,?\s*\d{4})?",
            r"Water Act(?:,?\s*\d{4})?",
            r"Hazardous Wastes Act(?:,?\s*\d{4})?",
            r"Cooperative Societies Act(?:,?\s*\d{4})?",
            r"Societies Registration Act(?:,?\s*\d{4})?",
            r"Trusts Act(?:,?\s*\d{4})?",
        ]
        
        for pattern in act_patterns:
            matches = re.findall(pattern, context, re.IGNORECASE)
            for match in matches:
                if match not in legal_acts:
                    legal_acts.append(match)
        
        return legal_acts

    @staticmethod
    def _extract_metadata(context: str, question: str) -> dict[str, str]:
        """Extract document metadata from context"""
        metadata = {}
        
        # Extract document type
        doc_types = [
            "Non-Disclosure Agreement", "NDA", "Employment Agreement", 
            "Lease Agreement", "Sale Agreement", "Service Agreement",
            "Partnership Agreement", "Loan Agreement", "Vendor Agreement",
            "Terms and Conditions", "Privacy Policy", "Power of Attorney",
            "Memorandum of Understanding", "MOU", "Affidavit", "Legal Notice"
        ]
        for doc_type in doc_types:
            if doc_type.lower() in context.lower():
                metadata["Document Type"] = doc_type
                break
        
        # Extract effective date
        date_pattern = r"(?:effective date|dated|agreement dated|effective from)[:\s]*([A-Za-z0-9,\-/ ]{6,40})"
        date_match = re.search(date_pattern, context, re.IGNORECASE)
        if date_match:
            metadata["Effective Date"] = date_match.group(1).strip()
        
        # Extract governing law/jurisdiction
        law_pattern = r"(?:governing law|governed by|jurisdiction)[:\s]*([^\n.;]{3,100})"
        law_match = re.search(law_pattern, context, re.IGNORECASE)
        if law_match:
            metadata["Governing Law"] = law_match.group(1).strip()
        
        # Extract parties
        between_pattern = r"between\s+(.{2,200}?)\s+and\s+(.{2,200}?)(?:\.|,|\n|hereinafter)"
        between_match = re.search(between_pattern, context, re.IGNORECASE | re.DOTALL)
        if between_match:
            metadata["Parties"] = f"{between_match.group(1).strip()} and {between_match.group(2).strip()}"
        
        return metadata

    @staticmethod
    def _is_legal_question(question: str) -> bool:
        """Check if the question is about legal acts or laws"""
        legal_keywords = [
            "law", "legal", "act", "statute", "legislation", "regulation",
            "governing law", "jurisdiction", "compliance", "applicable law",
            "indian law", "section", "provision", "clause"
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in legal_keywords)


# ------------------------------------------------------------
# Compatibility name
# ------------------------------------------------------------

MockLLMClient = LocalLLMClient


# ------------------------------------------------------------
# Main factory
# ------------------------------------------------------------

def get_llm_client() -> LLMClient:
    """
    Always use the local Ollama-free implementation.

    This intentionally prevents:
        https://ollama.com/api/chat
    from being called.
    """

    return LocalLLMClient()