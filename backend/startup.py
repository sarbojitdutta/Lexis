import os
import shutil
from pathlib import Path

RENDER_DATA = Path("/data")
LOCAL_DB    = Path(__file__).parent / "db"
LOCAL_DATA  = Path(__file__).parent / "data"

def setup_render_disk():
    print("Setting up Render persistent disk...")

    # Create folders
    (RENDER_DATA / "db/faiss").mkdir(parents=True, exist_ok=True)
    (RENDER_DATA / "db/graph").mkdir(parents=True, exist_ok=True)
    (RENDER_DATA / "data/raw").mkdir(parents=True, exist_ok=True)
    (RENDER_DATA / "data/processed").mkdir(parents=True, exist_ok=True)

    print("Folders created on /data disk")
    print("Now upload your files via Render shell:")
    print("  /data/db/faiss/legal.index")
    print("  /data/db/faiss/legal_meta.json")
    print("  /data/db/graph/graph.db")
    print("  /data/data/processed/*.json")

if __name__ == "__main__":
    setup_render_disk()