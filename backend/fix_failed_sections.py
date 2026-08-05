import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
import sqlite3
from config          import DATA_PROCESSED, GRAPH_DB
from graph.extractor import extract_sat
from graph.builder   import build_graph, init_db

# Find sections that have no nodes in the graph
con      = sqlite3.connect(GRAPH_DB)
existing = set(
    row[0] for row in
    con.execute("SELECT section_id FROM nodes").fetchall()
)
con.close()

# Load all sections
all_sections = []
for json_path in DATA_PROCESSED.glob("*.json"):
    with open(json_path) as f:
        all_sections.extend(json.load(f))

# Find missing ones
missing = [
    s for s in all_sections
    if s["section_id"] not in existing
    and len(s["text"].split()) >= 20
]

print(f"Found {len(missing)} sections with no graph nodes")
print("Re-extracting...\n")

from graph.extractor import extract_all
sat_results = extract_all(missing, delay=2.0)
build_graph(missing, sat_results)
print("Done")