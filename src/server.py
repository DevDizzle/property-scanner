from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from src.main import run_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="Property Scanner API")

class ScanRequest(BaseModel):
    zip_codes: Optional[List[str]] = ["33301"]
    limit: Optional[int] = 200
    skip_enrich: Optional[bool] = False
    skip_ai: Optional[bool] = False
    ai_top_n: Optional[int] = 5
    is_demo: Optional[bool] = False
    skip_bq: Optional[bool] = False

@app.get("/health")
def health_check():
    return {"status": "ok"}

def _run_scan_task(req: ScanRequest):
    logger.info(f"Background task starting scan for {req.zip_codes}")
    try:
        run_pipeline(
            zip_codes=req.zip_codes,
            limit=req.limit,
            skip_enrich=req.skip_enrich,
            skip_ai=req.skip_ai,
            ai_top_n=req.ai_top_n,
            is_demo=req.is_demo,
            skip_bq=req.skip_bq,
        )
        logger.info("Background task scan completed.")
    except Exception as e:
        logger.error(f"Background task scan failed: {e}")

@app.post("/scan")
def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    """Trigger the property scanner pipeline."""
    if not req.zip_codes:
        raise HTTPException(status_code=400, detail="Must provide at least one zip code")
        
    background_tasks.add_task(_run_scan_task, req)
    
    return {
        "status": "accepted",
        "message": f"Scan triggered for {req.zip_codes}. Limit: {req.limit}",
    }
