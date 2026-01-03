from fastapi import FastAPI
from app.api import router as api_router

app = FastAPI(
    title="Unified Cloud Platform API",
    description="API for Cloud Optimization, Security, and Reliability",
    version="0.1.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Unified Cloud Platform API is running"}
