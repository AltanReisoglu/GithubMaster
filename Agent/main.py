from fastapi import FastAPI
from api.analyze import router as analyze_router

app = FastAPI(title="Multi-Agent GitHub Analyst")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Multi-Agent GitHub Analyst is running"}

@app.get("/health")
async def health():
    """Health check endpoint — Java backend bunu çağırarak ayakta olduğumuzu kontrol eder."""
    checks = {"agent": "up"}

    # Ollama check
    try:
        import httpx
        from config import config
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            checks["ollama"] = "up" if resp.status_code == 200 else "down"
    except Exception:
        checks["ollama"] = "down"

    overall = "healthy" if all(v == "up" for v in checks.values()) else "degraded"
    return {"status": overall, **checks}

app.include_router(analyze_router, prefix="/api/agent", tags=["Analyze"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

