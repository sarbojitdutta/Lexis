import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import requests
from config import GROQ_API_KEY, LLM_MODEL

FALLBACK_MODELS = [
    "openai/gpt-oss-20b"
]


def call_llm(prompt: str,
             system_prompt: str = None,
             temperature: float = 0.1,
             max_tokens: int    = 1024) -> str:
    
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not found. "
            "Check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type" : "application/json",
    }

    model_to_try = [LLM_MODEL] + [m for m in FALLBACK_MODELS if m != LLM_MODEL]

    for model in model_to_try:
        try:
            messages = []
            if system_prompt:
                messages.append({
                    "role"   : "system",
                    "content": system_prompt
                })
            messages.append({
                "role"   : "user",
                "content": prompt
            })
        
            payload = {
                "model"      : model,
                "messages"   : messages,
                "temperature": temperature,
                "max_tokens" : max_tokens,
            }
        
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers = headers,
                    json    = payload,
                    timeout = 60,
                )
        
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
        
                elif response.status_code == 429:
                    raise Exception(
                        "Groq rate limit hit. Wait a moment and try again."
                    )
        
                else:
                    raise Exception(
                        f"Groq API error {response.status_code}: "
                        f"{response.text[:200]}"
                    )
        
            except requests.exceptions.Timeout:
                raise Exception("Groq API request timed out.")
        
            except requests.exceptions.RequestException as e:
                raise Exception(f"Network error calling Groq: {e}")
            
        except Exception as e:
            if "model_not_found" in str(e) or "404" in str(e):
                continue
            raise
    
    raise Exception(
        f"All models failed. Tried: {model_to_try}"
    )         


    # Build messages list
    

# ─────────────────────────────────────────────
# Legal Q&A function
# ─────────────────────────────────────────────

def answer_legal_question(question: str,
                          context: str) -> str:
    """
    Answer a legal question given retrieved context.
    This is the main function called by query.py
    during the online pipeline.

    question → user's question
    context  → merged context from merger.py
    """
    from llm.prompts import LEGAL_QA_SYSTEM, build_qa_prompt

    system = LEGAL_QA_SYSTEM
    prompt = build_qa_prompt(question, context)

    return call_llm(
        prompt        = prompt,
        system_prompt = system,
        temperature   = 0.1,
        max_tokens    = 1024,
    )


# ─────────────────────────────────────────────
# Summarizer
# ─────────────────────────────────────────────

def summarize_section(section_text: str,
                      section_id: str) -> str:
    """
    Summarize a single legal section in plain English.
    Useful for the document inspection endpoint.
    """
    from llm.prompts import build_summary_prompt

    prompt = build_summary_prompt(section_text, section_id)

    return call_llm(
        prompt      = prompt,
        temperature = 0.2,
        max_tokens  = 300,
    )


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

def check_llm_connection() -> dict:
    """
    Verify the Groq API is reachable and the
    API key is valid.
    Used by GET /api/health endpoint.
    """
    try:
        response = call_llm(
            prompt     = "Reply with just the word: connected",
            temperature= 0.0,
            max_tokens = 10,
        )
        return {
            "status" : "connected",
            "model"  : LLM_MODEL,
            "response": response.strip(),
        }
    except Exception as e:
        return {
            "status": "error",
            "model" : LLM_MODEL,
            "error" : str(e),
        }


# ─────────────────────────────────────────────
# Entry point — test LLM connection
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("Testing LLM connection...\n")

    # Test 1 — health check
    print("--- Test 1: Health check ---")
    result = check_llm_connection()
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Test 2 — simple legal question
    print("\n--- Test 2: Simple legal question ---")
    context = """
    [Section 10 — What agreements are contracts]
    All agreements are contracts if they are made by the
    free consent of parties competent to contract, for a
    lawful consideration and with a lawful object.

    [Section 11 — Who are competent to contract]
    Every person is competent to contract who is of the
    age of majority according to the law to which he is
    subject, and who is of sound mind, and is not
    disqualified from contracting by any law.
    """

    question = "Who can enter into a valid contract?"
    print(f"Question: {question}")
    print(f"Context preview: {context[:100]}...")

    from llm.prompts import LEGAL_QA_SYSTEM, build_qa_prompt
    answer = answer_legal_question(question, context)
    print(f"\nAnswer:\n{answer}")