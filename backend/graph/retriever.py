
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import sqlite3
import networkx as nx
from config import GRAPH_DB
from graph.schema import EdgeType, NodeType
from graph.builder import load_graph




try:
    G = load_graph()
    print(f"Graph loaded — {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges")
except FileNotFoundError:
    G = nx.DiGraph()
    print("Warning: graph.db not found. "
          "Run ingestion pipeline first.")



def get_neighbours(node_id: str,
                   depth: int = 2,
                   relation_filter: list[str] = None) -> list[dict]:
    if not G.has_node(node_id):
        return []

    visited = set()
    results = []
    queue   = [(node_id, 0)]

    while queue:
        current_id, current_depth = queue.pop(0)

        if current_id in visited:
            continue
        visited.add(current_id)

        if current_depth > depth:
            continue

        # Get node data
        node_data = G.nodes.get(current_id, {})
        if current_id != node_id and node_data:
            results.append({
                "node_id"   : current_id,
                "type"      : node_data.get("type", ""),
                "text"      : node_data.get("text", ""),
                "section_id": node_data.get("section_id", ""),
                "depth"     : current_depth,
            })

        # Traverse outgoing edges
        for _, neighbour_id, edge_data in G.out_edges(current_id, data=True):
            relation = edge_data.get("relation", "")
            if relation_filter and relation not in relation_filter:
                continue
            if neighbour_id not in visited:
                queue.append((neighbour_id, current_depth + 1))

        # Traverse incoming edges too
        # (a section that cites us is also relevant)
        for neighbour_id, _, edge_data in G.in_edges(current_id, data=True):
            relation = edge_data.get("relation", "")
            if relation_filter and relation not in relation_filter:
                continue
            if neighbour_id not in visited:
                queue.append((neighbour_id, current_depth + 1))

    return results


def get_section_node(section_id: str) -> dict:
    """
    Get the anchor node for a section by its
    section number e.g. "14" → node id "s14"
    """
    node_id  = f"s{section_id}"
    node_data = G.nodes.get(node_id, {})

    if not node_data:
        return {}

    return {
        "node_id"   : node_id,
        "type"      : node_data.get("type", ""),
        "text"      : node_data.get("text", ""),
        "section_id": node_data.get("section_id", ""),
    }


def get_related_sections(section_ids: list[str],
                         depth: int = 2) -> list[dict]:

    all_results = []
    seen_ids    = set(f"s{sid}" for sid in section_ids)

    for section_id in section_ids:
        node_id   = f"s{section_id}"
        neighbours = get_neighbours(node_id, depth=depth)

        for neighbour in neighbours:
            nid = neighbour["node_id"]
            if nid not in seen_ids:
                seen_ids.add(nid)
                all_results.append(neighbour)

    # Sort by depth — closer nodes are more relevant
    all_results.sort(key=lambda x: x["depth"])

    return all_results


def get_exceptions(section_id: str) -> list[dict]:
    """
    Find all exception/override nodes for a section.
    Critical for legal accuracy — missing an exception
    can make an answer completely wrong.
    """
    node_id = f"s{section_id}"
    return get_neighbours(
        node_id,
        depth            = 1,
        relation_filter  = [EdgeType.OVERRIDES]
    )


def get_definitions(section_id: str) -> list[dict]:
    """
    Find all definition nodes connected to a section.
    Useful for understanding what terms in the section mean.
    """
    node_id = f"s{section_id}"
    return get_neighbours(
        node_id,
        depth           = 2,
        relation_filter = [EdgeType.DEFINES, EdgeType.CITES]
    )


def get_citations(section_id: str) -> list[dict]:
    """
    Find all sections that this section explicitly cites
    and all sections that cite this section.
    """
    node_id = f"s{section_id}"
    return get_neighbours(
        node_id,
        depth           = 1,
        relation_filter = [EdgeType.CITES]
    )


def get_amendments(section_id: str) -> list[dict]:
    
    node_id = f"s{section_id}"
    return get_neighbours(
        node_id,
        depth           = 1,
        relation_filter = [EdgeType.AMENDS]
    )


def search_nodes_by_keyword(keywords: list[str],
                             node_types: list[str] = None,
                             limit: int = 10) -> list[dict]:
    
    if not GRAPH_DB.exists():
        return []

    con     = sqlite3.connect(GRAPH_DB)
    results = []

    try:
        for keyword in keywords[:5]:   # cap at 5 keywords
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                query = f"""
                    SELECT id, type, text, section_id
                    FROM nodes
                    WHERE text LIKE ?
                    AND type IN ({placeholders})
                    LIMIT ?
                """
                params = [f"%{keyword}%"] + node_types + [limit]
            else:
                query = """
                    SELECT id, type, text, section_id
                    FROM nodes
                    WHERE text LIKE ?
                    LIMIT ?
                """
                params = [f"%{keyword}%", limit]

            rows = con.execute(query, params).fetchall()

            for node_id, ntype, text, section_id in rows:
                results.append({
                    "node_id"   : node_id,
                    "type"      : ntype,
                    "text"      : text,
                    "section_id": section_id,
                    "depth"     : 0,
                })

    finally:
        con.close()

    # Deduplicate by node_id
    seen    = set()
    unique  = []
    for r in results:
        if r["node_id"] not in seen:
            seen.add(r["node_id"])
            unique.append(r)

    return unique[:limit]


def get_full_context(section_id: str) -> dict:

    return {
        "section"   : get_section_node(section_id),
        "exceptions": get_exceptions(section_id),
        "definitions": get_definitions(section_id),
        "citations" : get_citations(section_id),
        "amendments": get_amendments(section_id),
    }



# Entry point — test retrieval
if __name__ == "__main__":

    print("\n--- Test 1: get neighbours of Section 14 ---\n")
    neighbours = get_neighbours("s14", depth=2)
    print(f"Found {len(neighbours)} neighbours:")
    for n in neighbours:
        print(f"  [{n['depth']} hop] {n['node_id']} "
              f"({n['type']}) — {n['text'][:60]}...")

    print("\n--- Test 2: get related sections ---\n")
    related = get_related_sections(["14", "19"], depth=2)
    print(f"Found {len(related)} related nodes for sections 14 and 19:")
    for r in related:
        print(f"  {r['node_id']} ({r['type']}) "
              f"— {r['text'][:60]}...")

    print("\n--- Test 3: get exceptions for Section 19 ---\n")
    exceptions = get_exceptions("19")
    print(f"Found {len(exceptions)} exception nodes:")
    for e in exceptions:
        print(f"  {e['node_id']} — {e['text'][:80]}...")

    print("\n--- Test 4: keyword search ---\n")
    results = search_nodes_by_keyword(["coercion", "consent"])
    print(f"Found {len(results)} nodes matching keywords:")
    for r in results:
        print(f"  {r['node_id']} ({r['type']}) "
              f"— {r['text'][:60]}...")

    print("\n--- Test 5: full context for Section 14 ---\n")
    context = get_full_context("14")
    for key, value in context.items():
        if isinstance(value, list):
            print(f"  {key}: {len(value)} items")
        else:
            print(f"  {key}: {value.get('node_id', 'not found')}")