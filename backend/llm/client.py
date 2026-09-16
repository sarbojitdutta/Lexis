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
             max_tokens: int = 1024) -> str:
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not found. Check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    model_to_try = [LLM_MODEL] + [m for m in FALLBACK_MODELS if m != LLM_MODEL]

    for model in model_to_try:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()

                    choice = data["choices"][0]
                    message = choice["message"]
                    content = message.get("content", "")
                    finish_reason = choice.get("finish_reason")

                    print("\n========== GROQ DEBUG ==========")
                    print("Model:", data.get("model"))
                    print("Finish reason:", finish_reason)
                    print("Content:", repr(content))
                    print("Reasoning:", repr(message.get("reasoning")))
                    print("Usage:", data.get("usage"))
                    print("================================\n")

                    if not content and finish_reason == "length":
                        raise Exception(
                            "Groq generation stopped because max_tokens was reached "
                            "before a final answer was produced."
                        )

                    return content
                elif response.status_code == 429:
                    raise Exception("Groq rate limit hit. Wait a moment and try again.")
                else:
                    raise Exception(
                        f"Groq API error {response.status_code}: {response.text[:200]}"
                    )

            except requests.exceptions.Timeout:
                raise Exception("Groq API request timed out.")
            except requests.exceptions.RequestException as e:
                raise Exception(f"Network error calling Groq: {e}")

        except Exception as e:
            if "model_not_found" in str(e) or "404" in str(e):
                continue
            raise

    raise Exception(f"All models failed. Tried: {model_to_try}")


# ─────────────────────────────────────────────
# Conversational retrieval query rewriting
# ─────────────────────────────────────────────

def rewrite_conversational_query(question: str, history: list[dict]) -> str:
    """
    Turn a follow-up question into a standalone retrieval query.

    This is deliberately separate from answer generation: retrieval needs a
    self-contained query so FAISS and the graph search can resolve references
    like 'it', 'that section', or 'what happens if it is violated'.
    """
    if not history:
        return question.strip()

    from llm.prompts import build_rewrite_prompt

    history_text = "\n".join(
        f"{item['role'].upper()}: {item['content']}"
        for item in history[-10:]
    )

    rewritten = call_llm(
        prompt=build_rewrite_prompt(question, history_text),
        system_prompt=(
            "You rewrite legal search queries. Return only the standalone query. "
            "Do not answer the question or invent legal facts."
        ),
        temperature=0.0,
        max_tokens=180,
    ).strip()

    # Defensive fallback if the model returns an empty response.
    return rewritten or question.strip()


# ─────────────────────────────────────────────
# Legal Q&A function
# ─────────────────────────────────────────────

def answer_legal_question(question: str,
                           context: str,
                           history: str = "") -> str:
    """Answer a legal question using retrieved context and conversation history."""
    from llm.prompts import LEGAL_QA_SYSTEM, build_qa_prompt

    prompt = build_qa_prompt(question, context, history)

    return call_llm(
        prompt=prompt,
        system_prompt=LEGAL_QA_SYSTEM,
        temperature=0.1,
        max_tokens=1024,
    )


# ─────────────────────────────────────────────
# Summarizer
# ─────────────────────────────────────────────

def summarize_section(section_text: str,
                      section_id: str) -> str:
    """Summarize a single legal section in plain English."""
    from llm.prompts import build_summary_prompt

    prompt = build_summary_prompt(section_text, section_id)

    return call_llm(
        prompt=prompt,
        temperature=0.2,
        max_tokens=300,
    )


# ─────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────

def check_llm_connection() -> dict:
    """Verify the Groq API is reachable and the API key is valid."""
    try:
        response = call_llm(
            prompt="Reply with just the word: connected",
            temperature=0.0,
            max_tokens=50,
        )
        return {
            "status": "connected",
            "model": LLM_MODEL,
            "response": response.strip(),
        }
    except Exception as e:
        return {
            "status": "error",
            "model": LLM_MODEL,
            "error": str(e),
        }


if __name__ == "__main__":
    print("Testing LLM connection...\n")
    result = check_llm_connection()
    for k, v in result.items():
        print(f"  {k}: {v}")
