# RAG Platform — Frontend (v1)

React frontend for the Agentic RAG Platform. Consumes the v1 FastAPI
backend (see backend repo's `API.md`).

v1 scope: single fixed project, PDF upload + document list, multiple
conversations per project, chat with citation rendering. No auth, no
streaming. See backend's `v1-frontend-requirements.md` for full scope.

Status: **WIP — scaffolding stage, no screens built yet.**

## Stack
- React + Vite
- react-router-dom
- @tanstack/react-query
- Plain CSS
- ESLint + Prettier

## Getting started

\`\`\`bash
npm install
npm run dev
\`\`\`

Requires the backend running at the URL set in `.env.development`
(defaults to `http://localhost:8000`).

## Project structure

\`\`\`
src/
  api/         # fetch wrappers, one module per resource
  components/  # shared, reusable UI (no data fetching)
  pages/       # route-level containers (own their data fetching)
  App.jsx      # routes + layout
  main.jsx     # React Query provider + router setup
\`\`\`

## Scripts

- `npm run dev` — start dev server
- `npm run build` — production build
- `npm run lint` — run ESLint

## Deployment

Built with Vite, served via nginx in production (see `Dockerfile`,
`nginx.conf` — WIP).