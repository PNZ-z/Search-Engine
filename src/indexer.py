from pathlib import Path
from bs4 import BeautifulSoup
from nltk.stem import PorterStemmer
from collections import Counter
from collections import defaultdict
import json
import re
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "developer" / "DEV"
BIN = PROJECT_ROOT/"bin"
BATCH_SIZE = 500
stemmer = PorterStemmer()


def parse_html(content):
    try:
        return BeautifulSoup(content, "lxml")
    except Exception:
        try:
            return BeautifulSoup(content, "html5lib")
        except Exception:
            return None
        
def merge_partial_indexes():
    merged = defaultdict(list)

    for partial_path in sorted(BIN.glob("partial_*.jsonl")):
        with open(partial_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                merged[record["term"]].extend(record["postings"])

    final_path = BIN / "final_index.jsonl"
    with open(final_path, "w", encoding="utf-8") as f:
        for term in sorted(merged.keys()):
            record = {
                "term": term,
                "postings": merged[term]
            }
            f.write(json.dumps(record) + "\n")

def tokenize_and_stem(text):
    tokens = re.findall(r"[a-z0-9A-Z]+", text.lower())
    return [stemmer.stem(token) for token in tokens]

def write_index(partial_index, partial_id):
    output_path = BIN/ f"partial_{partial_id:03d}.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for token in sorted(partial_index.keys()):
            record = {
                "term": token,
                "postings": partial_index[token]
            }
            f.write(json.dumps(record) + "\n")

BIN.mkdir(exist_ok=True)
def main():
    count = 0
    # utfcounter = 0
    # noncounter = 0
    
    partial_index = {}
    doc_id = 0
    partial_id = 0
    count = 0
    doc_map = {}
    for file_path in DATA_DIR.rglob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
            
                page = json.load(f)
                content = page.get("content") or ""
                soup = parse_html(content)
                if soup is None:
                    text = content
                    important_text = ""
                for tag in soup.find_all(["script", "style"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)

                important_text = " ".join(tag.get_text(" ", strip=True) for tag in soup.find_all(["title", "h1", "h2", "h3", "b", "strong"]))
                important_tokens = tokenize_and_stem(important_text)
                imp_token_counter = Counter(important_tokens)

                reg_token_counter = Counter(tokenize_and_stem(text))
                
                doc_id += 1            
                doc_map[doc_id] = page.get("url")
                for token, tf in reg_token_counter.items():
                    important_tf = imp_token_counter.get(token, 0)
                    posting = [doc_id, tf, important_tf]

                    partial_index.setdefault(token, []).append(posting)
                
                count += 1
                if count % BATCH_SIZE == 0:
                    write_index(partial_index, partial_id)
                    partial_index.clear()
                    partial_id += 1

                if count % 1000 == 0:
                    print(f"Processed {count} files")
                
                
            
        
        except Exception as e:  
            print(e)
            print(file_path)
        # finally:
        #     count+= 1
    # print(utfcounter, noncounter)

    if partial_index:
        write_index(partial_index, partial_id)
        partial_index.clear()

    with open(BIN / "doc_map.json", "w", encoding="utf-8") as f:
        json.dump(doc_map, f)

    merge_partial_indexes()

if __name__ == "__main__":
    main()