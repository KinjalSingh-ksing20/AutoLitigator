from app.db import Base, engine
from app.models import CaseLog

# Create tables
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully.")
