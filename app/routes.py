from fastapi import APIRouter, File, UploadFile, Form, Depends
from sqlalchemy.orm import Session
from typing import List

from app.input_handler import process_legal_input
from app.db import get_db
from app.courtlistener import search_cases as search_cases_logic
from app.sec_filings import fetch_sec_filings
from app.schemas import CaseResult  # NEW


router = APIRouter()
@router.post("/analyze-case/")
async def analyze_case(
    text: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    return process_legal_input(text, file, db)


@router.get("/search-sec/")
async def search_sec(ticker: str, n: int = 3):
    print(f"[ROUTE] /search-sec/ called with ticker={ticker}")
    return fetch_sec_filings(ticker, num_filings=n)

@router.get("/search-cases/", response_model=list[CaseResult])
async def search_cases_route(query: str, n: int = 3):
    print(f"[ROUTE] /search-cases/ called with query={query}")
    return search_cases_logic(query, n=n)

    