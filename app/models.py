from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.db import Base

class CaseLog(Base):
    __tablename__ = "case_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    filename = Column(String, nullable=True)
    char_count = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class SearchLog(Base):
    __tablename__ = "search_logs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True)
    result_count = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)