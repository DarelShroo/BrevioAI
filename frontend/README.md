# Brevio Frontend

Vue 3 + TypeScript + Vite + Pinia + Vue Router + PrimeVue (Aura) client for the Brevio API.

## Setup

```bash
cd frontend
cp .env.example .env
npm install
```

### Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000` | Backend base URL (Axios `baseURL`) |
| `VITE_API_KEY` | `local_api_key_123` | Sent as `X-API-KEY` on catalog GETs (`/brevio/languages`, models, categories-styles, output-formats, summary-levels) |
| `VITE_OUT_DIR` | `dist` | Optional Vite `outDir` (`process.env.VITE_OUT_DIR`) |

Inventario de **todas** las variables (backend incluido): [docs/ENVIRONMENT.md](../docs/ENVIRONMENT.md).

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Vite dev server on port 3000 |
| `npm run type-check` | `vue-tsc --build` |
| `npm run lint` | ESLint (auto-fix) |
| `npm run format` | Prettier for `src/` and `e2e/` |
| `npm run test:unit` | Vitest (jsdom); add `-- --run` for CI |
| `npm run test:e2e` | Playwright Chromium (builds + previews on `:4173`) |
| `npm run test:e2e:ui` | Playwright UI mode |
| `npm run build` | Type-check + production build |
| `npm run preview` | Preview production build |

First Playwright run may need browsers:

```bash
npx playwright install chromium
```

## Backend → frontend map

See [docs/BACKEND_FRONTEND_MAP.md](./docs/BACKEND_FRONTEND_MAP.md) for the full endpoint → screen → state matrix.

## Architecture

```
src/
  main.ts, App.vue
  assets/styles/          Design tokens + global CSS
  router/                 Routes + auth/guest guards
  types/                  API / auth / user / brevio contracts
  services/               Axios HTTP + domain API clients
  stores/                 Pinia auth + catalog stores
  composables/            Async state, job polling, toast helpers
  layouts/                Auth shell + app shell (sidebar/drawer)
  components/             Reusable UI pieces
  views/                  Login, register, recovery, summary, store, profile
  utils/                  validation, error parsing, entry helpers
```

### Pages

| Route | Guard | Purpose |
| --- | --- | --- |
| `/auth/login` | guest | Sign in |
| `/auth/register` | guest | Create account |
| `/auth/password-recovery` | — | Password recovery handshake/verify |
| `/summary` | auth | Estimate + submit documents/media/YouTube; poll job |
| `/store` | auth | Folder entry history + download |
| `/profile` | auth | `GET /users/me` + optional provider credentials |

## Auth

- Login / register / refresh set httpOnly cookies (`brevio_access`, `brevio_refresh`). JSON returns `{ authenticated: true }` and never the JWT.
- Axios uses `withCredentials`. The access cookie is sent automatically; there is no `localStorage` token.
- A 401 on a non-auth route calls `POST /auth/refresh` once, then retries.
- Logout is `POST /auth/logout` (revokes the refresh session and clears cookies).
- Route guards call `GET /users/me` to see if the cookie session is valid.

## API layer

- `services/http.ts` — shared Axios instance, auth + error → `ApiError`.
- `withApiKey()` — catalog endpoints need `X-API-KEY`.
- Domain modules:
  - `auth.service` — login, register, refresh, logout, session, password recovery
  - `user.service` — `GET /users/me`, `GET|POST /users/entries`
  - `brevio.service` — catalogs, estimate, summary submit, download
  - `credentials.service` — provider API keys
- Summary documents: multipart `files` + `language`, `model`, `category`, `style`, `format`, `summary_level` → `task_id` + `folder_entry_id`.
- Job progress: `POST /users/entries` with `{ entries_refs }` (also list via GET).
- Download: `GET /brevio/download/{folder_entry_id}?format=&result_index=`.

Catalog response shapes are normalized on the client (formats may be `{ output_format_types }` or arrays; levels `{ summary_levels }` or arrays).

## Testing

- **Vitest**: utils (`jwt`, `validation`, `errors`, `entries`), stores, services (mocked Axios), `useJobPolling`, LoginView / StatusBadge / StateBlock.
- **Playwright**: `page.route` API mocks for register → app, login → profile, summary submit → poll COMPLETED, store entries, logout redirect, login error, empty store, failed job, validation, network failure.
