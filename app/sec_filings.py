import requests
from bs4 import BeautifulSoup
from app.downloader import download_and_save

import requests
import re

def resolve_cik_from_ticker_or_name(ticker_or_name: str) -> str:
    """Resolve ticker or company name to CIK with better matching"""
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {"User-Agent": "autolitigator@example.com"}
    

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print("[ERROR] CIK endpoint returned:", res.status_code)
            return None

        data = res.json()

        cleaned_input = re.sub(r'\W+', '', ticker_or_name).lower()  # remove punctuation & lowercase

        for item in data.values():
            ticker_clean = re.sub(r'\W+', '', item['ticker']).lower()
            title_clean = re.sub(r'\W+', '', item['title']).lower()

            if cleaned_input in ticker_clean or cleaned_input in title_clean:
                return str(item['cik_str']).zfill(10)

    except Exception as e:
        print("Error resolving CIK:", e)

    print(f"[ERROR] Could not resolve CIK for: {ticker_or_name}")
    return None



def fetch_sec_filings(ticker_or_name: str, num_filings: int = 3):
    cik = resolve_cik_from_ticker_or_name(ticker_or_name)
    if not cik:
        print(f"[ERROR] Could not resolve CIK for: {ticker_or_name}")
        return []

    base_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&owner=exclude&count={num_filings}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Referer": "https://www.sec.gov/",
        "Connection": "keep-alive"
    }

    res = requests.get(base_url, headers=headers)
    print(f"[DEBUG] SEC query status: {res.status_code}")
    print("[DEBUG] SEC HTML snippet:", res.text[:1000])

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select('a[href*="Archives/edgar/data"][id^="documentsbutton"]')
    print(f"[DEBUG] Found {len(links)} document links")

    filings = []

    for i, link in enumerate(links[:num_filings]):
        href = link.get("href")
        if not href:
            continue
        doc_url = f"https://www.sec.gov{href}"
        print(f"[DEBUG] Accessing document page: {doc_url}")

        filing_res = requests.get(doc_url, headers=headers)
        print(f"[DEBUG] Filing page status: {filing_res.status_code}")

        filing_soup = BeautifulSoup(filing_res.text, "html.parser")
        target_link = filing_soup.find("a", string=lambda s: s and ("htm" in s or "txt" in s))
        print(f"[DEBUG] Target link: {target_link}")

        if target_link:
            file_href = target_link.get("href")
            full_url = f"https://www.sec.gov{file_href}"
            save_as = f"sec_{ticker_or_name}_{i+1}.html"
            print(f"[DEBUG] Saving: {full_url} as {save_as}")
            # download_and_save(full_url, save_as)

            filings.append({
                "summary_page": doc_url,
                "document_saved_as": save_as,
                "original_doc_url": full_url
            })

    print(f"[DEBUG] Returning filings: {filings}")
    return filings
