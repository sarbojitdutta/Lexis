# backend/run_graph.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import json
from graph.extractor import extract_all
from graph.builder   import build_graph, graph_stats

processed_dir = Path("data/processed")
json_files    = list(processed_dir.glob("*.json"))

if not json_files:
    print("No processed files found. Run parser.py first.")
    sys.exit(1)

# Load all sections
all_sections = []
for json_path in json_files:
    with open(json_path) as f:
        sections = json.load(f)
        all_sections.extend(sections)
        print(f"Loaded {len(sections)} sections from {json_path.name}")

print(f"\nTotal sections: {len(all_sections)}")
print("Starting SAT extraction and graph build...\n")

# Extract SAT triples from all sections
sat_results = extract_all(all_sections, delay=0.5)

# Build graph
G = build_graph(all_sections, sat_results)

# Print final stats
print("\n--- Final Graph Stats ---")
stats = graph_stats()
for k, v in stats.items():
    print(f"  {k}: {v}")