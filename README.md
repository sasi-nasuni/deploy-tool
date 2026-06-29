# Deploy Tool (Clean Rebuild)

This repository provides a separate backend and frontend app for deploying:
- nbn-daemon (`make deploy-rpm FILER=<ip>`)
- unity (`python python/tools/sync-dev.py --restart <ip>`)

## AWS Credential Behavior

- The UI always shows AWS fields:
  - Access Key ID
  - Secret Access Key
  - Session Token
- If cached CodeArtifact token is expired/missing, credentials are mandatory for nbn-daemon.
- If token is still valid, credentials are optional.
- If optional credentials are provided and valid, backend refreshes token cache with fresh TTL.

## Run Backend

```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:5174 and talks to backend on http://localhost:8000.
