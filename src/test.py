from indexer_helpers import *

partial_unigram_index = {}
partial_bigram_index = {}
doc_id = 0
partial_id = 0
count = 0
doc_map = {}
# declare and initialize dicts
for file_path in DATA_DIR.rglob("*.json"):
    if count >= 10:
        break;
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

            tokens = tokenize_and_stem(text)
            bigram = make_bigram(tokens)
            reg_token_counter = Counter(tokens)
            bigram_counter = Counter(bigram)
            
            
            doc_id += 1            
            doc_map[doc_id] = page.get("url")
            for token, tf in reg_token_counter.items():
                important_tf = imp_token_counter.get(token, 0)
                posting = [doc_id, tf, important_tf]

                partial_unigram_index.setdefault(token, []).append(posting)
            
            for bigram_token, tf in bigram_counter.items():
                posting = [doc_id, tf]

                partial_bigram_index.setdefault(bigram_token, []).append(posting)

            count += 1
            if count % BATCH_SIZE == 0:
                write_unigram_index(partial_unigram_index, partial_id)
                write_bigram_index(partial_bigram_index, partial_id)
                partial_unigram_index.clear()
                partial_bigram_index.clear()
                partial_id += 1

            if count % 1000 == 0:
                print(f"Processed {count} files")
            
            
        
    
    except Exception as e:  
        print(e)
        print(file_path)
    # finally:
    #     count+= 1
# print(utfcounter, noncounter)

if partial_unigram_index:
    write_unigram_index(partial_unigram_index, partial_id)
    write_bigram_index(partial_bigram_index, partial_id)
    partial_unigram_index.clear()
    partial_bigram_index.clear()
    
with open(BIN / "doc_map.json", "w", encoding="utf-8") as f:
    json.dump(doc_map, f)

merge_indexes()