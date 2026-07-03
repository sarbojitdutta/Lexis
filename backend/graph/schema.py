
class NodeType:
    CLAIM      = "claim"       # A legal assertion or provision
    EVIDENCE   = "evidence"    # Supporting text, illustrations, explanations
    CONDITION  = "condition"   # An if/when clause that activates a claim
    EXCEPTION  = "exception"   # A notwithstanding/proviso clause
    DEFINITION = "definition"  # Defines a term used in other sections
    AMENDMENT  = "amendment"   # A modification to an earlier provision

    ALL = [CLAIM, EVIDENCE, CONDITION, EXCEPTION, DEFINITION, AMENDMENT]



# Edge/relation types

class EdgeType:
    SUPPORTS    = "SUPPORTS"    # This section strengthens another
    QUALIFIES   = "QUALIFIES"   # This section restricts another
    OVERRIDES   = "OVERRIDES"   # This section creates exception to another
    CITES       = "CITES"       # This section explicitly references another
    DEFINES     = "DEFINES"     # This section defines a term used in another
    AMENDS      = "AMENDS"      # This section modifies an earlier version
    ILLUSTRATES = "ILLUSTRATES" # This section gives an example of another

    ALL = [SUPPORTS, QUALIFIES, OVERRIDES, CITES, DEFINES, AMENDS, ILLUSTRATES]



# SQLite table schemas

CREATE_NODES_TABLE = """
    CREATE TABLE IF NOT EXISTS nodes (
        id          TEXT PRIMARY KEY,
        type        TEXT NOT NULL,
        text        TEXT NOT NULL,
        section_id  TEXT NOT NULL,
        source      TEXT NOT NULL,
        title       TEXT,
        part        TEXT,
        chapter     TEXT
    )
"""

CREATE_EDGES_TABLE = """
    CREATE TABLE IF NOT EXISTS edges (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        src         TEXT NOT NULL,
        dst         TEXT NOT NULL,
        relation    TEXT NOT NULL,
        source      TEXT NOT NULL,
        FOREIGN KEY (src) REFERENCES nodes(id),
        FOREIGN KEY (dst) REFERENCES nodes(id)
    )
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nodes_section ON nodes(section_id)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_type    ON nodes(type)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_source  ON nodes(source)",
    "CREATE INDEX IF NOT EXISTS idx_edges_src     ON edges(src)",
    "CREATE INDEX IF NOT EXISTS idx_edges_dst     ON edges(dst)",
    "CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation)",
]


# ─────────────────────────────────────────────
# SAT triple structure
# Used as a typed reference across extractor.py
# and builder.py
# ─────────────────────────────────────────────

# A single SAT extraction result for one section looks like:
#
# {
#   "claims": [
#       {"id": "s10_c1", "text": "All agreements are contracts if..."}
#   ],
#   "evidence": [
#       {"id": "s10_e1", "text": "Nothing herein shall affect any law..."}
#   ],
#   "conditions": [
#       {"id": "s10_cond1", "text": "if made by free consent of competent parties"}
#   ],
#   "exceptions": [
#       {"id": "s10_exc1", "text": "unless hereby expressly declared to be void"}
#   ],
#   "definitions": [],
#   "amendments":  [],
#   "relations": [
#       {"from": "s10_c1",    "to": "s11",      "type": "CITES"},
#       {"from": "s10_cond1", "to": "s10_c1",   "type": "QUALIFIES"},
#       {"from": "s10_exc1",  "to": "s10_c1",   "type": "OVERRIDES"}
#   ]
# }

EMPTY_SAT = {
    "claims"    : [],
    "evidence"  : [],
    "conditions": [],
    "exceptions": [],
    "definitions": [],
    "amendments": [],
    "relations" : [],
}


# ─────────────────────────────────────────────
# Quick sanity check
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Node types:")
    for t in NodeType.ALL:
        print(f"  {t}")

    print("\nEdge types:")
    for t in EdgeType.ALL:
        print(f"  {t}")

    print("\nSQLite schemas defined:")
    print("  nodes table  ✓")
    print("  edges table  ✓")
    print(f"  indexes      ✓ ({len(CREATE_INDEXES)} indexes)")

    print("\nEmpty SAT triple structure:")
    for k, v in EMPTY_SAT.items():
        print(f"  {k}: {v}")