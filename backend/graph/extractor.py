import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import time
import requests
from config import GROQ_API_KEY, LLM_MODEL
from graph.schema import EMPTY_SAT, EdgeType, NodeType


# ─────────────────────────────────────────────
# Prompt template
# ─────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a legal knowledge graph expert. Extract the structured argument tree from the given legal section.

Return ONLY a valid JSON object with this exact structure — no explanation, no markdown, no extra text:

{{
  "claims": [
    {{"id": "s{section_id}_c1", "text": "the main legal assertion or provision"}}
  ],
  "evidence": [
    {{"id": "s{section_id}_e1", "text": "supporting text, illustrations or explanations"}}
  ],
  "conditions": [
    {{"id": "s{section_id}_cond1", "text": "if/when clause that activates the claim"}}
  ],
  "exceptions": [
    {{"id": "s{section_id}_exc1", "text": "notwithstanding/proviso clause that overrides claim"}}
  ],
  "definitions": [
    {{"id": "s{section_id}_d1", "text": "definition of a legal term"}}
  ],
  "amendments": [
    {{"id": "s{section_id}_am1", "text": "modification to an earlier provision"}}
  ],
  "relations": [
    {{"from": "s{section_id}_c1", "to": "s15", "type": "CITES"}},
    {{"from": "s{section_id}_exc1", "to": "s{section_id}_c1", "type": "OVERRIDES"}}
  ]
}}

Rules:
- Keep all text concise — under 100 words per node
- Only include node types that actually exist in this section
- For relations, "to" can reference either a node id in this section OR another section number like "s15"
- Valid relation types: SUPPORTS, QUALIFIES, OVERRIDES, CITES, DEFINES, AMENDS, ILLUSTRATES
- If nothing meaningful can be extracted return empty lists for all fields
- Return pure JSON only — no ```json``` fences

Legal section to extract from:
Section {section_id} — {title}

{text}"""


# ─────────────────────────────────────────────
# Groq API call
# ─────────────────────────────────────────────

def _call_llm(prompt: str, retries: int = 3) -> str:
    """
    Call Groq API and return raw response text.
    Retries on rate limit or server errors with
    exponential backoff.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type" : "application/json",
    }

    payload = {
        "model"      : LLM_MODEL,
        "messages"   : [{"role": "user", "content": prompt}],
        "temperature": 0.0,    
        "max_tokens" : 1000,
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers = headers,
                json    = payload,
                timeout = 30,
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]

            elif response.status_code == 429:
                # Rate limited — wait and retry
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)

            elif response.status_code >= 500:
                wait = 2 ** attempt
                print(f"    Server error {response.status_code}. Waiting {wait}s...")
                time.sleep(wait)

            else:
                print(f"    API error {response.status_code}: {response.text[:100]}")
                return ""

        except requests.exceptions.Timeout:
            print(f"    Timeout on attempt {attempt + 1}")
            time.sleep(2 ** attempt)

        except requests.exceptions.RequestException as e:
            print(f"    Request failed: {e}")
            return ""

    print(f"    All {retries} attempts failed.")
    return ""


# ─────────────────────────────────────────────
# Parse LLM response into SAT structure
# ─────────────────────────────────────────────

def _parse_response(raw: str, section_id: str) -> dict:
    """
    Parse the raw LLM response into a validated SAT dict.
    Falls back to EMPTY_SAT if parsing fails at any point.
    """
    if not raw or not raw.strip():
        return EMPTY_SAT.copy()

    # Strip any accidental markdown fences the LLM added
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Find the JSON object boundaries
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        print(f"    No JSON found in response for section {section_id}")
        return EMPTY_SAT.copy()

    raw = raw[start:end]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for section {section_id}: {e}")
        return EMPTY_SAT.copy()

    # Validate and sanitize — ensure all expected keys exist
    result = EMPTY_SAT.copy()
    for key in EMPTY_SAT:
        if key in data and isinstance(data[key], list):
            result[key] = data[key]

    # Validate relations — only keep ones with valid edge types
    valid_relations = []
    for rel in result.get("relations", []):
        if (
            isinstance(rel, dict)
            and "from" in rel
            and "to"   in rel
            and "type" in rel
            and rel["type"] in EdgeType.ALL
        ):
            valid_relations.append(rel)

    result["relations"] = valid_relations
    return result


# ─────────────────────────────────────────────
# Main extraction function
# ─────────────────────────────────────────────

def extract_sat(section: dict) -> dict:
    """
    Extract SAT triples from a single section dict
    (as produced by parser.py).

    Returns a SAT dict with claims, evidence, conditions,
    exceptions, definitions, amendments and relations.

    Falls back to EMPTY_SAT on any failure so the pipeline
    never crashes on a bad section.
    """
    section_id = section.get("section_id", "?")
    title      = section.get("title", "")
    text       = section.get("text",  "")

    # Skip sections that are too short to extract anything from
    if len(text.split()) < 20:
        print(f"    Section {section_id} too short — skipping extraction")
        return EMPTY_SAT.copy()

    # Truncate very long sections to stay within token limit
    # Take first 600 words — enough to capture the main provision
    words = text.split()
    if len(words) > 600:
        text = " ".join(words[:600]) + "..."

    prompt = EXTRACTION_PROMPT.format(
        section_id = section_id,
        title      = title,
        text       = text,
    )

    raw    = _call_llm(prompt)
    result = _parse_response(raw, section_id)

    # Count what was extracted for logging
    node_count = sum(
        len(result[k]) for k in result if k != "relations"
    )
    edge_count = len(result["relations"])

    print(f"    Section {section_id}: "
          f"{node_count} nodes, {edge_count} relations extracted")

    return result


# ─────────────────────────────────────────────
# Batch extraction with rate limit protection
# ─────────────────────────────────────────────

def extract_all(sections: list[dict],
                delay: float = 0.5) -> list[tuple[dict, dict]]:
    """
    Extract SAT triples for all sections.
    Returns a list of (section, sat_result) tuples.

    delay — seconds to wait between API calls to
    avoid hitting Groq rate limits. 0.5s is safe
    for the free tier.
    """
    results = []
    total   = len(sections)

    print(f"Extracting SAT triples from {total} sections...")
    print(f"Estimated time: ~{total * delay / 60:.1f} minutes\n")

    for i, section in enumerate(sections):
        section_id = section.get("section_id", "?")
        print(f"  [{i+1}/{total}] Section {section_id} — {section.get('title', '')[:50]}")

        sat = extract_sat(section)
        results.append((section, sat))

        # Polite delay between calls — skip on last item
        if i < total - 1:
            time.sleep(delay)

    successful = sum(
        1 for _, sat in results
        if any(len(sat[k]) > 0 for k in sat if k != "relations")
    )

    print(f"\nExtraction complete:")
    print(f"  Total sections : {total}")
    print(f"  Successful     : {successful}")
    print(f"  Empty/failed   : {total - successful}")

    return results


# ─────────────────────────────────────────────
# Quick test on a single section
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import json as _json

    # Load first 3 sections from processed JSON
    processed_dir = Path(__file__).parent.parent / "data/processed"
    json_files    = list(processed_dir.glob("*.json"))

    if not json_files:
        print("No processed files found. Run parser.py first.")
        sys.exit(1)

    with open(json_files[0]) as f:
        sections = _json.load(f)

    # Test on sections 1, 2, and 14
    test_sections = [s for s in sections if s["section_id"] in ["1", "2", "14"]]

    print(f"Testing extractor on {len(test_sections)} sections...\n")

    for section in test_sections:
        print(f"Section {section['section_id']} — {section['title']}")
        print(f"  Text preview: {section['text'][:80]}...")
        sat = extract_sat(section)
        print(f"  Result:")
        print(f"    claims     : {len(sat['claims'])}")
        print(f"    evidence   : {len(sat['evidence'])}")
        print(f"    conditions : {len(sat['conditions'])}")
        print(f"    exceptions : {len(sat['exceptions'])}")
        print(f"    definitions: {len(sat['definitions'])}")
        print(f"    relations  : {len(sat['relations'])}")
        if sat["relations"]:
            print(f"    sample rel : {sat['relations'][0]}")
        print()