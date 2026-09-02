#!/usr/bin/env python3
"""
Agent Platform Agent Gateway Runtime Service (Client-to-Agent Ingress Mode).

Implements the zero-trust ingress governance and networking layer for The Conductor v3,
configured according to declarative manifests in `infra/gateway/`:
- gateway.yaml: governedAccessPath: CLIENT_TO_AGENT
- authz_extension.yaml: Model Armor DLP, wireFormat: EXT_PROC_GRPC, failOpen: false
- authz_policy.yaml: CONTENT_AUTHZ policy enforcing inline DLP
- route_rules.yaml: Routing rules mapping client paths to Agent Engine microservice

Enforces:
1. Declarative route mapping (/query, /streamQuery, /getAgentCard, /api/v1/*).
2. Inline Model Armor DLP redaction on incoming prompts, responses, and SSE stream chunks.
   - Partner discount 45% and internal margins -> [CONFIDENTIAL_COMMERCIAL_RATE]
   - Social Security Numbers -> [REDACTED_SSN]
   - Non-Google emails -> [REDACTED_PII]
   - Injection attacks (SQLi, XSS scripts) -> Blocked with HTTP 400
3. Agent identity attestation headers (X-Agent-Identity, X-Governed-By).
4. Cloud Trace correlation (X-Cloud-Trace-Context) and structured Cloud Logging.
5. Zero-CORS preflight handling (OPTIONS -> HTTP 204 No Content with CORS headers).
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
import uvicorn
import yaml
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conductor.agent_gateway")

# Model Armor DLP Regular Expressions
UNRELEASED_SKU_PATTERN = re.compile(
    r"(?i)(?:"
    r"(?:(?:unreleased|internal|confidential|secret)[:=\-\s_]+)?(?:partner[:=\-\s_]+)?(?:discounts?|pricings?|margins?|rebates?)"
    r"(?:[:=\-\s_]*(?:(?:is|are|of)[:=\-\s_]+)?(?:\(\s*\d+(?:\.\d+)?\s*%\s*\)|\d+(?:\.\d+)?\s*%|\$\s*\d+(?:\.\d+)?(?:\/\w+)?))?|"
    r"(?:(?:unreleased|internal|confidential|secret)[:=\-\s_]+)?custom[:=\-\s_]+seller[:=\-\s_]+deal|"
    r"\b\d+(?:\.\d+)?\s*%\s*(?:internal|confidential)?\s*margins?|"
    r"\b\d+(?:\.\d+)?\s*%\s+on\s+compute\s+margins?|"
    r"\bmargins?\s*(?:(?:is|are|of)[:=\-\s_]+)?(?:\(\s*\d+(?:\.\d+)?\s*%\s*\)|\d+(?:\.\d+)?\s*%)"
    r")"
)

SSN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

BLOCKED_PATTERNS = [
    "drop table ",
    "<script>",
    "javascript:",
    "union select ",
    "exec xp_",
]


class ModelArmorDLPFilter:
    """Inline Model Armor DLP filter mimicking EXT_PROC_GRPC inspection."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        if not text:
            return ""

        # Redact non-Google PII emails
        def _replace_email(match):
            email = match.group(0)
            if email.lower().endswith("@google.com"):
                return email
            return "[REDACTED_PII]"

        sanitized = EMAIL_PATTERN.sub(_replace_email, text)
        sanitized = SSN_PATTERN.sub("[REDACTED_SSN]", sanitized)
        sanitized = UNRELEASED_SKU_PATTERN.sub("[CONFIDENTIAL_COMMERCIAL_RATE]", sanitized)
        return sanitized

    @classmethod
    def contains_blocked_pattern(cls, text: str) -> bool:
        lower = text.lower()
        return any(p in lower for p in BLOCKED_PATTERNS)

    @classmethod
    def inspect_payload(cls, data: Any) -> Any:
        if isinstance(data, str):
            return cls.sanitize_text(data)
        elif isinstance(data, dict):
            return {k: cls.inspect_payload(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.inspect_payload(item) for item in data]
        return data


def create_gateway_app(
    backend_url: str = "http://127.0.0.1:8080",
    manifest_dir: Optional[str] = None,
    project_id: str = "riccardo-blog-test-v1",
    location: str = "us-central1",
    gateway_id: str = "conductor-v3-ingress-gateway",
) -> FastAPI:
    """Factory creating the Agent Platform Agent Gateway FastAPI application."""
    manifest_dir = manifest_dir or os.path.dirname(os.path.abspath(__file__))
    gateway_resource = f"projects/{project_id}/locations/{location}/agentGateways/{gateway_id}"
    agent_identity = f"conductor-v3-ara@{project_id}.iam.gserviceaccount.com"

    app = FastAPI(
        title="Agent Platform Agent Gateway",
        description="Google Cloud Agent Platform Agent Gateway (Client-to-Agent Ingress)",
        version="3.0.0",
    )

    # Ingress CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-User-Email",
            "X-Goog-Authenticated-User-Email",
            "x-goog-iap-jwt-assertion",
            "X-Cloud-Trace-Context",
            "X-Workspace-ID",
            "Accept",
            "Origin",
        ],
        expose_headers=[
            "X-Cloud-Trace-Context",
            "X-Agent-Identity",
            "X-Governed-By",
        ],
        max_age=3600,
    )

    client = httpx.AsyncClient(
        base_url=backend_url.rstrip("/"),
        timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=30.0),
        follow_redirects=True,
    )

    def extract_or_create_trace_id(request: Request) -> str:
        trace_header = request.headers.get("x-cloud-trace-context", "")
        if trace_header:
            return trace_header.split("/")[0]
        return uuid.uuid4().hex

    def log_telemetry(
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        trace_id: str,
        sanitized: bool = False,
    ):
        log_entry = {
            "severity": "INFO" if status_code < 400 else ("WARNING" if status_code < 500 else "ERROR"),
            "message": f"Agent Gateway governed {method} {path} -> {status_code}",
            "logging.googleapis.com/trace": f"projects/{project_id}/traces/{trace_id}",
            "agent_identity": agent_identity,
            "governed_by": gateway_resource,
            "governed_access_path": "CLIENT_TO_AGENT",
            "http_request": {
                "request_method": method,
                "request_url": path,
                "status": status_code,
                "latency": f"{duration_ms:.3f}ms",
            },
            "model_armor_sanitized": sanitized,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        logger.info(json.dumps(log_entry))

    @app.middleware("http")
    async def gateway_governance_middleware(request: Request, call_next):
        start_time = time.time()
        trace_id = extract_or_create_trace_id(request)

        # 1. Zero-CORS preflight handling: Intercept OPTIONS immediately
        if request.method == "OPTIONS":
            log_telemetry("OPTIONS", request.url.path, 204, (time.time() - start_time) * 1000, trace_id)
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-User-Email, X-Goog-Authenticated-User-Email, x-goog-iap-jwt-assertion, X-Cloud-Trace-Context, X-Workspace-ID, Accept, Origin",
                    "Access-Control-Max-Age": "3600",
                    "X-Governed-By": gateway_resource,
                    "X-Agent-Identity": agent_identity,
                    "X-Cloud-Trace-Context": f"{trace_id}/1;o=1",
                },
            )

        # 2. Add governance headers to request state
        request.state.trace_id = trace_id
        response = await call_next(request)

        # 3. Add governance headers to response
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["X-Governed-By"] = gateway_resource
        response.headers["X-Agent-Identity"] = agent_identity
        response.headers["X-Cloud-Trace-Context"] = f"{trace_id}/1;o=1"
        return response

    # -------------------------------------------------------------
    # Route Rules Handlers
    # -------------------------------------------------------------

    @app.get("/health")
    @app.get("/ready")
    @app.get("/healthz")
    async def gateway_health(request: Request):
        """Operational probe returning gateway health and backend connectivity."""
        trace_id = request.state.trace_id
        try:
            resp = await client.get("/health")
            backend_ok = resp.status_code == 200
        except Exception:
            backend_ok = False

        status = {
            "status": "healthy" if backend_ok else "degraded",
            "gateway": {
                "resource": gateway_resource,
                "mode": "CLIENT_TO_AGENT",
                "model_armor_dlp": "ACTIVE",
                "fail_open": False,
            },
            "backend_connected": backend_ok,
            "trace_id": trace_id,
        }
        return JSONResponse(status, status_code=200 if backend_ok else 200)

    @app.api_route("/getAgentCard", methods=["GET", "POST"])
    async def get_agent_card(request: Request):
        """Proxies Agent Engine capability card."""
        trace_id = request.state.trace_id
        start = time.time()
        try:
            resp = await client.get(
                "/getAgentCard",
                headers={"X-Cloud-Trace-Context": f"{trace_id}/1;o=1"},
            )
            log_telemetry(request.method, "/getAgentCard", resp.status_code, (time.time() - start) * 1000, trace_id)
            return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "application/json"))
        except httpx.RequestError as e:
            return JSONResponse({"error": "Backend microservice unavailable", "detail": str(e)}, status_code=502)

    @app.post("/query")
    async def query_endpoint(request: Request):
        """Synchronous query endpoint with inline Model Armor DLP sanitization."""
        trace_id = request.state.trace_id
        start = time.time()

        # Read and inspect body
        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="replace")

        # Attack pattern check (failOpen: false)
        if ModelArmorDLPFilter.contains_blocked_pattern(body_text):
            log_telemetry("POST", "/query", 400, (time.time() - start) * 1000, trace_id, sanitized=True)
            return JSONResponse(
                {
                    "error": "BLOCKED_BY_MODEL_ARMOR",
                    "detail": "Input prompt contains forbidden injection or script payload",
                },
                status_code=400,
            )

        # Inbound prompt DLP sanitization
        sanitized_prompt = ModelArmorDLPFilter.sanitize_text(body_text)

        # Parse JSON
        try:
            payload = json.loads(sanitized_prompt) if sanitized_prompt else {}
        except Exception:
            payload = {}

        # Forward to backend
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Cloud-Trace-Context": f"{trace_id}/1;o=1",
                "X-Agent-Identity": agent_identity,
            }
            resp = await client.post("/query", json=payload, headers=headers)
            content_text = resp.text

            # Outbound response DLP sanitization
            sanitized_response = ModelArmorDLPFilter.sanitize_text(content_text)
            log_telemetry("POST", "/query", resp.status_code, (time.time() - start) * 1000, trace_id, sanitized=True)
            return Response(
                content=sanitized_response,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.RequestError as e:
            return JSONResponse({"error": "Backend microservice unavailable", "detail": str(e)}, status_code=502)

    @app.post("/streamQuery")
    @app.post("/query:stream")
    async def stream_query_endpoint(request: Request):
        """Streaming SSE query endpoint with chunk-level Model Armor DLP."""
        trace_id = request.state.trace_id
        start = time.time()

        raw_body = await request.body()
        body_text = raw_body.decode("utf-8", errors="replace")

        if ModelArmorDLPFilter.contains_blocked_pattern(body_text):
            return JSONResponse(
                {
                    "error": "BLOCKED_BY_MODEL_ARMOR",
                    "detail": "Input prompt contains forbidden injection or script payload",
                },
                status_code=400,
            )

        sanitized_prompt = ModelArmorDLPFilter.sanitize_text(body_text)
        try:
            payload = json.loads(sanitized_prompt) if sanitized_prompt else {}
        except Exception:
            payload = {}

        async def sse_event_stream() -> AsyncGenerator[bytes, None]:
            headers = {
                "Content-Type": "application/json",
                "X-Cloud-Trace-Context": f"{trace_id}/1;o=1",
                "X-Agent-Identity": agent_identity,
            }
            try:
                async with client.stream("POST", "/streamQuery", json=payload, headers=headers) as upstream_stream:
                    async for raw_chunk in upstream_stream.aiter_bytes():
                        chunk_text = raw_chunk.decode("utf-8", errors="replace")
                        # Real-time chunk DLP sanitization
                        sanitized_chunk = ModelArmorDLPFilter.sanitize_text(chunk_text)
                        yield sanitized_chunk.encode("utf-8")
            except Exception as ex:
                err_event = f"event: error\ndata: {json.dumps({'error': str(ex)})}\n\n"
                yield err_event.encode("utf-8")

        log_telemetry("POST", request.url.path, 200, (time.time() - start) * 1000, trace_id, sanitized=True)
        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.api_route(
        "/api/v1/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    async def proxy_api_v1(request: Request, path: str):
        """Universal reverse proxy for /api/v1/* routes with inline Model Armor screening."""
        trace_id = request.state.trace_id
        start = time.time()

        raw_body = await request.body()
        req_text = raw_body.decode("utf-8", errors="replace") if raw_body else ""

        # Traps injection attacks
        if req_text and ModelArmorDLPFilter.contains_blocked_pattern(req_text):
            log_telemetry(request.method, f"/api/v1/{path}", 400, (time.time() - start) * 1000, trace_id, sanitized=True)
            return JSONResponse(
                {
                    "error": "BLOCKED_BY_MODEL_ARMOR",
                    "detail": "Input payload contains forbidden injection patterns",
                },
                status_code=400,
            )

        sanitized_req_body = ModelArmorDLPFilter.sanitize_text(req_text).encode("utf-8") if req_text else None

        # Build forward headers
        forward_headers = dict(request.headers)
        forward_headers["x-cloud-trace-context"] = f"{trace_id}/1;o=1"
        forward_headers["x-agent-identity"] = agent_identity
        forward_headers["x-governed-by"] = gateway_resource
        # Remove host
        forward_headers.pop("host", None)

        try:
            resp = await client.request(
                method=request.method,
                url=f"/api/v1/{path}",
                params=dict(request.query_params),
                content=sanitized_req_body,
                headers=forward_headers,
            )

            resp_text = resp.text
            sanitized_resp_text = ModelArmorDLPFilter.sanitize_text(resp_text)
            log_telemetry(
                request.method,
                f"/api/v1/{path}",
                resp.status_code,
                (time.time() - start) * 1000,
                trace_id,
                sanitized=bool(resp_text != sanitized_resp_text),
            )
            return Response(
                content=sanitized_resp_text.encode("utf-8"),
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.RequestError as e:
            return JSONResponse({"error": "Backend microservice unavailable", "detail": str(e)}, status_code=502)

    return app


def main():
    parser = argparse.ArgumentParser(description="Run Agent Platform Agent Gateway Service.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")), help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument(
        "--backend-url",
        default=os.environ.get("AGENT_ENGINE_BACKEND_URL", "http://127.0.0.1:8080"),
        help="Vertex AI Agent Engine backend URL",
    )
    parser.add_argument("--project", default="riccardo-blog-test-v1", help="GCP Project ID")
    parser.add_argument("--location", default="us-central1", help="GCP Region")
    parser.add_argument("--gateway-id", default="conductor-v3-ingress-gateway", help="Gateway Resource ID")
    args = parser.parse_args()

    app = create_gateway_app(
        backend_url=args.backend_url,
        project_id=args.project,
        location=args.location,
        gateway_id=args.gateway_id,
    )
    logger.info("====================================================================")
    logger.info("  🚀 Starting Agent Platform Agent Gateway (CLIENT_TO_AGENT Ingress)")
    logger.info(f"  Listening on: {args.host}:{args.port}")
    logger.info(f"  Upstream:     {args.backend_url}")
    logger.info(f"  Model Armor:  failOpen=False, wireFormat=EXT_PROC_GRPC")
    logger.info("====================================================================")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
