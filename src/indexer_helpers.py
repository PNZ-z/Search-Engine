from pathlib import Path
from bs4 import BeautifulSoup
from nltk.stem import PorterStemmer
from collections import Counter
from collections import defaultdict
from hashlib import md5
import json
import re
import heapq
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "developer" / "DEV"
BIN = PROJECT_ROOT/"bin"
BATCH_SIZE = 500
stemmer = PorterStemmer()
# cur example: {"term": "0000", "postings": [[171, 1, 0]]}  term, [[doc_id, tf, important tf], [doc_id, ... , ...]]

import re

HTML_TAG_PATTERN = re.compile(
    r"<\s*(html|head|body|title|p|div|span|a|h1|h2|h3|ul|ol|li|table|tr|td|strong|b|br)\b",
    re.IGNORECASE
)

def is_probably_html_page(content):
    if not content:
        return False

    stripped = content.strip()

    if len(stripped) < 50:
        return False

    # Reject obvious plain text: no common HTML tags at all.
    if not HTML_TAG_PATTERN.search(stripped):
        return False

    soup = parse_html(content)

    if soup is None:
        return False

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    tokens = re.findall(r"[A-Za-z0-9]+", text)

    # Avoid indexing pages with almost no searchable content.
    if len(tokens) < 5:
        return False

    return True

def relative_path(path, base):
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
    
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
                        heapq.heappush(heap, (next_record["term"], same_file_id, next_record["postings"]))
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

def stable_64_bit_hash(feature):
    digest = md5(feature.encode("utf=8")).digest()
    return int.from_bytes(digest[:8], 'big')

def simhash(features):
    vector = [0] * 64
    counts = Counter(features)

    for feature, weight in counts.items():
        h = stable_64_bit_hash(feature)
        for bit in range(64):
            if h & (1 << bit):
                vector[bit] += weight
            else:
                vector[bit] -= weight
    
    fingerprint = 0
    for i in range(64):
        if vector[i] > 0:
            fingerprint |= (1 << i)
    
    return fingerprint

def get_blocks(fingerprint):
    blocks = []

    for blockid in range(4):
        block_value = fingerprint & (1 >> blockid*16)
        blocks.append((blockid, block_value))

    return blocks

def hammingdistance(a, b):
    return (a ^ b).bit_count()

def find_near_duplicate(fingerprint, buckets, fingerprints):
    candidate_doc_ids = set()

    for block in get_blocks(fingerprint):
        candidate_doc_ids.update(buckets.get(block, []))

    for doc_id in candidate_doc_ids:
        distance = hammingdistance(fingerprint, fingerprints[doc_id])
        if distance <= 3:
            return doc_id, distance
        
    return None, None

def update_seen_hash(buckets, fingerprint, fingerprints, doc_id):
    fingerprints[doc_id] = fingerprint
    for block in get_blocks(fingerprint):
        buckets.setdefault(block, []).append(doc_id)