import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from fraud_detection.data_manager import PostgresDataService
from fraud_detection.retraining_pipeline import RetrainingPipeline

load_dotenv()

_data_service = None
_retraining_pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _data_service, _retraining_pipeline
    _data_service = PostgresDataService()
    _retraining_pipeline = RetrainingPipeline(data_service=_data_service)
    yield
    _data_service.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/retrain")
def retrain():
    labeled = _retraining_pipeline.get_labeled_count()
    if not _retraining_pipeline.request_retraining():
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": f"Not enough labeled data ({labeled} labeled, need 500)",
            },
        )
    result = _retraining_pipeline.run_retraining()
    status = 200 if result.get("success") else 500
    return JSONResponse(status_code=status, content=result)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("RETRAIN_HTTP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
