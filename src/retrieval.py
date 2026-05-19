from indexer import tokenize_and_stem
from pathlib import Path
import json
import sys, signal
import math

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "developer" / "DEV"
BIN = PROJECT_ROOT/"bin"


def graceful_exit(signum, frame):
    print(f"\nSignal {signum} received. Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)

final_indexer_path = BIN / "final_index.jsonl"
lexicon_path = BIN / "lexicon.json"

with open(lexicon_path, "r") as f:
    lexicon = json.load(f)
with open(BIN / "doc_map.json", "r", encoding="utf-8") as f:
    doc_map = json.load(f)
    N = len(doc_map)

def calc_tf(token, doc_id, posting_map):
    posting = posting_map[token][doc_id]
    return posting[1] + 2*posting[2]

def calc_idf(token, posting_dict):
    postings = posting_dict[token]
    idf = math.log((N + 1)/(len(postings) + 1)) + 1
    return idf

def calc_score(doc_id, tokens, posting_map, posting_dict):
    score = 0.0
    for token in tokens:
        score += calc_tf(token, doc_id, posting_map) * calc_idf(token, posting_dict)
    return score

def main():


    while True:
        query = input("Please input the query for search:(ctrl + c to exit)")
        tokens = list(dict.fromkeys(tokenize_and_stem(query)))
        if not tokens:
            print("No matched results.")
            continue
        if any(token not in lexicon for token in tokens):
            print("No matched result")
            continue
        term_offsets = [(token, lexicon[token]) for token in tokens]

        posting_by_term = {}
        with open(final_indexer_path, "r") as f:
            for token, offset in term_offsets:
                f.seek(offset)
                record = json.loads(f.readline())
                posting_by_term[token] = record["postings"]
        
        posting_map = {}
        for token, postings in posting_by_term.items():
            posting_curr_dict = {}
            for posting in postings:
                posting_curr_dict[posting[0]] = posting
            posting_map[token] = posting_curr_dict


        doc_sets = []
        for posting in posting_by_term.values():
            doc_sets.append({id[0] for id in posting})
        matched_doc = set.intersection(*doc_sets)

        scores = {}
        for doc_id in matched_doc:
            scores[doc_id] = calc_score(doc_id, tokens, posting_map, posting_by_term)
        sorted_doc_list = sorted(matched_doc, key= lambda doc_id : scores[doc_id], reverse=True)

        top_docs = sorted_doc_list[:5]

        for doc_id in top_docs:
            print(doc_id, doc_map[str(doc_id)])

        continue
    
if __name__ == "__main__":
    main()



