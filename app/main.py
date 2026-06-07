"""
ScanUpload Python Example App
==============================
Demonstrates scan-upload-api-client integration using FastAPI.

- ScanUploadProxyMiddleware forwards /scanupload-api/* to the ScanUpload hub
  and injects a Keycloak bearer token on every request.
- GET /download-file/{session_id} streams the uploaded file back to the browser.

Run:
    pip install -r ../requirements.txt
    uvicorn main:app --port 7021 --reload
or:
    python main.py
"""

import io
import os
import zipfile
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

from scan_upload_api_client import (
    KeycloakClient,
    ScanUploadApiClient,
    ScanUploadProxyOptions,
    TokenProvider,
)
from scan_upload_api_client.middleware import ScanUploadProxyMiddleware

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Load .env from the project root (parent of this file's directory).
# Priority: SCANUPLOAD_DOTENV_PATH env var → .env next to this file → ../.env
_dotenv_path = os.getenv("SCANUPLOAD_DOTENV_PATH")
if _dotenv_path:
    load_dotenv(_dotenv_path)
else:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in your credentials."
        )
    return value


options = ScanUploadProxyOptions(
    target_base_url=os.getenv(
        "SCANUPLOAD_TARGET_BASE_URL", "https://hub.scanupload.net/api/front-end"
    ),
    route_prefix=os.getenv("SCANUPLOAD_ROUTE_PREFIX", "/scanupload-api"),
    token_route=os.getenv("SCANUPLOAD_TOKEN_ROUTE", "/scanupload-api/token"),
    strip_route_prefix=os.getenv("SCANUPLOAD_STRIP_ROUTE_PREFIX", "true").lower()
    == "true",
    request_timeout=int(os.getenv("SCANUPLOAD_REQUEST_TIMEOUT", "90")),
    keycloak_server_url=os.getenv(
        "KEYCLOAK_SERVER_URL", "https://identity.scanupload.net/"
    ),
    keycloak_realm=os.getenv("KEYCLOAK_REALM", "scanupload-hub"),
    keycloak_client_id=_require("KEYCLOAK_CLIENT_ID"),
    keycloak_client_secret=_require("KEYCLOAK_CLIENT_SECRET"),
)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Keycloak client and token provider; clean up on shutdown."""
    keycloak_client = KeycloakClient(options)
    token_provider = TokenProvider(keycloak_client, options)
    api_client = ScanUploadApiClient(
        base_url=os.getenv(
            "SCANUPLOAD_API_CLIENT_BASE_URL", "https://hub.scanupload.net"
        ),
        token_provider=token_provider,
    )

    app.state.keycloak_client = keycloak_client
    app.state.scan_upload_token_provider = token_provider
    app.state.api_client = api_client

    try:
        yield
    finally:
        await keycloak_client.close()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="ScanUpload Python Example", version="1.0.0", lifespan=lifespan)

# Proxy all /scanupload-api/* requests to the ScanUpload hub, automatically
# attaching a bearer token obtained from Keycloak.
app.add_middleware(ScanUploadProxyMiddleware, options=options)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    """Health-check / smoke-test endpoint."""
    return {"message": "ScanUpload API client is active"}


@app.get("/download-file/{session_id}")
async def download_file(session_id: str, request: Request):
    """
    Download file(s) uploaded in a ScanUpload session and stream them back
    to the browser.

    The client-app calls this via:  GET /api/download-file/{sessionId}
    Vite's dev proxy strips the /api prefix so the request arrives here as:
                                    GET /download-file/{sessionId}
    """
    api_client: ScanUploadApiClient = request.app.state.api_client

    output = io.BytesIO()
    files_received = False

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        async def collect_file(filename: str, content: bytes) -> None:
            nonlocal files_received
            zf.writestr(filename, content)
            files_received = True

        try:
            await api_client.download_async(session_id, collect_file)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download from ScanUpload hub: {exc}",
            ) from exc

    if not files_received:
        raise HTTPException(
            status_code=404,
            detail="No files found for this session.",
        )

    output.seek(0)
    return Response(
        content=output.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}.zip"',
        },
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ssl_certfile = os.getenv("UVICORN_SSL_CERTFILE") or None
    ssl_keyfile = os.getenv("UVICORN_SSL_KEYFILE") or None
    port = int(os.getenv("PORT", "7021"))

    scheme = "https" if (ssl_certfile and ssl_keyfile) else "http"
    print(f"Starting ScanUpload Python example on {scheme}://localhost:{port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
    )
