from pydantic import BaseModel
from typing import List, Literal

class RecommendationRequest(BaseModel):
    user_id: int
    k: int = 10

class RecommendationResponse(BaseModel):
    user_id: int
    recs: List[int]
    model_type: Literal["personal", "popular"]
