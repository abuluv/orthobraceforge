"""
OrthoBraceForge — Custom Exception Hierarchy
Domain-specific exceptions for medical device pipeline error handling.
"""
from typing import Any, Dict, Optional, Tuple


class OrthoError(Exception):
    """Base exception for all OrthoBraceForge domain errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.base_message = message
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.context:
            ctx = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.base_message} [{ctx}]"
        return self.base_message


class ComplianceError(OrthoError):
    """Regulatory or compliance check failure."""


class CADGenerationError(OrthoError):
    """CAD script generation or execution failure."""

    def __init__(self, message: str, engine: str = "",
                 context: Optional[Dict[str, Any]] = None):
        self.engine = engine
        ctx = context or {}
        if engine:
            ctx["engine"] = engine
        super().__init__(message, ctx)


class PrinterConnectionError(OrthoError):
    """OctoPrint connectivity or communication failure."""


class MeasurementValidationError(OrthoError):
    """Patient measurement data out of acceptable range."""

    def __init__(self, message: str, field: str = "", value: Any = None,
                 valid_range: Optional[Tuple[float, float]] = None,
                 context: Optional[Dict[str, Any]] = None):
        self.field = field
        self.value = value
        self.valid_range = valid_range
        ctx = context or {}
        if field:
            ctx["field"] = field
        if value is not None:
            ctx["value"] = value
        if valid_range is not None:
            ctx["valid_range"] = valid_range
        super().__init__(message, ctx)
