from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from src.utils.logger import logger
from src.service.recommender import RecommenderEngine
from src.service.schemas import RecommendationRequest, RecommendationResponse

app = FastAPI(title="MovieRecs Service")

recommender = RecommenderEngine()

# Monitoring
# Expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def startup_event():
    """Load models when service starts."""
    logger.info("Service is starting up...")
    recommender.load_models()

@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """
    Main endpoint for inference.
    """
    logger.info(f"Incoming request for user_id={request.user_id}")
    
    recs, model_type = recommender.recommend(request.user_id, request.k)
    
    if model_type == "error" and not recs:
         raise HTTPException(status_code=503, detail="Models not loaded or internal error")

    return RecommendationResponse(
        user_id=request.user_id,
        recs=recs,
        model_type=model_type
    )

@app.post("/reload")
async def reload_models():
    """
    Endpoint triggered by Airflow after retraining.
    """
    logger.info("Reload signal received.")
    recommender.load_models()
    if recommender.models_loaded:
        return {"status": "success", "message": "Models reloaded"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reload models")

@app.get("/health")
async def health_check():
    status = "healthy" if recommender.models_loaded else "degraded"
    return {"status": status}
