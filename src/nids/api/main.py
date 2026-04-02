from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
import joblib
import os

from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.pipeline.processor import Pipeline, NetworkFlow
from src.nids.data.loader import FEATURE_COLUMNS


app = FastAPI(
    title="NIDS API",
    description="Network Intrusion Detection System - Real-time inference API",
    version="1.0.0",
)


class FlowFeatures(BaseModel):
    flow_duration: float
    total_fwd_packets: int
    total_bwd_packets: int
    total_length_fwd_packets: float
    total_length_bwd_packets: float
    fwd_packet_length_mean: float
    fwd_packet_length_std: float
    bwd_packet_length_mean: float
    bwd_packet_length_std: float
    flow_bytes_per_sec: float
    flow_packets_per_sec: float
    flow_iat_mean: float
    flow_iat_std: float
    flow_iat_max: float
    fwd_iat_total: float
    fwd_iat_mean: float
    fwd_iat_std: float
    bwd_iat_total: float
    bwd_iat_mean: float
    bwd_iat_std: float
    fwd_packets_per_sec: float
    bwd_packets_per_sec: float
    down_up_ratio: float
    avg_packet_size: float
    avg_fwd_segment_size: float
    avg_bwd_segment_size: float
    subflow_fwd_packets: int
    subflow_bwd_packets: int
    subflow_fwd_bytes: float
    subflow_bwd_bytes: float


class PredictionRequest(BaseModel):
    features: FlowFeatures
    src_ip: Optional[str] = "0.0.0.0"
    dst_ip: Optional[str] = "0.0.0.0"


class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    probabilities: Dict[str, float]
    explanation: Dict[str, Any]


class AlertResponse(BaseModel):
    id: str
    timestamp: str
    src_ip: str
    dst_ip: str
    attack_type: str
    confidence: float
    top_3_features: List[Dict[str, Any]]
    severity: str


@app.on_event("startup")
async def load_models():
    """Load classifier and explainer on startup."""
    try:
        app.state.classifier = NIDSClassifier()
        app.state.classifier.load("models/nids_model.pkl")

        app.state.explainer = SHAPExplainer(app.state.classifier.model, FEATURE_COLUMNS)

        app.state.pipeline = Pipeline(app.state.classifier, app.state.explainer)

        print("✓ Models loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load models: {e}")
        app.state.classifier = None
        app.state.explainer = None
        app.state.pipeline = None


@app.get("/")
async def root():
    return {"name": "NIDS API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": app.state.classifier is not None}


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Predict attack type for a single network flow."""
    if app.state.classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feature_values = [
        request.features.flow_duration,
        request.features.total_fwd_packets,
        request.features.total_bwd_packets,
        request.features.total_length_fwd_packets,
        request.features.total_length_bwd_packets,
        request.features.fwd_packet_length_mean,
        request.features.fwd_packet_length_std,
        request.features.bwd_packet_length_mean,
        request.features.bwd_packet_length_std,
        request.features.flow_bytes_per_sec,
        request.features.flow_packets_per_sec,
        request.features.flow_iat_mean,
        request.features.flow_iat_std,
        request.features.flow_iat_max,
        request.features.fwd_iat_total,
        request.features.fwd_iat_mean,
        request.features.fwd_iat_std,
        request.features.bwd_iat_total,
        request.features.bwd_iat_mean,
        request.features.bwd_iat_std,
        request.features.fwd_packets_per_sec,
        request.features.bwd_packets_per_sec,
        request.features.down_up_ratio,
        request.features.avg_packet_size,
        request.features.avg_fwd_segment_size,
        request.features.avg_bwd_segment_size,
        request.features.subflow_fwd_packets,
        request.features.subflow_bwd_packets,
        request.features.subflow_fwd_bytes,
        request.features.subflow_bwd_bytes,
    ]

    features = np.array(feature_values).reshape(1, -1)

    prediction = app.state.classifier.predict_single(features)

    explanation = app.state.explainer.explain_prediction(features, top_k=3)

    return PredictionResponse(
        prediction=prediction["prediction"],
        confidence=prediction["confidence"],
        probabilities=prediction["probabilities"],
        explanation=explanation,
    )


@app.get("/stats")
async def get_stats():
    """Get pipeline statistics."""
    if app.state.pipeline is None:
        return {"error": "Pipeline not initialized"}

    return app.state.pipeline.get_stats()


@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(limit: int = 10):
    """Get recent alerts."""
    if app.state.pipeline is None:
        return []

    alerts = app.state.pipeline.alert_queue.get_all()
    return [
        AlertResponse(
            id=a.id,
            timestamp=a.timestamp,
            src_ip=a.src_ip,
            dst_ip=a.dst_ip,
            attack_type=a.attack_type,
            confidence=a.confidence,
            top_3_features=a.top_3_features,
            severity=a.severity,
        )
        for a in alerts[:limit]
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
