import requests
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.db import SessionLocal
from app.models import SearchLog
from app.cache import get_cached_text, cache_text
import hashlib
import json

def query_cache_key(query: str) -> str:
    return "courtlistener:" + hashlib.sha1(query.encode()).hexdigest()


API_TOKEN = "9a87752efee09043325d6f5621edc07ad5101c91"
BASE_URL = "https://www.courtlistener.com/api/rest/v4"

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Accept": "application/json"
}

# Setup logger
logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")

def log_search_to_db(query: str, result_count: int):
    db = SessionLocal()
    try:
        entry = SearchLog(query=query, result_count=result_count)
        db.add(entry)
        db.commit()
    except Exception as e:
        logging.error(f"[DB ERROR] Failed to log search: {e}")
    finally:
        db.close()

def get_retry_session():
    """Create a retry-enabled requests session."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[502, 503, 504, 429],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session

session = get_retry_session()


def fetch_results(endpoint: str, query: str, n: int = 5, retries: int = 5):
    """Fetch results from a CourtListener endpoint with retries."""
    url = f"{BASE_URL}/{endpoint}?search={query}&order_by=date_filed"
    
    for attempt in range(1, retries + 1):
        try:
            logging.debug(f"[Attempt {attempt}] Fetching from: {url}")
            response = session.get(url, headers=HEADERS, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])[:n]

            elif response.status_code == 202:
                logging.info("[202 Accepted] Still processing. Retrying in 3s...")
                time.sleep(3)
                continue

            else:
                logging.error(f"[{response.status_code}] Unexpected status.")
                break

        except requests.exceptions.RequestException as e:
            logging.error(f"[Exception] {str(e)}")
            time.sleep(2)

    logging.warning(f"Failed to get results from {endpoint}")
    return []


from app.schemas import CaseResult  # <-- Make sure this is at the top
import re

def extract_metadata_from_plain_text(text: str) -> dict:
    """Extract judge name, case number, statutes, precedents, and ruling summary."""
    judge_name = None
    case_number = None
    statutes = []
    precedents = []
    ruling_summary = None

    if not text:
        return {
            "judge_name": None,
            "case_number": None,
            "statutes": [],
            "precedents": [],
            "ruling_summary": None,
        }

    lines = text.splitlines()

    # Case number: e.g., 5:24-CV-01032-XR
    match_case = re.search(r"\b\d{1,2}:\d{2}-[A-Z]+-\d+\b", text)
    if match_case:
        case_number = match_case.group()

    # Judge name: look for "To the Honorable ..."
    match_judge = re.search(r"To the Honorable\s+(.*?)[:\n]", text, re.IGNORECASE)
    if match_judge:
        judge_name = match_judge.group(1).strip()

    # Statutes: e.g., "28 U.S.C. § 636(b)(1)(A)"
    statutes = re.findall(r"\b\d+\s+U\.S\.C\.\s+§+\s*[\w\d\(\)\.]+", text)

    # Precedents: look for patterns like "v." + citation
    precedents = re.findall(r"\b[A-Z][a-zA-Z]+ v\. [A-Z][a-zA-Z]+, \d+ U\.S\. \d+", text)

    # Ruling summary: try to find the "Conclusion and Recommendation" block
    conclusion_match = re.search(r"(Conclusion and Recommendation.*?)(Instructions for Service|IT IS SO ORDERED|Signed|$)", text, re.DOTALL | re.IGNORECASE)
    if conclusion_match:
        summary = conclusion_match.group(1).strip()
        ruling_summary = re.sub(r"\s+", " ", summary)[:500]  # trim and compact

    return {
        "judge_name": judge_name,
        "case_number": case_number,
        "statutes": statutes,
        "precedents": precedents,
        "ruling_summary": ruling_summary,
    }

import logging
def get_court_name(court_url: str) -> str:
    """Fetches human-readable court name from the court URL."""
    try:
        full_url = f"https://www.courtlistener.com{court_url}" if court_url.startswith("/api/") else court_url
        response = session.get(full_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("name", "N/A")
    except Exception as e:
        logging.error(f"[Court Fetch Error] {e}")
    return "N/A"

def get_cluster_details(cluster_url: str) -> dict:
    """Fetches metadata like case name, court, and date_filed from the cluster endpoint."""
    try:
        cluster_resp = session.get(cluster_url, headers=HEADERS, timeout=10)
        if cluster_resp.status_code == 200:
            return cluster_resp.json()
        else:
            logging.warning(f"[Cluster] Failed to fetch metadata from {cluster_url} — Status: {cluster_resp.status_code}")
    except Exception as e:
        logging.error(f"[Cluster Exception] {str(e)}")
    return {}

def search_cases(query: str, n: int = 5):
    """Try /opinions/, fallback to /clusters/, return structured cases enriched with metadata."""
    logging.info(f"[QUERY] Searching for: {query}")

    cache_key = query_cache_key(query)
    cached = get_cached_text(cache_key)
    if cached:
        logging.info("[CACHE HIT] Returning cached result")
        return json.loads(cached)
    
    results = fetch_results("opinions", query, n=n)
    if not results:
        logging.warning("[FALLBACK] Trying /clusters/ endpoint instead.")
        results = fetch_results("clusters", query, n=n)

    structured = []
    for result in results:
        print("[DEBUG] Raw result keys:", result.keys())
        print("[DEBUG] Result:", result)

        case_name = "N/A"
        court = "N/A"
        date_filed = "N/A"

        cluster_url = result.get("cluster")
        plain_text = result.get("plain_text", "")

        # Try extracting from cluster
        if cluster_url:
            cluster_data = get_cluster_details(cluster_url)
            case_name = cluster_data.get("case_name", "N/A")
            date_filed = cluster_data.get("date_filed", "N/A")

        # Extract court name from first 10 lines of plain_text
        if plain_text:
            lines = [line.strip() for line in plain_text.strip().splitlines()]
            for i, line in enumerate(lines[:15]):  # scan first 15 lines just in case
                if "district court" in line.lower():
                    court_line = line.strip()
                    next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

                    # If next line adds jurisdiction info (e.g., FOR THE WESTERN DISTRICT...)
                    if next_line.lower().startswith("for the") or "district of" in next_line.lower():
                        court = f"{court_line}, {next_line}"
                    else:
                        court = court_line
                    break

        enriched = extract_metadata_from_plain_text(plain_text)

        case = CaseResult(
            case_name=case_name,
            court=court,  # DON'T TOUCH THIS
            date_filed=date_filed,
            url="https://www.courtlistener.com" + result.get("absolute_url", "")
            if result.get("absolute_url") else "https://www.courtlistener.com",
            judge_name=enriched["judge_name"],
            case_number=enriched["case_number"],
            statutes=enriched["statutes"],
            precedents=enriched["precedents"],
            ruling_summary=enriched["ruling_summary"]
        )
        structured.append(case)

        cache_text(cache_key, json.dumps([case.dict() for case in structured]))  # assuming CaseResult is a pydantic model

        log_search_to_db(query, len(structured))

    return structured

# CLI test
if __name__ == "__main__":
    query = "privacy laws"
    top_cases = search_cases(query, n=3)

    for idx, case in enumerate(top_cases, start=1):
        print(f"\n📄 Result {idx}:")
        print("  ➤ Title:", case["case_name"])
        print("  ➤ Court:", case["court"])
        print("  ➤ Date:", case["date_filed"])
        print("  ➤ URL: ", case["url"])
