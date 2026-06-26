# Deploy Tool

Web-based deployment tool for `nbn-daemon` and `unity` repositories.

See the full project context in `functional_requirements.ipynb`.

## Repository Structure

```text
deploy-tool/
├── README.md
├── .env.example
├── .gitignore
├── functional_requirements.ipynb
├── backend/
└── frontend/
```

> `backend/` and `frontend/` are currently placeholders in this integration PR and are expected to be populated by their dedicated implementation issues.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for nbn-daemon RPM builds)
- Git
- uv (Python package manager)
- SSH key with access to filers (port 222)
- GitHub Personal Access Token

## Quick Start

### 1) Clone this repo

```bash
git clone https://github.com/sasi-nasuni/deploy-tool.git
cd deploy-tool
```

### 2) Set up environment

```bash
cp .env.example .env
# Edit .env with your values (at minimum: GITHUB_PAT)
```

### 3) Start backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 4) Start frontend

```bash
cd frontend
npm install
npm run dev
```

### 5) Open

- <http://localhost:5173>

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_PAT` | Yes | — | GitHub Personal Access Token used for cloning `nasuni/nbn-daemon` and `nasuni/unity`. |
| `REPOS_BASE_PATH` | No | `~/.deploy_tool/repos` | Base directory where target repos are cloned locally. |
| `NBN_DAEMON_REPO_URL` | No | `https://github.com/nasuni/nbn-daemon.git` | Source repository URL for nbn-daemon. |
| `UNITY_REPO_URL` | No | `https://github.com/nasuni/unity.git` | Source repository URL for Unity. |
| `DEPLOY_TIMEOUT_SECONDS` | No | `1800` | Deployment timeout in seconds (30 minutes). |
| `SERVER_PORT` | No | `8000` | Backend server port. |

## Usage

1. Select repo (`nbn-daemon` or `unity`)
2. Select branch from dropdown
3. Enter filer IP
4. Click **Deploy**
5. Monitor logs in real-time

Bookmark the URL (query params) to preserve repo/branch/filer values for one-click deploys.

## Development Wiring

### Backend CORS (FastAPI)

Configure CORS in `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Frontend proxy (Vite)

Configure Vite to proxy `/api` to FastAPI during development:

```ts
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

## Production Build Approach

Build frontend assets:

```bash
cd frontend
npm run build
```

Then have FastAPI serve the built app in `backend/app/main.py` (after API routes):

```python
from fastapi.staticfiles import StaticFiles

app.mount('/', StaticFiles(directory='../frontend/dist', html=True), name='frontend')
```

Run backend only:

```bash
uv run uvicorn app.main:app --port 8000
```

## Architecture

- React frontend (UI + WebSocket log display)
- FastAPI backend (deploy orchestration + API + WebSocket)
- Local checked-out `nbn-daemon` / `unity` repos under `REPOS_BASE_PATH`

For detailed functional requirements and flows, see:
- `functional_requirements.ipynb`
