from fastapi import FastAPI
from app.routes import router
from fastapi.responses import RedirectResponse

app = FastAPI(title="AutoLitigator")

app.include_router(router)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

