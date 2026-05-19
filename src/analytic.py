
from pathlib import Path

import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "developer" / "DEV"
BIN = PROJECT_ROOT/"bin"
BATCH_SIZE = 500
with open(BIN / "doc_map.json", "r", encoding="utf-8") as f:
    doc_map = json.load(f)

num_docs = len(doc_map)
unique_tokens = 0
with open(BIN / "final_index.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        unique_tokens += 1
        
print("The number of docs:", num_docs)
print("The number of unique tokens:", unique_tokens)
