# Introduction

[ScanUpload](https://app.scanupload.net/) enables the integration and the
ability to use QR codes to scan and upload files directly from a mobile device
to your webapp.

# ScanUpload Python Example

A FastAPI application that integrates the
[scan-upload-api-client](https://pypi.org/project/scan-upload-api-client/)
Python package to enable QR-code-based file uploads from a mobile device to your
web app.

## How it works

```
Mobile device  ──(QR scan)──►  ScanUpload Hub
                                     │
                        /scanupload-api/*  (proxied + bearer token injected)
                                     │
                               FastAPI (main.py)
                                     │
                         GET /download-file/{session_id}
```

- **`ScanUploadProxyMiddleware`** intercepts every `/scanupload-api/*` request,
  obtains a Keycloak bearer token, and forwards the request to the ScanUpload
  hub.
- **`GET /download-file/{session_id}`** downloads all files uploaded in a
  session and returns them as a single `.zip` archive.

---

## Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- A [ScanUpload account](https://app.scanupload.net/) with a **Client ID** and
  **Client Secret**

---

## Project structure

```
ScanUpload.Example.Python/
├── app/
│   └── main.py          # FastAPI application
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
└── README.md
```

---

## 1. Install Python dependencies

**PowerShell**

```powershell
cd path\to\ScanUpload.Example.Python
pip install -r requirements.txt
```

**Bash**

```bash
cd path/to/ScanUpload.Example.Python
pip install -r requirements.txt
```

This installs:

- `scan-upload-api-client[asgi]` — the ScanUpload client with FastAPI/uvicorn
  extras
- `python-dotenv` — `.env` file loading

---

## 2. Configure environment variables

Copy the example file and fill in your credentials:

**PowerShell**

```powershell
Copy-Item .env.example .env
```

**Bash**

```bash
cp .env.example .env
```

Open `.env` and set the two required values:

```ini
KEYCLOAK_CLIENT_ID=your-client-id
KEYCLOAK_CLIENT_SECRET=your-client-secret
```

All available settings:

| Variable                         | Default                                    | Description                       |
| -------------------------------- | ------------------------------------------ | --------------------------------- |
| `KEYCLOAK_CLIENT_ID`             | _(required)_                               | Your ScanUpload client ID         |
| `KEYCLOAK_CLIENT_SECRET`         | _(required)_                               | Your ScanUpload client secret     |
| `KEYCLOAK_SERVER_URL`            | `https://identity.scanupload.net/`         | Keycloak server URL               |
| `KEYCLOAK_REALM`                 | `scanupload-hub`                           | Keycloak realm                    |
| `KEYCLOAK_SCOPE`                 | `openid profile email scanupload.hub`      | Token scopes                      |
| `SCANUPLOAD_TARGET_BASE_URL`     | `https://hub.scanupload.net/api/front-end` | ScanUpload hub proxy target       |
| `SCANUPLOAD_ROUTE_PREFIX`        | `/scanupload-api`                          | Route prefix exposed by this app  |
| `SCANUPLOAD_TOKEN_ROUTE`         | `/scanupload-api/token`                    | Token endpoint route              |
| `SCANUPLOAD_STRIP_ROUTE_PREFIX`  | `true`                                     | Strip prefix before forwarding    |
| `SCANUPLOAD_REQUEST_TIMEOUT`     | `90`                                       | Proxy request timeout (seconds)   |
| `SCANUPLOAD_API_CLIENT_BASE_URL` | `https://hub.scanupload.net`               | Base URL for file downloads       |
| `PORT`                           | `7021`                                     | Port the Python server listens on |
| `UVICORN_SSL_CERTFILE`           | _(optional)_                               | Path to TLS certificate file      |
| `UVICORN_SSL_KEYFILE`            | _(optional)_                               | Path to TLS private key file      |
| `SCANUPLOAD_DOTENV_PATH`         | _(optional)_                               | Override `.env` file path         |

> **Warning:** Never commit `.env` to source control. It contains secrets.

---

## 3. Create a TLS certificate (recommended)

Running over HTTPS is recommended. Use **mkcert** to create a locally-trusted
certificate without browser warnings.

### Install mkcert

**PowerShell**

```powershell
# Using winget
winget install FiloSottile.mkcert

# Or using Chocolatey
choco install mkcert
```

**Bash**

```bash
# Using Homebrew (macOS/Linux)
brew install mkcert

# Or on Linux with apt
sudo apt install mkcert
```

### Install the local Certificate Authority (one-time)

```powershell
mkcert -install
```

This adds a trusted CA to your system and browser stores so certificates signed
by it are trusted automatically.

### Generate a certificate for localhost

Run this from the project root so the files are stored alongside the project:

**PowerShell**

```powershell
cd path\to\ScanUpload.Example.Python
mkcert localhost 127.0.0.1
```

**Bash**

```bash
cd path/to/ScanUpload.Example.Python
mkcert localhost 127.0.0.1
```

Two files are created:

- `localhost+1.pem` — certificate
- `localhost+1-key.pem` — private key

### Add the certificate paths to `.env`

```ini
UVICORN_SSL_CERTFILE=path/to/ScanUpload.Example.Python/localhost+1.pem
UVICORN_SSL_KEYFILE=path/to/ScanUpload.Example.Python/localhost+1-key.pem
```

When both values are set the server starts on `https://localhost:7021`.

---

## 4. Run the backend

**PowerShell**

```powershell
cd path\to\ScanUpload.Example.Python
python app/main.py
```

**Bash**

```bash
cd path/to/ScanUpload.Example.Python
python app/main.py
```

Expected output:

```
Starting ScanUpload Python example on https://localhost:7021
INFO:     Started server process [...]
INFO:     Uvicorn running on https://0.0.0.0:7021 (Press CTRL+C to quit)
```

Alternatively, use uvicorn directly (useful for `--reload` during development):

**PowerShell**

```powershell
cd app
uvicorn main:app --port 7021 --reload `
  --ssl-certfile ../localhost+1.pem `
  --ssl-keyfile ../localhost+1-key.pem
```

**Bash**

```bash
cd app
uvicorn main:app --port 7021 --reload \
  --ssl-certfile ../localhost+1.pem \
  --ssl-keyfile ../localhost+1-key.pem
```

Verify the backend is running:

**PowerShell**

```powershell
Invoke-RestMethod https://localhost:7021/
# {"message":"ScanUpload API client is active"}
```

**Bash**

```bash
curl https://localhost:7021/
# {"message":"ScanUpload API client is active"}
```

---

## 5. API endpoints

| Method | Path                          | Description                            |
| ------ | ----------------------------- | -------------------------------------- |
| `GET`  | `/`                           | Health check                           |
| `ANY`  | `/scanupload-api/*`           | Proxied to ScanUpload hub (middleware) |
| `GET`  | `/download-file/{session_id}` | Download uploaded files as a `.zip`    |

### Interactive API docs

While the server is running, visit:

- Swagger UI: [https://localhost:7021/docs](https://localhost:7021/docs)
- ReDoc: [https://localhost:7021/redoc](https://localhost:7021/redoc)

---

## Troubleshooting

### Port already in use

```
[Errno 10048] error while attempting to bind on address ('0.0.0.0', 7021)
```

Find and stop the process occupying the port:

**PowerShell**

```powershell
# Find the PID
netstat -ano | findstr :7021

# Stop it (replace 12345 with the actual PID)
Stop-Process -Id 12345 -Force
```

**Bash**

```bash
# Find the PID
lsof -i :7021

# Stop it (replace 12345 with the actual PID)
kill 12345
```

### Missing environment variable

```
RuntimeError: Required environment variable 'KEYCLOAK_CLIENT_ID' is not set.
```

Ensure `.env` exists in the project root and contains `KEYCLOAK_CLIENT_ID` and
`KEYCLOAK_CLIENT_SECRET`.

### Token provider not found

```
ScanUploadProxyException: Token provider not found on app.state.scan_upload_token_provider
```

The middleware requires the token provider to be stored on
`app.state.scan_upload_token_provider`. Verify this is set in `lifespan()`
inside `main.py`.

### Certificate not trusted

If you see browser SSL warnings, re-run `mkcert -install` to ensure the local CA
is trusted, then regenerate the certificate.
