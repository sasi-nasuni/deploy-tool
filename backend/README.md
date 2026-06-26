# Backend Placeholder

Backend implementation is expected from issue `sasi-nasuni/deploy-tool#1`.

Integration requirements for backend wiring:
- Include CORS middleware allowing `http://localhost:3000` and `http://localhost:5173`.
- For production, serve `../frontend/dist` via `fastapi.staticfiles.StaticFiles` after API routes.
