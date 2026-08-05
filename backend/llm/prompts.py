
LEGAL_QA_SYSTEM = """You are Lexis, an expert Indian legal assistant.
You answer questions based strictly on the provided legal context
from Indian laws and acts.

Your rules:
- Answer only from the provided context — never from general knowledge
- Always cite the section number when making a legal statement
- If the context does not contain enough information say so clearly
- Explain legal terms in plain English after using them
- Keep answers concise and structured
- If there is an exception or condition that affects the answer always mention it
- Never give personal legal advice — always recommend consulting a lawyer for specific cases"""


# ─────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────

def build_qa_prompt(question: str, context: str) -> str:
    """
    Build the full prompt for legal Q&A.
    """
    return f"""Use the following legal context from Indian law to answer the question.

LEGAL CONTEXT:
{context}

QUESTION:
{question}

ANSWER (cite section numbers, explain exceptions if any):"""


def build_summary_prompt(section_text: str,
                         section_id: str) -> str:
    """
    Build prompt for summarizing a single section.
    """
    return f"""Summarize Section {section_id} of this Indian law in 2-3 plain English sentences.
Focus on what the section does and who it applies to.

Section text:
{section_text[:1000]}

Summary:"""


def build_keyword_prompt(query: str) -> str:
    """
    Build prompt for extracting legal keywords
    from a user query.
    Used to improve graph keyword search.
    """
    return f"""Extract 3-5 key legal terms from this question about Indian law.
Return only the terms separated by commas, nothing else.

Question: {query}

Legal terms:"""