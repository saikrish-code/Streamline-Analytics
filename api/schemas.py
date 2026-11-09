"""FastAPI request and response models for customer churn scoring."""

from pydantic import BaseModel, Field


class ChurnFeatures(BaseModel):
    recency_days: int = Field(ge=0, description="Days since the last non-canceled order")
    frequency_180d: int = Field(ge=1, description="Distinct orders in the previous 180 days")
    monetary_180d: float = Field(ge=0, description="Order value in BRL over the previous 180 days")
    average_order_value_180d: float = Field(ge=0)
    mean_review_sentiment_180d: float | None = Field(default=None, ge=-1, le=1)
    negative_review_share_180d: float | None = Field(default=None, ge=0, le=1)
    mean_review_score_180d: float | None = Field(default=None, ge=1, le=5)
    review_count_180d: int = Field(default=0, ge=0)


class ChurnPrediction(BaseModel):
    model_version: str
    churn_probability: float = Field(ge=0, le=1)
    predicted_churn: bool
    decision_threshold: float
