from fastapi import FastAPI
from app.routes import router

app = FastAPI(title="AutoLitigator")

app.include_router(router)