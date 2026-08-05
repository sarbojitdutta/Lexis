import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import sqlite3
from fastapi     import APIRouter, HTTPException
from api.schemas import GraphResponse, GraphNode, GraphEdge
from config      import GRAPH_DB
from graph.retriever import get_full_context

router = APIRouter()


# ─────────────────────────────────────────────
# GET /api/graph/node/{section_id}
# ─────────────────────────────────────────────

@router.get("/graph/node/{section_id}",
            response_model=GraphResponse)
def get_graph_node(section_id: str):
    """
    Get a section's node and all its neighbours
    from the SAT graph.

    Used by frontend graph visualiser to show
    how sections connect to each other.
    """
    if not GRAPH_DB.exists():
        raise HTTPException(
            status_code = 503,
            detail      = "Graph database not built yet. "
                          "Run ingestion pipeline first."
        )

    try:
        context = get_full_context(section_id)
        con     = sqlite3.connect(GRAPH_DB)

        # Get the anchor node
        node_id  = f"s{section_id}"
        node_row = con.execute(
            "SELECT id, type, text, section_id "
            "FROM nodes WHERE id=?",
            (node_id,)
        ).fetchone()

        anchor_node = None
        if node_row:
            anchor_node = GraphNode(
                node_id    = node_row[0],
                type       = node_row[1],
                text       = node_row[2],
                section_id = node_row[3],
            )

        # Get all edges for this node
        edge_rows = con.execute("""
            SELECT src, dst, relation FROM edges
            WHERE src=? OR dst=?
        """, (node_id, node_id)).fetchall()

        edges = [
            GraphEdge(src=r[0], dst=r[1], relation=r[2])
            for r in edge_rows
        ]

        # Get all neighbour nodes
        neighbour_ids = set()
        for edge in edges:
            if edge.src != node_id:
                neighbour_ids.add(edge.src)
            if edge.dst != node_id:
                neighbour_ids.add(edge.dst)

        neighbours = []
        for nid in neighbour_ids:
            row = con.execute(
                "SELECT id, type, text, section_id "
                "FROM nodes WHERE id=?",
                (nid,)
            ).fetchone()
            if row:
                neighbours.append(GraphNode(
                    node_id    = row[0],
                    type       = row[1],
                    text       = row[2],
                    section_id = row[3],
                ))

        con.close()

        return GraphResponse(
            section_id = section_id,
            node       = anchor_node,
            neighbours = neighbours,
            edges      = edges,
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Graph query failed: {str(e)}"
        )


# ─────────────────────────────────────────────
# GET /api/graph/stats
# ─────────────────────────────────────────────

@router.get("/graph/stats")
def get_graph_stats():
    """
    Return overall graph statistics.
    """
    if not GRAPH_DB.exists():
        return {
            "status": "not built",
            "nodes" : 0,
            "edges" : 0,
        }

    con = sqlite3.connect(GRAPH_DB)
    try:
        nodes = con.execute(
            "SELECT COUNT(*) FROM nodes"
        ).fetchone()[0]

        edges = con.execute(
            "SELECT COUNT(*) FROM edges"
        ).fetchone()[0]

        node_types = con.execute("""
            SELECT type, COUNT(*) FROM nodes
            GROUP BY type ORDER BY COUNT(*) DESC
        """).fetchall()

        edge_types = con.execute("""
            SELECT relation, COUNT(*) FROM edges
            GROUP BY relation ORDER BY COUNT(*) DESC
        """).fetchall()

        return {
            "status"    : "ready",
            "nodes"     : nodes,
            "edges"     : edges,
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
        }
    finally:
        con.close()