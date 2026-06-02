from indexer_helpers import *
from pathlib import Path
from collections import Counter
import hashlib
import json
import math

from bs4 import BeautifulSoup

from indexer_helpers import tokenize_and_stem, make_bigram, parse_html, simhash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN = PROJECT_ROOT / "bin"

UNIGRAM_INDEX = BIN / "final_unigram_indexer.jsonl"
BIGRAM_INDEX = BIN / "final_bigram_indexer.jsonl"
UNIGRAM_LEXICON = BIN / "final_unigram_lexicon.json"
BIGRAM_LEXICON = BIN / "final_bigram_lexicon.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_postings(term, lexicon, index_path):
    if term not in lexicon:
        return []

    with open(index_path, "r", encoding="utf-8") as f:
        f.seek(lexicon[term])
        record = json.loads(f.readline())

    if record["term"] != term:
        print("LEXICON MISMATCH:", term, "->", record["term"])

    return record["postings"]


def posting_for_doc(postings, doc_id):
    for posting in postings:
        if posting[0] == doc_id:
            return posting
    return None


def find_doc_id_by_path(target_path, debug_map):
    target_path = str(Path(target_path).resolve())

    for doc_id, path in debug_map.items():
        if str(Path(path).resolve()) == target_path:
            return int(doc_id)

    return None

def dump_raw_text(file_path, output_path):
    with open(file_path, "r", encoding="utf-8") as f:
        page = json.load(f)

    content = page.get("content") or ""
    soup = parse_html(content)

    if soup is None:
        text = content
    else:
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Raw parsed text written to: {output_path}")

def inspect_file_tokens(file_path, query_tokens):
    with open(file_path, "r", encoding="utf-8") as f:
        page = json.load(f)

    content = page.get("content") or ""
    soup = parse_html(content)

    if soup is None:
        text = content
        important_text = ""
    else:
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        important_text = " ".join(
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(["title", "h1", "h2", "h3", "b", "strong"])
        )

    token_counts = Counter(tokenize_and_stem(text))
    important_counts = Counter(tokenize_and_stem(important_text))

    print("\nParsed file token counts:")
    for token in query_tokens:
        print(
            token,
            "tf_in_parsed_text =", token_counts.get(token, 0),
            "important_tf =", important_counts.get(token, 0),
        )
def get_text_from_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        page = json.load(f)

    content = page.get("content") or ""
    soup = parse_html(content)

    if soup is None:
        return content

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    return soup.get_text(separator=" ", strip=True)


def print_doc_hashes(doc_id):
    debug_map = load_json(BIN / "debug_map.json")
    file_path = debug_map.get(str(doc_id))

    if file_path is None:
        print(f"doc_id {doc_id} not found in debug_map")
        return

    text = get_text_from_file(file_path)

    normalized_text = " ".join(text.lower().split())
    exact_digest = hashlib.sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()

    tokens = tokenize_and_stem(text)
    simhash_value = simhash(tokens)

    print("doc_id:", doc_id)
    print("file_path:", file_path)
    print("sha256:", exact_digest)
    print("simhash int:", simhash_value)
    print("simhash hex:", f"{simhash_value:016x}")
    print("simhash bin:", f"{simhash_value:064b}")

def explain_score(query, file_path):
    debug_map = load_json(BIN / "debug_map.json")
    doc_map = load_json(BIN / "doc_map.json")
    unigram_lexicon = load_json(UNIGRAM_LEXICON)
    bigram_lexicon = load_json(BIGRAM_LEXICON)

    doc_id = find_doc_id_by_path(file_path, debug_map)

    if doc_id is None:
        print("This file is not in debug_map. It may have been skipped as duplicate or failed during indexing.")
        return

    print("Query:", query)
    print("Doc ID:", doc_id)
    print("URL:", doc_map.get(str(doc_id)))
    print("File:", file_path)

    query_tokens = list(dict.fromkeys(tokenize_and_stem(query)))
    query_bigrams = make_bigram(query_tokens)

    print("\nQuery tokens:", query_tokens)
    print("Query bigrams:", query_bigrams)

    N = len(doc_map)
    total_score = 0.0

    print("\nUnigram contributions:")

    for token in query_tokens:
        postings = read_postings(token, unigram_lexicon, UNIGRAM_INDEX)
        posting = posting_for_doc(postings, doc_id)

        df = len(postings)
        idf = math.log((N + 1) / (df + 1)) + 1 if df else 0

        if posting is None:
            print(token, "NOT in postings for this doc")
            continue

        tf = posting[1]
        important_tf = posting[2]

        tf_score = 1 + math.log(tf + 2 * important_tf)
        contribution = tf_score * idf
        total_score += contribution

        print({
            "token": token,
            "posting": posting,
            "df": df,
            "idf": idf,
            "tf_score": tf_score,
            "contribution": contribution,
        })

    print("\nBigram contributions:")

    for bigram in query_bigrams:
        postings = read_postings(bigram, bigram_lexicon, BIGRAM_INDEX)
        posting = posting_for_doc(postings, doc_id)

        df = len(postings)
        idf = math.log((N + 1) / (df + 1)) + 1 if df else 0

        if posting is None:
            print(bigram, "NOT in bigram postings for this doc")
            continue

        tf = posting[1]
        tf_score = 1 + math.log(tf)
        contribution = 10 * tf_score * idf
        total_score += contribution

        print({
            "bigram": bigram,
            "posting": posting,
            "df": df,
            "idf": idf,
            "tf_score": tf_score,
            "contribution": contribution,
        })

    print("\nTotal debug score:", total_score)

    inspect_file_tokens(file_path, query_tokens)

    dump_raw_text(
        file_path,
        r"C:\Users\Zhang\Desktop\raw_debug_text.txt")


def print_hash_comparison(doc_id_a, doc_id_b):
    debug_map = load_json(BIN / "debug_map.json")

    text_a = get_text_from_file(debug_map[str(doc_id_a)])
    text_b = get_text_from_file(debug_map[str(doc_id_b)])

    sim_a = simhash(tokenize_and_stem(text_a))
    sim_b = simhash(tokenize_and_stem(text_b))

    print("doc A:", doc_id_a, f"{sim_a:016x}")
    print("doc B:", doc_id_b, f"{sim_b:016x}")
    print("hamming distance:", (sim_a ^ sim_b).bit_count())

if __name__ == "__main__":
    # query = "cristina lopes"
    # file_path = r"C:\Users\Zhang\Desktop\code\121\hw3\Search-Engine\data\developer\DEV\www_ics_uci_edu\29cf971008606c6a5961448e4bad8061d573cd4cf0a7d033b56a7de9b53666be.json"

    # explain_score(query, file_path)
    print_doc_hashes(21339)
    print_doc_hashes(18602)
    print_hash_comparison(21339, 18602)