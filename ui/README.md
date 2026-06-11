# Sandalwood AI Mixer — Web UI

React 19 + Vite frontend for the Sandalwood AI Mixer. All project documentation
lives in the root [README.md](../README.md) — that file is the single source of truth.

```bash
npm install
npm run dev      # http://localhost:3000 (proxies /api to the backend on :8000)
npm run lint
npm run build
```

Set `VITE_API_BASE` if the backend runs on another host (see `src/api.js`).
