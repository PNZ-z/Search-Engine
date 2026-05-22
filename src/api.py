from flask import request, Flask, jsonify
from flask_cors import CORS
from retrieval import search

app = Flask(__name__)
CORS(app)

@app.route("/api/search")
def search_api():
    query = request.args.get("q", "")
    results = search(query, 5)
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True, port=5000)