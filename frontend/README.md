# Frontend — HousePrice Insight

React + Vite SPA. Development server: `http://localhost:3000`.

## Development

```powershell
cd frontend
npm install
npm run dev
```

Uses `BrowserRouter` (HTML5 history). Routes are client-side only.

## Tests

```powershell
cd frontend
npm test
```

This runs the Node built-in test runner:

```text
node --test "tests/**/*.test.js"
```

No extra test framework dependency is required.

## Production build

```powershell
cd frontend
npm run build
```

Output directory:

```text
frontend/dist/
```

The build must include `dist/index.html` plus hashed assets under `dist/assets/`.

Set `VITE_API_URL` to the production API origin before building (see root `README.md` and `.env.example`).

For a production deploy build that must reject localhost API URLs:

```powershell
cd frontend
$env:VITE_API_URL="https://api.example.com"
$env:APP_ENV="production"
npm run build
```

## Static hosting — SPA rewrite requirement

This app uses **React Router `BrowserRouter`**. Nested paths such as `/market` or `/estimate` are not real files on disk.

**Production static hosting must rewrite unknown / non-file requests to `/index.html`.**

Example:

1. User opens `https://production-domain.example/market` (direct visit or refresh).
2. The host must serve `index.html` (HTTP 200), not a 404 for a missing `/market` file.
3. React Router then renders the `/market` route in the browser.

Without that rewrite, deep links and refreshes fail on static hosts even though in-app navigation works.

Do **not** switch to `HashRouter` for this project.

Vercel: `frontend/vercel.json` rewrites all routes to `/index.html`. Deploy the contents of `frontend/dist/` (or point the Vercel project root at `frontend` with the Vite build output). Other hosts still need an equivalent SPA fallback.

## Local preview of the production build

Vite’s built-in preview (no extra packages):

```powershell
cd frontend
npm run build
npm run preview
```

`vite preview` serves `dist/` and applies history fallback for nested routes locally. A real deployment still needs the host’s rewrite rule configured explicitly.

## Routes (unchanged)

| Path | Notes |
|---|---|
| `/` | Landing |
| `/estimate` | Price estimate |
| `/compare` | Compare properties |
| `/affordability` | Affordability |
| `/market` | Market insights |
| `/how-it-works` | How it works |
| `/history` | Prediction history |
| `/login` | Login |
| `/register` | Register |
| `/forgot-password` | Forgot password |
| `/reset-password` | Reset password |
| `/dashboard` | Redirects to `/history` |

Unknown paths redirect to `/`.

## SPA hosting checklist (platform-neutral)

- [ ] Deploy the contents of `frontend/dist/`
- [ ] Serve the site from the web root (Vite `base` is `/`; do not change unless deploying under a subpath)
- [ ] Rewrite non-file routes to `/index.html`
- [ ] Keep API calls on `VITE_API_URL` (backend is separate; CORS must allow the frontend origin)
