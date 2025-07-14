import fitz  # PyMuPDF
from fastapi import UploadFile
from typing import Optional
from app.cache import cache_text, get_cached_text
from sqlalchemy.orm import Session
from app.models import CaseLog
from app.db import get_db

from app.cache import cache_text, get_cached_text
import fitz

def extract_text_from_pdf(file: UploadFile) -> str:
    doc = fitz.open(stream=file.file.read(), filetype="pdf")
    return " ".join([page.get_text() for page in doc])

def process_legal_input(text: Optional[str], file: Optional[UploadFile], db: Session):
    if file:
        cache_key = f"file:{file.filename}"
        cached = get_cached_text(cache_key)

        if cached:
            return {
                "cached": True,
                "source": "pdf",
                "preview": cached[:1000],
                "char_count": len(cached)
            }

        case_text = extract_text_from_pdf(file)
        cache_text(cache_key, case_text)

        # ✅ Log to DB
        log = CaseLog(
            source="pdf",
            filename=file.filename,
            char_count=len(case_text)
        )
        db.add(log)
        db.commit()

        return {
            "cached": False,
            "source": "pdf",
            "preview": case_text[:1000],
            "char_count": len(case_text)
        }

    elif text:
        # ✅ Log raw text to DB
        log = CaseLog(
            source="text",
            filename=None,
            char_count=len(text)
        )
        db.add(log)
        db.commit()

        return {
            "cached": False,
            "source": "text",
            "preview": text[:1000],
            "char_count": len(text)
        }

    else:
        return {"error": "No input provided"}
