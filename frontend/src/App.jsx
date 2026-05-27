import { useState } from "react";
import "./App.css"
function App(){
    const [ query, setQuery] = useState("");
    const [results, setResults] = useState([]);

    async function handleSearch(event){
        event.preventDefault();
        
        const response = await fetch(
            `http://127.0.0.1:5000/api/search?q=${encodeURIComponent(query)}`
        )


        const data =  await response.json();
        setResults(data);
    }

    return(
        <main className="mainpage">
            <h1>Search Engine</h1>
            <form className="search-form" onSubmit={handleSearch}>
                <input value={query}
                    onChange={(event) => setQuery(event.target.value)}/>
                <button className="search-button" type="submit">Search</button>
            </form>
            <ol className="results-list">
                {results.map((result) => (<li className="result-item" key={result.doc_id} ><a href={`http://127.0.0.1:5000/api/document/${result.doc_id}`}>{result.url}</a>
                <div className="result-info">Doc ID: {result.doc_id}</div> <div className="result-info">Score: {result.score.toFixed(4)}</div></li>))}
            </ol>
        </main>


    )

}

export default App;