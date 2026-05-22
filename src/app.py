from flask import Flask, render_template, request
import retrieval
from retrieval import search

app = Flask(
    __name__,
    template_folder="../templates"
)

@app.route("/", methods=["GET", "POST"])
def home():
    query = ""
    results = []

    if request.method == "POST":
        query = request.form.get("query", "")
        results = search(query, limit=5)

    return render_template("index.html", query=query, results=results)

if __name__ == "__main__":
    app.run(debug=True)