import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import sqlite3
from config import GRAPH_DB
from retrieval.vector_search import get_section_ids
from graph.retriever import (
    get_related_sections,
    get_exceptions,
    get_definitions,
    search_nodes_by_keyword,
    get_full_context
)


def search(section_ids: list[str],
           query: str      = "",
           depth: int      = 2) -> list[dict]:

    if not section_ids:
        return []

    results    = []
    seen_ids   = set()

    # ── 1. Graph traversal from vector search results ──
    related = get_related_sections(section_ids, depth=depth)
    for node in related:
        nid = node["node_id"]
        if nid not in seen_ids:
            seen_ids.add(nid)
            results.append(node)

    # ── 2. Explicitly fetch exceptions for each section ──
    # Exceptions are the most legally critical nodes —
    # missing one can make an answer completely wrong
    for sid in section_ids:
        exceptions = get_exceptions(sid)
        for node in exceptions:
            nid = node["node_id"]
            if nid not in seen_ids:
                seen_ids.add(nid)
                node["reason"] = "exception"
                results.append(node)

    # ── 3. Fetch definitions for each section ──
    # Definitions clarify what terms in the section mean
    for sid in section_ids:
        definitions = get_definitions(sid)
        for node in definitions:
            nid = node["node_id"]
            if nid not in seen_ids:
                seen_ids.add(nid)
                node["reason"] = "definition"
                results.append(node)

    # ── 4. Keyword search inside graph ──
    # Catches nodes that are related by keywords
    # but not connected by edges yet
    if query:
        keywords = _extract_keywords(query)
        keyword_results = search_nodes_by_keyword(
            keywords, limit=5
        )
        for node in keyword_results:
            nid = node["node_id"]
            if nid not in seen_ids:
                seen_ids.add(nid)
                node["reason"] = "keyword"
                results.append(node)

    return results

def _extract_keywords(query: str) -> list[str]:
    """
    Extract meaningful keywords from the query
    for graph keyword search.
    Filters out common stop words.
    """
    stop_words = {
        "what", "is", "are", "the", "a", "an",
        "in", "of", "to", "and", "or", "for",
        "can", "how", "when", "where", "who",
        "does", "do", "be", "been", "was", "were",
        "will", "would", "should", "could", "may",
        "might", "shall", "under", "if", "that",
        "this", "with", "by", "from", "it", "its"
    }

    words    = query.lower().split()
    keywords = [
        w.strip("?.,!") for w in words
        if w.strip("?.,!") not in stop_words
        and len(w.strip("?.,!")) > 3
    ]

    return keywords[:5]   # cap at 5 keywords


def get_graph_texts(section_ids: list[str],
                    query: str = "") -> list[str]:
    """
    Convenience function that returns just the
    text content from graph search results.

    Used by merger.py to combine with vector
    search text results.
    """
    results = search(section_ids, query=query)
    texts   = []

    for node in results:
        text = node.get("text", "").strip()
        if text and len(text.split()) > 10:
            texts.append(text)

    return texts


def get_section_context(section_id: str) -> str:

    context = get_full_context(section_id)
    parts   = []

    # Main section text
    section = context.get("section", {})
    if section.get("text"):
        parts.append(f"Section {section_id}:\n{section['text']}")

    # Exceptions — most important
    exceptions = context.get("exceptions", [])
    if exceptions:
        parts.append("Exceptions/Overrides:")
        for e in exceptions:
            if e.get("text"):
                parts.append(f"  - {e['text']}")

    # Definitions
    definitions = context.get("definitions", [])
    if definitions:
        parts.append("Related Definitions:")
        for d in definitions[:3]:   # top 3 only
            if d.get("text"):
                parts.append(f"  - {d['text']}")

    # Citations
    citations = context.get("citations", [])
    if citations:
        cited_ids = [
            c.get("section_id", "") for c in citations
            if c.get("section_id")
        ]
        if cited_ids:
            parts.append(f"References: Sections {', '.join(cited_ids)}")

    return "\n".join(parts)

def graph_search_stats() -> dict:
    """
    Return basic stats about what the graph
    search found for debugging purposes.
    """
    if not GRAPH_DB.exists():
        return {"status": "graph not built"}

    con = sqlite3.connect(GRAPH_DB)
    try:
        node_count = con.execute(
            "SELECT COUNT(*) FROM nodes"
        ).fetchone()[0]

        edge_count = con.execute(
            "SELECT COUNT(*) FROM edges"
        ).fetchone()[0]

        return {
            "status"    : "ready",
            "nodes"     : node_count,
            "edges"     : edge_count,
            "db_path"   : str(GRAPH_DB),
        }
    finally:
        con.close()


if __name__ == "__main__":
    
    test_queries = [
        "Can a contract made under coercion be enforced",
        "What is free consent in a contract",
        "compensation for breach of contract",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 55)

        # Step 1 — vector search gives section IDs
        section_ids = get_section_ids(query, k=4)
        print(f"Vector search found sections: {section_ids}")

        # Step 2 — graph search expands those IDs
        graph_results = search(section_ids, query=query)
        print(f"Graph search found {len(graph_results)} additional nodes:")

        for r in graph_results[:5]:
            reason = r.get("reason", "traversal")
            print(f"  [{reason}] {r['node_id']} "
                  f"({r['type']}) — {r['text'][:70]}...")

        # Step 3 — get text content
        texts = get_graph_texts(section_ids, query=query)
        print(f"\nGraph texts: {len(texts)} text blocks retrieved")

        # Step 4 — section context
        if section_ids:
            print(f"\nFull context for Section {section_ids[0]}:")
            ctx = get_section_context(section_ids[0])
            print(ctx[:300] + "..." if len(ctx) > 300 else ctx)

    print("\n--- Graph search stats ---")
    stats = graph_search_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")