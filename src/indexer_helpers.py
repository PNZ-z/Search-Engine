from pathlib import Path
from bs4 import BeautifulSoup
from nltk.stem import PorterStemmer
from collections import Counter
from collections import defaultdict
import json
import re
import heapq
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "developer" / "DEV"
BIN = PROJECT_ROOT/"bin"
BATCH_SIZE = 500
stemmer = PorterStemmer()
# cur example: {"term": "0000", "postings": [[171, 1, 0]]}  term, [[doc_id, tf, important tf], [doc_id, ... , ...]]
def parse_html(content):
    try:
        return BeautifulSoup(content, "lxml")
    except Exception:
        try:
            return BeautifulSoup(content, "html5lib")
        except Exception:
            return None
        
# build lexicon and merge the final index together
def merge_partial_indexes(partial_pattern, final_filename, final_lexicon_path):
    partial_paths = sorted(BIN.glob(partial_pattern))
    final_path = BIN / final_filename
    lexicon_path = BIN / final_lexicon_path
    files = []
    heap = []
    lexicon = {}
    try:
        for file_id, path in enumerate(partial_paths):
            file = open(path)
            files.append(file)

            line = file.readline()
            if line:
                record = json.loads(line)
                heapq.heappush(heap, (record["term"], file_id, record["postings"]))
        
        with open(final_path, "w") as f:
            while heap:
                term, file_id, postings = heapq.heappop(heap)
                copy_list = list(postings)
                next_line = files[file_id].readline()
                if next_line:
                    next_record = json.loads(next_line)
                    heapq.heappush(heap, (next_record["term"], file_id, next_record["postings"]))
                while heap and heap[0][0] == term:
                    _, same_file_id, same_postings = heapq.heappop(heap)
                    copy_list.extend(same_postings)

                    next_line = files[same_file_id].readline()
                    if next_line:
                        next_record = json.loads(next_line)
                        heapq.heappush(heap, (next_record["term"], file_id, next_record["postings"]))
                offset = f.tell()
                lexicon[term] = offset

                record = { "term" : term, "postings": copy_list}
                f.write(json.dumps(record) + "\n")

        with open(lexicon_path, "w") as lex:
            json.dump(lexicon, lex, separators=(",", ":"))
    finally:
        for file in files:
            file.close()


def merge_indexes():
    merge_partial_indexes("partial_unigram_*.jsonl", "final_unigram_indexer.jsonl", "final_unigram_lexicon.json")
    merge_partial_indexes("partial_bigram_*.jsonl", "final_bigram_indexer.jsonl", "final_bigram_lexicon.json")

def tokenize_and_stem(text):
    tokens = re.findall(r"[a-z0-9A-Z]+", text.lower())
    return [stemmer.stem(token) for token in tokens]

def write_unigram_index(partial_index, partial_id):
    output_path = BIN/ f"partial_unigram_{partial_id:03d}.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for token in sorted(partial_index.keys()):
            record = {
                "term": token,
                "postings": partial_index[token]
            }
            f.write(json.dumps(record) + "\n")

def write_bigram_index(partial_index, partial_id):
    output_path = BIN/ f"partial_bigram_{partial_id:03d}.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for token in sorted(partial_index.keys()):
            record = {
                "term": token,
                "postings": partial_index[token]
            }
            f.write(json.dumps(record) + "\n")


def make_bigram(tokens):
    return [
        tokens[i] + " " + tokens[i+1]
        for i in range(len(tokens)-1)
    ]