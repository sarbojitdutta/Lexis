import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from config import TOP_K_VECTOR, TOP_K_GRAPH, MAX_CONTEXT
from retrieval.vector_search import search  as vector_search
from retrieval.vector_search import get_section_ids
from retrieval.graph_search  import search  as graph_search
from retrieval.graph_search  import get_graph_texts
from retrieval.vector_search import meta


WEIGHTS = {
    "vector"    : 1.0,   # direct semantic match — highest priority
    "exception" : 0.95,  # exceptions are legally critical
    "definition": 0.85,  # definitions clarify meaning
    "traversal" : 0.75,  # graph neighbours
    "keyword"   : 0.65,  # keyword matched nodes
}

# Node types that should always be included
# regardless of their score
PRIORITY_TYPES = ["exception", "amendment"]

def merge(query: str,
          k_vector: int = None,
          k_graph : int = None) -> list[dict]:
    """
    Run both vector search and graph search,
    merge the results, deduplicate, rank by
    relevance and return a unified list.

    Each result has:
    - text        : the content to send to LLM
    - section_id  : which section it came from
    - source_type : 'vector' or 'graph'
    - score       : relevance score 0-1
    - title       : section title
    - metadata    : all other fields
    """
    k_vector = k_vector or TOP_K_VECTOR
    k_graph  = k_graph  or TOP_K_GRAPH

    # ── Step 1 — vector search ──
    vector_results = vector_search(query, k=k_vector)
    section_ids    = [
        r["section_id"] for r in vector_results
        if r.get("section_id")
    ]

    # ── Step 2 — graph search ──
    graph_results = graph_search(
        section_ids, query=query
    )

    # ── Step 3 — normalize vector results ──
    normalized = []
    for r in vector_results:
        normalized.append({
            "text"       : r.get("text", ""),
            "section_id" : r.get("section_id", ""),
            "title"      : r.get("title", ""),
            "source"     : r.get("source", ""),
            "source_type": "vector",
            "score"      : r.get("score", 0.0) * WEIGHTS["vector"],
            "has_exception"  : r.get("has_exception",   False),
            "has_proviso"    : r.get("has_proviso",      False),
            "has_definition" : r.get("has_definition",  False),
            "has_amendment"  : r.get("has_amendment",   False),
            "cross_references": r.get("cross_references", []),
        })
    meta_lookup = {
        m["section_id"]: m for m in meta
    }

    # ── Step 4 — normalize graph results ──
    for r in graph_results:
        reason = r.get("reason", "traversal")
        weight = WEIGHTS.get(reason, WEIGHTS["traversal"])
        section_id = r.get("section_id", "")
        meta_entry = meta_lookup.get(section_id, {})
        normalized.append({
            "text"       : r.get("text", ""),
            "section_id" : r.get("section_id", ""),
            "title"      : r.get("title", ""),
            "source"     : r.get("source", ""),
            "source_type": f"graph_{reason}",
            "score"      : weight,
            "has_exception"  : r.get("type") == "exception",
            "has_proviso"    : False,
            "has_definition" : r.get("type") == "definition",
            "has_amendment"  : r.get("type") == "amendment",
            "cross_references": [],
        })

    # ── Step 5 — deduplicate by text content ──
    seen_texts  = set()
    seen_sections = set()
    deduped     = []

    # Always include priority types first
    priority = [
        r for r in normalized
        if r.get("has_exception") or r.get("has_amendment")
    ]
    regular  = [
        r for r in normalized
        if not r.get("has_exception") and not r.get("has_amendment")
    ]

    for r in priority + regular:
        text = r.get("text", "").strip()

        # Skip empty text
        if not text or len(text.split()) < 10:
            continue

        # Skip duplicate text
        text_key = text[:100]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        deduped.append(r)

    # ── Step 6 — sort by score ──
    deduped.sort(key=lambda x: x["score"], reverse=True)

    return deduped


def build_context(query: str,
                  k_vector: int = None,
                  k_graph : int = None) -> tuple[str, list[dict]]:
    """
    Run the full retrieval pipeline and build
    a single context string ready to be injected
    into the LLM prompt.

    Returns:
    - context_str : text to put in the prompt
    - results     : full result list for citations

    Trims context to MAX_CONTEXT words so the
    LLM prompt stays within token limits.
    """
    results = merge(query, k_vector=k_vector, k_graph=k_graph)

    if not results:
        return "No relevant legal context found.", []

    parts       = []
    word_count  = 0
    used_results = []

    for r in results:
        text = r.get("text", "").strip()
        if not text:
            continue

        words = text.split()

        # Stop adding if we would exceed the word limit
        if word_count + len(words) > MAX_CONTEXT:
            # Try to fit a trimmed version
            remaining = MAX_CONTEXT - word_count
            if remaining > 50:
                text  = " ".join(words[:remaining]) + "..."
                parts.append(_format_chunk(r, text))
                used_results.append(r)
            break

        parts.append(_format_chunk(r, text))
        used_results.append(r)
        word_count += len(words)

    context_str = "\n\n".join(parts)
    return context_str, used_results


def _format_chunk(result: dict, text: str) -> str:
    """
    Format a single result chunk with its
    section label for the LLM context.
    """
    section_id   = result.get("section_id", "")
    title        = result.get("title", "")
    source_type  = result.get("source_type", "")

    # Add a label so the LLM can cite the section
    if section_id and title:
        label = f"[Section {section_id} — {title}]"
    elif section_id:
        label = f"[Section {section_id}]"
    else:
        label = f"[Legal Context — {source_type}]"

    return f"{label}\n{text}"


def build_citations(results: list[dict]) -> list[dict]:
    """
    Build a clean list of citations from the
    merged results for the API response.

    The frontend uses this to show source
    references alongside the LLM answer.
    """
    citations    = []
    seen_sections = set()

    for r in results:
        sid = r.get("section_id", "")
        if not sid or sid in seen_sections:
            continue
        seen_sections.add(sid)

        citations.append({
            "section_id" : sid,
            "title"      : r.get("title", ""),
            "source"     : r.get("source", ""),
            "source_type": r.get("source_type", ""),
            "score"      : round(r.get("score", 0.0), 4),
        })

    return citations


if __name__ == "__main__":

    test_queries = [
        "Can a contract made under coercion be enforced",
        "What is free consent",
        "compensation for breach of contract",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("=" * 60)

        # Full merge
        results = merge(query)
        print(f"Total merged results : {len(results)}")

        vector_count = sum(
            1 for r in results if r["source_type"] == "vector"
        )
        graph_count  = len(results) - vector_count
        print(f"  From vector search : {vector_count}")
        print(f"  From graph search  : {graph_count}")

        print(f"\nTop 5 results:")
        for i, r in enumerate(results[:5]):
            print(f"  [{i+1}] score={r['score']:.3f} "
                  f"type={r['source_type']:20s} "
                  f"section={r['section_id']:5s} "
                  f"text={r['text'][:50]}...")

        # Build context
        context, used = build_context(query)
        word_count    = len(context.split())
        print(f"\nContext built:")
        print(f"  Word count  : {word_count} / {MAX_CONTEXT}")
        print(f"  Chunks used : {len(used)}")
        print(f"\nContext preview:")
        print(context[:400] + "..." if len(context) > 400 else context)

        # Citations
        citations = build_citations(used)
        print(f"\nCitations ({len(citations)}):")
        for c in citations:
            print(f"  Section {c['section_id']} — "
                  f"{c['title']} (score: {c['score']})")