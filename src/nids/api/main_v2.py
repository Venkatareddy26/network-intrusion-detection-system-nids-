"""Production-grade FastAPI application with security and monitoring."""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import numpy as np
import time
from contextlib import asynccontextmanager

from config import config, ensure_directories
from src.nids.models.classifier import NIDSClassifier
from src.nids.models.explainer import SHAPExplainer
from src.nids.pipeline.processor import Pipeline, NetworkFlow
from src.nids.data.loader import FEATURE_COLUMNS
from src.nids.utils.logging import setup_logging, get_logger
from src.nids.utils.exceptions import (
    ModelNotLoadedException,
    InferenceException,
    InferenceTimeoutException,
)
from src.nids.utils.metrics import metrics_collector
from src.nids.utils.validators import validate_features, validate_ip_address
from src.nids.api.middleware import setup_middleware

# Setup logging
setup_logging(
    level=config.logging.level,
    log_format=config.logging.format,
    log_file=config.logging.log_file,
    max_bytes=config.logging.max_bytes,
    backup_count=config.logging.backup_count,
)

logger = get_logger(__name__)


# Pydantic Models
class FlowFeatures(BaseModel):
    """Network flow features."""

    flow_duration: float = Field(ge=0, description="Flow duration in microseconds")
    total_fwd_packets: int = Field(ge=0, description="Total forward packets")
    total_bwd_packets: int = Field(ge=0, description="Total backward packets")
    total_length_fwd_packets: float = Field(ge=0)
    total_length_bwd_packets: float = Field(ge=0)
    fwd_packet_length_mean: float = Field(ge=0)
    fwd_packet_length_std: float = Field(ge=0)
    bwd_packet_length_mean: float = Field(ge=0)
    bwd_packet_length_std: float = Field(ge=0)
    flow_bytes_per_sec: float = Field(ge=0)
    flow_packets_per_sec: float = Field(ge=0)
    flow_iat_mean: float = Field(ge=0)
    flow_iat_std: float = Field(ge=0)
    flow_iat_max: float = Field(ge=0)
    fwd_iat_total: float = Field(ge=0)
    fwd_iat_mean: float = Field(ge=0)
    fwd_iat_std: float = Field(ge=0)
    bwd_iat_total: float = Field(ge=0)
    bwd_iat_mean: float = Field(ge=0)
    bwd_iat_std: float = Field(ge=0)
    fwd_packets_per_sec: float = Field(ge=0)
    bwd_packets_per_sec: float = Field(ge=0)
    down_up_ratio: float = Field(ge=0)
    avg_packet_size: float = Field(ge=0)
    avg_fwd_segment_size: float = Field(ge=0)
    avg_bwd_segment_size: float = Field(ge=0)
    subflow_fwd_packets: int = Field(ge=0)
    subflow_bwd_packets: int = Field(ge=0)
    subflow_fwd_bytes: float = Field(ge=0)
    subflow_bwd_bytes: float = Field(ge=0)


class PredictionRequest(BaseModel):
    """Prediction request model."""

    features: FlowFeatures
    src_ip: str = Field(default="0.0.0.0", description="Source IP address")
    dst_ip: str = Field(default="0.0.0.0", description="Destination IP address")

    @validator("src_ip", "dst_ip")
    def validate_ip(cls, v):
        if not validate_ip_address(v):
            raise ValueError(f"Invalid IP address: {v}")
        return v


class PredictionResponse(BaseModel):
    """Prediction response model."""

    prediction: str
    confidence: float
    probabilities: Dict[str, float]
    explanation: Dict[str, Any]
    inference_time_ms: float
    request_id: Optional[str] = None


class AlertResponse(BaseModel):
    """Alert response model."""

    id: str
    timestamp: str
    src_ip: str
    dst_ip: str
    attack_type: str
    confidence: float
    top_3_features: List[Dict[str, Any]]
    severity: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float
    total_requests: int
    success_rate: float


class MetricsResponse(BaseModel):
    """Metrics response."""

    performance: Dict[str, Any]
    attack_distribution: Dict[str, int]


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting NIDS API server")
    ensure_directories()

    try:
        app.state.classifier = NIDSClassifier()
        app.state.classifier.load(config.model.model_path)

        app.state.explainer = SHAPExplainer(
            app.state.classifier.model, FEATURE_COLUMNS
        )

        def on_alert(alert):
            metrics_collector.record_attack(alert.attack_type)

        app.state.pipeline = Pipeline(
            app.state.classifier, app.state.explainer, on_alert
        )

        logger.info("Models loaded successfully")
        logger.info(f"Model version: {config.model.model_version}")

    except Exception as e:
        logger.error(f"Failed to load models: {e}", exc_info=True)
        app.state.classifier = None
        app.state.explainer = None
        app.state.pipeline = None

    yield

    # Shutdown
    logger.info("Shutting down NIDS API server")


# Create FastAPI app
app = FastAPI(
    title=config.app_name,
    description="Network Intrusion Detection System - Production API",
    version=config.app_version,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)


# Dependency for model availability
def get_classifier():
    """Dependency to check if classifier is loaded."""
    if app.state.classifier is None:
        raise ModelNotLoadedException("Model not loaded")
    return app.state.classifier


def get_pipeline():
    """Dependency to check if pipeline is available."""
    if app.state.pipeline is None:
        raise ModelNotLoadedException("Pipeline not initialized")
    return app.state.pipeline


# Routes
@app.get("/", tags=["General"])
async def root():
    """Root endpoint."""
    return {
        "name": config.app_name,
        "version": config.app_version,
        "status": "running",
        "environment": config.app_env,
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health():
    """Health check endpoint."""
    stats = metrics_collector.performance.get_stats()

    return HealthResponse(
        status="healthy" if app.state.classifier is not None else "degraded",
        model_loaded=app.state.classifier is not None,
        model_version=config.model.model_version,
        uptime_seconds=stats["uptime_seconds"],
        total_requests=stats["total_requests"],
        success_rate=stats["success_rate"],
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict(
    request: PredictionRequest,
    classifier: NIDSClassifier = Depends(get_classifier),
):
    """Predict attack type for a single network flow.
    
    Args:
        request: Prediction request with flow features
        classifier: Classifier dependency
        
    Returns:
        Prediction response with attack type and confidence
        
    Raises:
        HTTPException: If inference fails
    """
    start_time = time.time()

    try:
        # Convert features to numpy array
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

        # Validate features
        validate_features(features)

        # Predict
        prediction = classifier.predict_single(features)

        # Get explanation
        explanation = app.state.explainer.explain_prediction(features, top_k=3)

        inference_time_ms = (time.time() - start_time) * 1000

        # Check timeout
        if inference_time_ms > config.model.inference_timeout_ms:
            logger.warning(
                f"Inference exceeded timeout: {inference_time_ms:.2f}ms > {config.model.inference_timeout_ms}ms"
            )

        # Record metrics
        metrics_collector.performance.record_inference(inference_time_ms, success=True)

        return PredictionResponse(
            prediction=prediction["prediction"],
            confidence=prediction["confidence"],
            probabilities=prediction["probabilities"],
            explanation=explanation,
            inference_time_ms=inference_time_ms,
        )

    except Exception as e:
        inference_time_ms = (time.time() - start_time) * 1000
        metrics_collector.performance.record_inference(inference_time_ms, success=False)

        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "error_code": "INFERENCE_FAILED"},
        )


@app.get("/stats", tags=["Monitoring"])
async def get_stats(pipeline: Pipeline = Depends(get_pipeline)):
    """Get pipeline statistics."""
    return pipeline.get_stats()


@app.get("/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics():
    """Get performance metrics."""
    return MetricsResponse(
        performance=metrics_collector.performance.get_stats(),
        attack_distribution=metrics_collector.get_attack_distribution(),
    )


@app.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def get_alerts(
    limit: int = 10, pipeline: Pipeline = Depends(get_pipeline)
):
    """Get recent alerts.
    
    Args:
        limit: Maximum number of alerts to return
        pipeline: Pipeline dependency
        
    Returns:
        List of recent alerts
    """
    alerts = pipeline.alert_queue.get_all()
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


@app.post("/reset-metrics", tags=["Monitoring"])
async def reset_metrics():
    """Reset performance metrics."""
    metrics_collector.performance.reset()
    metrics_collector.reset_attack_counts()
    logger.info("Metrics reset")
    return {"message": "Metrics reset successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.nids.api.main_v2:app",
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
        reload=config.api.reload,
        log_level=config.logging.level.lower(),
    )
