from fastapi import FastAPI
from app.routes import router
from fastapi.responses import HTMLResponse

app = FastAPI(title="AutoLitigator")

app.include_router(router)
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <h1>👋 Welcome to AutoLitigator</h1>
    <p>This is a legal document mining API. Use the endpoints like:</p>
    <ul>
        <li><code>POST /analyze-case/</code> – Upload a brief or description</li>
        <li><code>GET /search-sec/?ticker=AAPL</code> – Search SEC filings</li>
        <li><code>GET /search-cases/?query=wrongful+termination</code> – Case law retrieval</li>
    </ul>
    <p>Explore the interactive docs at <a href="/docs">/docs</a></p>
    """

