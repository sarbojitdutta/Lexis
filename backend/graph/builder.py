
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import sqlite3
import networkx as nx
from typing import Optional

from config import GRAPH_DB
from graph.schema import (
    NodeType, EdgeType,
    CREATE_NODES_TABLE,
    CREATE_EDGES_TABLE,
    CREATE_INDEXES,
    EMPTY_SAT
)


# ─────────────────────────────────────────────
# Database setup
# ─────────────────────────────────────────────

def init_db() -> None:
    """
    Create SQLite database and tables if they
    don't already exist.
    """
    GRAPH_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(GRAPH_DB)
    try:
        con.execute(CREATE_NODES_TABLE)
        con.execute(CREATE_EDGES_TABLE)
        for index_sql in CREATE_INDEXES:
            con.execute(index_sql)
        con.commit()
    finally:
        con.close()


# ─────────────────────────────────────────────
# Node helpers
# ─────────────────────────────────────────────

def _insert_node(con: sqlite3.Connection, node_id: str,
                 node_type: str, text: str,
                 section: dict) -> None:
    """
    Insert a single node into SQLite.
    Ignores if node_id already exists — safe to
    call multiple times on the same node.
    """
    con.execute("""
        INSERT OR IGNORE INTO nodes
            (id, type, text, section_id, source, title, part, chapter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        node_id,
        node_type,
        text[:1000],                      # cap at 1000 chars
        section.get("section_id", ""),
        section.get("source",     ""),
        section.get("title",      ""),
        section.get("part",       ""),
        section.get("chapter",    ""),
    ))


def _insert_section_node(con: sqlite3.Connection,
                         section: dict) -> str:
    """
    Every section itself becomes a CLAIM node
    in the graph — this is the anchor node that
    all extracted sub-nodes and cross-reference
    edges connect to.

    Returns the node id.
    """
    node_id = f"s{section['section_id']}"
    _insert_node(
        con       = con,
        node_id   = node_id,
        node_type = NodeType.CLAIM,
        text      = section.get("text", "")[:500],
        section   = section,
    )
    return node_id


# ─────────────────────────────────────────────
# Edge helpers
# ─────────────────────────────────────────────

def _insert_edge(con: sqlite3.Connection,
                 src: str, dst: str,
                 relation: str, source: str) -> None:
    """
    Insert a single edge into SQLite.
    Skips duplicate edges silently.
    """
    # Check for duplicate before inserting
    exists = con.execute("""
        SELECT 1 FROM edges
        WHERE src=? AND dst=? AND relation=?
    """, (src, dst, relation)).fetchone()

    if not exists:
        con.execute("""
            INSERT INTO edges (src, dst, relation, source)
            VALUES (?, ?, ?, ?)
        """, (src, dst, relation, source))


# ─────────────────────────────────────────────
# Cross-reference edges
# ─────────────────────────────────────────────

def _add_cross_reference_edges(con: sqlite3.Connection,
                                section: dict,
                                anchor_id: str) -> int:
    """
    Use the cross_references list from parser.py
    to add CITES edges between sections.
    These are explicit references found in the
    text like 'as defined in section 15'.

    Returns number of edges added.
    """
    count = 0
    for ref in section.get("cross_references", []):
        dst = f"s{ref}"
        _insert_edge(
            con      = con,
            src      = anchor_id,
            dst      = dst,
            relation = EdgeType.CITES,
            source   = section.get("source", "")
        )
        count += 1
    return count


# ─────────────────────────────────────────────
# Legal marker edges
# ─────────────────────────────────────────────

def _add_marker_edges(con: sqlite3.Connection,
                      section: dict,
                      anchor_id: str) -> None:
    """
    Use the boolean flags from parser.py
    (has_proviso, has_exception etc.) to add
    structural edges automatically without
    needing LLM extraction.

    This is a fast heuristic layer that runs
    on top of the LLM extraction layer.
    """
    source = section.get("source", "")

    # Sections with provisos qualify their own claim
    if section.get("has_proviso"):
        proviso_id = f"{anchor_id}_proviso"
        _insert_node(
            con       = con,
            node_id   = proviso_id,
            node_type = NodeType.CONDITION,
            text      = "Proviso clause detected in this section",
            section   = section,
        )
        _insert_edge(con, proviso_id, anchor_id,
                     EdgeType.QUALIFIES, source)

    # Sections with exceptions override their own claim
    if section.get("has_exception"):
        exception_id = f"{anchor_id}_exception"
        _insert_node(
            con       = con,
            node_id   = exception_id,
            node_type = NodeType.EXCEPTION,
            text      = "Exception/notwithstanding clause detected",
            section   = section,
        )
        _insert_edge(con, exception_id, anchor_id,
                     EdgeType.OVERRIDES, source)

    # Sections with definitions define their anchor
    if section.get("has_definition"):
        def_id = f"{anchor_id}_def"
        _insert_node(
            con       = con,
            node_id   = def_id,
            node_type = NodeType.DEFINITION,
            text      = "Definition clause detected in this section",
            section   = section,
        )
        _insert_edge(con, def_id, anchor_id,
                     EdgeType.DEFINES, source)

    # Sections with amendments modify their anchor
    if section.get("has_amendment"):
        amend_id = f"{anchor_id}_amend"
        _insert_node(
            con       = con,
            node_id   = amend_id,
            node_type = NodeType.AMENDMENT,
            text      = "Amendment clause detected in this section",
            section   = section,
        )
        _insert_edge(con, amend_id, anchor_id,
                     EdgeType.AMENDS, source)


# ─────────────────────────────────────────────
# SAT triple insertion
# ─────────────────────────────────────────────

def _add_sat_nodes(con: sqlite3.Connection,
                   sat: dict,
                   section: dict) -> dict[str, str]:
    """
    Insert all nodes from a SAT extraction result.
    Returns a mapping of node_id → node_id for
    use when inserting edges.
    """
    node_map = {}

    # Map SAT key to NodeType
    type_map = {
        "claims"    : NodeType.CLAIM,
        "evidence"  : NodeType.EVIDENCE,
        "conditions": NodeType.CONDITION,
        "exceptions": NodeType.EXCEPTION,
        "definitions": NodeType.DEFINITION,
        "amendments": NodeType.AMENDMENT,
    }

    for key, node_type in type_map.items():
        for node in sat.get(key, []):
            node_id = node.get("id", "")
            text    = node.get("text", "")
            if not node_id or not text:
                continue
            _insert_node(con, node_id, node_type, text, section)
            node_map[node_id] = node_id

    return node_map


def _add_sat_edges(con: sqlite3.Connection,
                   sat: dict,
                   section: dict) -> int:
    """
    Insert all edges from a SAT extraction result.
    Returns number of edges added.
    """
    count  = 0
    source = section.get("source", "")

    for rel in sat.get("relations", []):
        src      = rel.get("from", "")
        dst      = rel.get("to",   "")
        relation = rel.get("type", "")

        if not src or not dst or not relation:
            continue

        if relation not in EdgeType.ALL:
            continue

        # Normalize dst — if it looks like a section
        # number like "s15" or "15" make it consistent
        if dst.isdigit():
            dst = f"s{dst}"
        elif not dst.startswith("s"):
            dst = f"s{dst}"

        _insert_edge(con, src, dst, relation, source)
        count += 1

    return count


# ─────────────────────────────────────────────
# NetworkX graph builder
# ─────────────────────────────────────────────

def _build_networkx_graph(con: sqlite3.Connection) -> nx.DiGraph:
    """
    Load the full SQLite graph into a NetworkX
    DiGraph for in-memory traversal.
    Called once after all sections are processed.
    """
    G = nx.DiGraph()

    # Add all nodes
    rows = con.execute(
        "SELECT id, type, text, section_id FROM nodes"
    ).fetchall()
    for node_id, ntype, text, section_id in rows:
        G.add_node(node_id,
                   type=ntype,
                   text=text,
                   section_id=section_id)

    # Add all edges
    rows = con.execute(
        "SELECT src, dst, relation FROM edges"
    ).fetchall()
    for src, dst, relation in rows:
        # Only add edge if both nodes exist
        if G.has_node(src) and G.has_node(dst):
            G.add_edge(src, dst, relation=relation)

    return G


# ─────────────────────────────────────────────
# Main builder function
# ─────────────────────────────────────────────

def build_graph(sections: list[dict],
                sat_results: list[tuple[dict, dict]]) -> nx.DiGraph:
    """
    Build the complete SAT graph from:
    - sections: list of section dicts from parser.py
    - sat_results: list of (section, sat) tuples from extractor.py

    Saves everything to SQLite and returns a
    NetworkX DiGraph for immediate use.
    """
    init_db()
    con = sqlite3.connect(GRAPH_DB)

    total_nodes = 0
    total_edges = 0

    try:
        # Build a lookup for sections by section_id
        section_lookup = {
            s["section_id"]: s for s in sections
        }

        print(f"Building graph from {len(sat_results)} sections...")

        for section, sat in sat_results:
            section_id = section.get("section_id", "?")

            # 1 — Create anchor node for this section
            anchor_id = _insert_section_node(con, section)
            total_nodes += 1

            # 2 — Add cross-reference edges from parser
            #     (these come from explicit "section X"
            #     mentions found during parsing)
            ref_count = _add_cross_reference_edges(
                con, section, anchor_id
            )
            total_edges += ref_count

            # 3 — Add structural edges from parser flags
            #     (has_proviso, has_exception etc.)
            _add_marker_edges(con, section, anchor_id)

            # 4 — Add LLM-extracted SAT nodes
            node_map = _add_sat_nodes(con, sat, section)
            total_nodes += len(node_map)

            # 5 — Add LLM-extracted SAT edges
            edge_count = _add_sat_edges(con, sat, section)
            total_edges += edge_count

            # 6 — Connect all SAT claim nodes back
            #     to the anchor node
            for claim in sat.get("claims", []):
                claim_id = claim.get("id", "")
                if claim_id:
                    _insert_edge(
                        con      = con,
                        src      = claim_id,
                        dst      = anchor_id,
                        relation = EdgeType.SUPPORTS,
                        source   = section.get("source", "")
                    )
                    total_edges += 1

        con.commit()
        print(f"Graph built:")
        print(f"  Nodes : {total_nodes}")
        print(f"  Edges : {total_edges}")

        # Load into NetworkX for return
        G = _build_networkx_graph(con)
        print(f"  NetworkX graph: {G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges")
        return G

    finally:
        con.close()


# ─────────────────────────────────────────────
# Load existing graph from SQLite
# ─────────────────────────────────────────────

def load_graph() -> nx.DiGraph:
    """
    Load the graph from SQLite into NetworkX.
    Used by retriever.py at startup.
    """
    if not GRAPH_DB.exists():
        raise FileNotFoundError(
            f"Graph DB not found at {GRAPH_DB}. "
            f"Run the ingestion pipeline first."
        )

    con = sqlite3.connect(GRAPH_DB)
    try:
        G = _build_networkx_graph(con)
        return G
    finally:
        con.close()


# ─────────────────────────────────────────────
# Graph stats helper
# ─────────────────────────────────────────────

def graph_stats() -> dict:
    """
    Return basic stats about the stored graph.
    Useful for debugging and the /api/health endpoint.
    """
    if not GRAPH_DB.exists():
        return {"nodes": 0, "edges": 0, "status": "not built"}

    con = sqlite3.connect(GRAPH_DB)
    try:
        node_count = con.execute(
            "SELECT COUNT(*) FROM nodes"
        ).fetchone()[0]

        edge_count = con.execute(
            "SELECT COUNT(*) FROM edges"
        ).fetchone()[0]

        node_types = con.execute("""
            SELECT type, COUNT(*) as count
            FROM nodes
            GROUP BY type
            ORDER BY count DESC
        """).fetchall()

        edge_types = con.execute("""
            SELECT relation, COUNT(*) as count
            FROM edges
            GROUP BY relation
            ORDER BY count DESC
        """).fetchall()

        return {
            "nodes"      : node_count,
            "edges"      : edge_count,
            "node_types" : dict(node_types),
            "edge_types" : dict(edge_types),
            "status"     : "ready"
        }
    finally:
        con.close()


# ─────────────────────────────────────────────
# Entry point — test build
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import json as _json
    from backend.graph.extractor import extract_all

    processed_dir = Path(__file__).parent.parent / "data/processed"
    json_files    = list(processed_dir.glob("*.json"))

    if not json_files:
        print("No processed files found. Run parser.py first.")
        sys.exit(1)

    # Load sections
    all_sections = []
    for json_path in json_files:
        with open(json_path) as f:
            all_sections.extend(_json.load(f))

    print(f"Loaded {len(all_sections)} sections\n")

    # Test with first 5 sections only to keep it fast
    test_sections = all_sections[:5]
    print(f"Testing builder with first {len(test_sections)} sections...\n")

    # Extract SAT triples
    sat_results = extract_all(test_sections, delay=0.5)

    # Build graph
    G = build_graph(test_sections, sat_results)

    # Print stats
    print("\n--- Graph Stats ---")
    stats = graph_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    # Print sample edges
    print("\n--- Sample edges ---")
    con = sqlite3.connect(GRAPH_DB)
    rows = con.execute(
        "SELECT src, relation, dst FROM edges LIMIT 10"
    ).fetchall()
    con.close()
    for src, rel, dst in rows:
        print(f"  {src} --[{rel}]--> {dst}")