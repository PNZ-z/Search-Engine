from indexer_helpers import tokenize_and_stem
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

final_unigram_indexer_path = BIN / "final_unigram_indexer.jsonl"
final_bigram_indexer_path = BIN / "final_bigram_indexer.jsonl"
unigram_lexicon_path = BIN / "final_unigram_lexicon.json"
bigram_lexicon_path = BIN / "final_bigram_lexicon.json"

with open(unigram_lexicon_path, "r") as f:
    unigram_lexicon = json.load(f)
with open(bigram_lexicon_path, "r") as f:
    bigram_lexicon = json.load(f)
with open(BIN / "doc_map.json", "r", encoding="utf-8") as f:
    doc_map = json.load(f)
    N = len(doc_map)

def calc_tf(token, doc_id, posting_map):
    posting = posting_map[token][doc_id]
    return 1+math.log(posting[1] + 2*posting[2])\
    
def calc_tf_bigram(token, doc_id, posting_map):
    # print(posting_map)
    if doc_id not in posting_map[token]:
        return 0
    posting = posting_map[token][doc_id]
    return 1+math.log(posting[1])

def calc_idf(token, posting_dict):
    postings = posting_dict[token]
    idf = math.log((N + 1)/(len(postings) + 1)) + 1
    return idf


def calc_score(doc_id, unigram_tokens, unigram_posting_map,  bigram_tokens, bigram_posting_map, unigram_posting_by_term, bigram_posting_by_term):
    score = 0.0
    for token in unigram_tokens:
        score += calc_tf(token, doc_id, unigram_posting_map) * calc_idf(token, unigram_posting_by_term)
    for token in bigram_tokens:
        score += 10 * (calc_tf_bigram(token, doc_id, bigram_posting_map)) * calc_idf(token, bigram_posting_by_term)
    return score

# load postings from the file in to the correspond dict of posting
def load_records(postings_dest, indexer_path, offsets):
    with open(indexer_path, "r") as f:
        for token, offset in offsets:
            f.seek(offset)
            record = json.loads(f.readline())
            postings_dest[token] = record["postings"]

#get the docid to posting dict for better cal
def load_docid_to_posting(posting_map, posting_by_term):
    for token, postings in posting_by_term.items():
        posting_curr_dict = {}
        for posting in postings:
            posting_curr_dict[posting[0]] = posting
        posting_map[token] = posting_curr_dict

def fetch_doc_list(posting_by_term, unigram_tokens, unigram_posting_map, bigram_tokens, bigram_posting_map):
    doc_sets = []
    for posting in posting_by_term.values():
        doc_sets.append({id[0] for id in posting})
    matched_doc = set.intersection(*doc_sets)

    scores = {}
    for doc_id in matched_doc:
        scores[doc_id] = calc_score(doc_id, unigram_tokens, unigram_posting_map,  bigram_tokens, bigram_posting_map, posting_by_term)
    sorted_doc_list = sorted(matched_doc, key= lambda doc_id : scores[doc_id], reverse=True)
    return sorted_doc_list

def search(query, limit=5):
    tokens = list(dict.fromkeys(tokenize_and_stem(query)))
    if not tokens:
        print("No tokens")
        return []
    if any(token not in unigram_lexicon for token in tokens):
        print("No matched result")
        print(tokens)
        print(len(unigram_lexicon))
        return []
    term_offsets = [(token, unigram_lexicon[token]) for token in tokens]

    if(len(tokens) > 1):
        bigram_tokens = [
            tokens[i] + " " + tokens[i+1]
            for i in range(len(tokens) -1)
        ]
    else:
        bigram_tokens = []
    term_bigram_offsets = [(token, bigram_lexicon[token]) for token in bigram_tokens]

    posting_by_term = {}
    posting_by_term_bigram = {}

    load_records(posting_by_term, final_unigram_indexer_path, term_offsets)
    load_records(posting_by_term_bigram, final_bigram_indexer_path, term_bigram_offsets)
    
    
    unigram_posting_map = {}
    bigram_posting_map = {}
    load_docid_to_posting(unigram_posting_map, posting_by_term)
    load_docid_to_posting(bigram_posting_map, posting_by_term_bigram)



    doc_sets = []
    for posting in posting_by_term.values():
        doc_sets.append({id[0] for id in posting})
    matched_doc = set.intersection(*doc_sets)

    scores = {}
    for doc_id in matched_doc:
        scores[doc_id] = calc_score(doc_id, tokens, unigram_posting_map, bigram_tokens, bigram_posting_map, posting_by_term, posting_by_term_bigram)
    sorted_doc_list = sorted(matched_doc, key= lambda doc_id : scores[doc_id], reverse=True)

    top_docs = sorted_doc_list[:limit]

    return [
            {
                "doc_id": doc_id,
                "url": doc_map[str(doc_id)],
                "score": scores[doc_id],
            }
            for doc_id in top_docs
        ]
    


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



