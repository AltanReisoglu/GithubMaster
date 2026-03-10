from fastapi import FastAPI
from api.webhooks import router as webhook_router
from api.analyze import router as analyze_router

app = FastAPI(title="Multi-Agent GitHub Analyst")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Multi-Agent GitHub Analyst is running"}

app.include_router(webhook_router, prefix="/webhooks", tags=["GitHub"])
app.include_router(analyze_router, prefix="/api/agent", tags=["Analyze"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
