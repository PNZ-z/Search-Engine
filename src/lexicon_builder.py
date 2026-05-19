import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN = PROJECT_ROOT / "bin"

def build_lexicon():
    final_index_path = BIN / "final_index.jsonl"
    lexicon_path = BIN / "lexicon.json"

    lexicon = {}
    with open(final_index_path, "r") as f:
        while True:
            offset = f.tell()
            line = f.readline()

            if not line:
                break

            record = json.loads(line)
            term = record["term"]
            lexicon[term] = offset

    with open(lexicon_path, "w") as f:
        json.dump(lexicon, f, separators=(",", ":"))

    print(f"Lexicon built successfully! Lexicon size: {len(lexicon)} terms")

if __name__ == "__main__":
    build_lexicon()