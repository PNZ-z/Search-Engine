from pathlib import Path
from flask import request, Flask, jsonify, Response, abort
from flask_cors import CORS
from retrieval import search
from bs4 import BeautifulSoup
import json
app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN = PROJECT_ROOT / "bin"

with open(BIN / "debug_map.json", "r", encoding="utf-8") as f:
    debug_map = json.load(f)


@app.route("/api/search")
def search_api():
    query = request.args.get("q", "")
    results = search(query, 5)
    return jsonify(results)

@app.route("/api/document/<int:doc_id>")
def document_api(doc_id):
    file_path = debug_map.get(str(doc_id))

    if file_path is None:
        abort(404)

    with open(file_path, "r", encoding="utf-8") as f:
        page = json.load(f)

    content = page.get("content") or ""
    soup = BeautifulSoup(content, "lxml")

    # Avoid running JavaScript from crawled pages locally.
    for tag in soup.find_all("script"):
        tag.decompose()
    print(file_path)
    return Response(str(soup), content_type="text/html; charset=utf-8")
if __name__ == "__main__":
    app.run(debug=True, port=5000)