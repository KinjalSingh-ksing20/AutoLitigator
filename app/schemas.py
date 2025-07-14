from pydantic import BaseModel
from typing import Optional, List

class CaseResult(BaseModel):
    case_name: str
    court: str
    date_filed: str
    url: str

    judge_name: Optional[str] = None
    case_number: Optional[str] = None
    statutes: Optional[List[str]] = []
    precedents: Optional[List[str]] = []
    ruling_summary: Optional[str] = None