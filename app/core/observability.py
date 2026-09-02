import logging
import sys
from typing import Any
from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from app.core.config import settings

# Global tracer instance for use across application services
tracer = trace.get_tracer("conductor.v2.tracer")


def setup_observability(app: FastAPI) -> None:
    """
    Configures structured Google Cloud Logging correlated with X-Cloud-Trace-Context headers,
    and initializes OpenTelemetry Cloud Trace exporting across HTTP, database, and Vertex AI calls.
    """
    # 1. Initialize Google Cloud Logging if in production or GCP environment
    if settings.ENVIRONMENT == "production" and settings.VERTEX_AI_PROJECT != "local-dev-project":
        try:
            import google.cloud.logging
            client = google.cloud.logging.Client(project=settings.VERTEX_AI_PROJECT)
            client.setup_logging()
            logging.info("Google Cloud Logging structured logger successfully attached.")
        except Exception as e:
            logging.warning(f"Could not initialize Google Cloud Logging client: {e}")
    else:
        class TraceContextFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                if not hasattr(record, "trace_id"):
                    current_span = trace.get_current_span()
                    ctx = current_span.get_span_context() if current_span else None
                    record.trace_id = format(ctx.trace_id, "032x") if (ctx and ctx.is_valid) else "none"
                return True

        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(TraceContextFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] trace_id=%(trace_id)s %(message)s"))
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        # Avoid duplicate handlers
        if not root_logger.handlers:
            root_logger.addHandler(handler)
        logging.info("Using standard stdout logging for local development/testing.")

    # 2. Configure OpenTelemetry Tracer Provider with GCP Cloud Trace Exporter
    resource = Resource.create({
        "service.name": "conductor-v2",
        "cloud.project_id": settings.VERTEX_AI_PROJECT,
        "deployment.environment": settings.ENVIRONMENT,
    })
    provider = TracerProvider(resource=resource)

    if settings.ENVIRONMENT == "production" and settings.VERTEX_AI_PROJECT != "local-dev-project":
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
            exporter = CloudTraceSpanExporter(project_id=settings.VERTEX_AI_PROJECT)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logging.info("OpenTelemetry CloudTraceSpanExporter attached.")
        except Exception as e:
            logging.warning(f"Could not attach CloudTraceSpanExporter: {e}")

    trace.set_tracer_provider(provider)

    # 3. Instrument FastAPI automatically if instrumentation library is available
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logging.info("FastAPI OpenTelemetry instrumentation applied.")
    except Exception as e:
        logging.warning(f"FastAPI instrumentor could not be applied: {e}")

    # 4. Instrument SQLAlchemy async engine automatically if instrumentation is available
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from app.core.database import engine
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)
        logging.info("SQLAlchemy OpenTelemetry instrumentation applied.")
    except Exception as e:
        logging.warning(f"SQLAlchemy instrumentor could not be applied: {e}")


def log_structured_event(logger_instance: logging.Logger, event_name: str, payload: dict[str, Any], level: int = logging.INFO) -> None:
    """
    Helper function to emit structured logs cleanly correlated with active OpenTelemetry trace context.
    """
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context() if current_span else None

    trace_id = format(span_context.trace_id, "032x") if (span_context and span_context.is_valid) else "00000000000000000000000000000000"
    span_id = format(span_context.span_id, "016x") if (span_context and span_context.is_valid) else "0000000000000000"

    structured_record = {
        "event_name": event_name,
        "logging.googleapis.com/trace": f"projects/{settings.VERTEX_AI_PROJECT}/traces/{trace_id}",
        "logging.googleapis.com/spanId": span_id,
        "payload": payload,
    }
    logger_instance.log(level, f"[{event_name}] {payload}", extra=structured_record)
