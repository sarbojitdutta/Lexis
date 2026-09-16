LEGAL_QA_SYSTEM = """You are Lexis, an expert Indian legal assistant.
You answer questions based strictly on the provided legal context
from Indian laws and acts.

Your rules:
- The LEGAL CONTEXT is the only source of legal facts. Never use general knowledge.
- CONVERSATION HISTORY is only for resolving references such as 'it', 'that section', or 'the exception'. Never treat historical assistant claims as legal evidence.
- Always cite the section number when making a legal statement.
- If the legal context does not contain enough information, say so clearly.
- Explain legal terms in plain English after using them.
- Keep answers concise and structured.
- If an exception or condition affects the answer, always mention it.
- Never give personal legal advice; recommend consulting a lawyer for a specific case."""


# ─────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────

def build_qa_prompt(question: str, context: str, history: str = "") -> str:
    """
    Build the grounded legal Q&A prompt.

    History helps the model understand conversational references, while
    retrieved legal context remains the only source of legal facts.
    """
    history_block = history.strip() or "No previous conversation."

    return f"""Use the following retrieved legal context from Indian law to answer the current question.

CONVERSATION HISTORY (reference only):
{history_block}

LEGAL CONTEXT (source of truth):
{context}

CURRENT QUESTION:
{question}

ANSWER (cite section numbers and explain relevant exceptions):"""


def build_rewrite_prompt(question: str, history: str) -> str:
    """Rewrite a conversational follow-up into a standalone legal search query."""
    return f"""Rewrite the current user question into a single standalone search query for retrieving relevant Indian legal provisions.

Use the conversation history only to resolve references such as 'it', 'that section', 'this rule', or 'what happens then'.
Do not add legal facts that are not present in the history.
Preserve names of laws, sections, parties, legal concepts, and conditions exactly when they appear.
If the current question is already standalone, return it unchanged.
Return ONLY the rewritten query, with no explanation, quotes, or prefix.

CONVERSATION HISTORY:
{history}

CURRENT QUESTION:
{question}

STANDALONE SEARCH QUERY:"""


def build_summary_prompt(section_text: str,
                         section_id: str) -> str:
    """Build prompt for summarizing a single legal section."""
    return f"""Summarize Section {section_id} of this Indian law in 2-3 plain English sentences.
Focus on what the section does and who it applies to.

Section text:
{section_text[:1000]}

Summary:"""


def build_keyword_prompt(query: str) -> str:
    """Build prompt for extracting legal keywords from a user query."""
    return f"""Extract 3-5 key legal terms from this question about Indian law.
Return only the terms separated by commas, nothing else.

Question: {query}

Legal terms:"""
