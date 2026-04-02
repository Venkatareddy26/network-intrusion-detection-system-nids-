"""Custom exception classes for NIDS application."""


class NIDSException(Exception):
    """Base exception for NIDS application."""

    def __init__(self, message: str, error_code: str = "NIDS_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ModelNotLoadedException(NIDSException):
    """Raised when model is not loaded."""

    def __init__(self, message: str = "Model not loaded"):
        super().__init__(message, "MODEL_NOT_LOADED")


class ModelLoadException(NIDSException):
    """Raised when model fails to load."""

    def __init__(self, message: str = "Failed to load model"):
        super().__init__(message, "MODEL_LOAD_FAILED")


class InferenceException(NIDSException):
    """Raised when inference fails."""

    def __init__(self, message: str = "Inference failed"):
        super().__init__(message, "INFERENCE_FAILED")


class InferenceTimeoutException(NIDSException):
    """Raised when inference exceeds timeout."""

    def __init__(self, message: str = "Inference timeout"):
        super().__init__(message, "INFERENCE_TIMEOUT")


class InvalidFeatureException(NIDSException):
    """Raised when feature validation fails."""

    def __init__(self, message: str = "Invalid features"):
        super().__init__(message, "INVALID_FEATURES")


class DataLoadException(NIDSException):
    """Raised when data loading fails."""

    def __init__(self, message: str = "Failed to load data"):
        super().__init__(message, "DATA_LOAD_FAILED")


class ConfigurationException(NIDSException):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Invalid configuration"):
        super().__init__(message, "INVALID_CONFIG")


class AuthenticationException(NIDSException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_FAILED")


class RateLimitException(NIDSException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class AlertQueueFullException(NIDSException):
    """Raised when alert queue is full."""

    def __init__(self, message: str = "Alert queue is full"):
        super().__init__(message, "ALERT_QUEUE_FULL")
