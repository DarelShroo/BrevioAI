# Backend → Frontend map

Source of truth: FastAPI routers under `core/brevio_api`. Frontend lives in `frontend/`.

## Auth

| Capability | Endpoint | Auth | Frontend |
| ---------- | -------- | ---- | -------- |
| Login | `POST /auth/login` `{ identity, password }` → cookies httpOnly + `{ authenticated }` | Public | `LoginView`, `auth.store` |
| Register | `POST /auth/register` `{ username, email, password }` → token + folder | Public | `RegisterView` |
| Password recovery OTP | `POST /auth/password-recovery-handshake` `{ identity }` | Public | `PasswordRecoveryView` |
| Password reset | `POST /auth/password-recovery-verify` `{ email, password, otp }` | Public | `PasswordRecoveryView` |
| Logout | `POST /auth/logout` (revokes refresh, clears cookies) | cookie | `auth.store.logout` |
| Refresh | `POST /auth/refresh` | refresh cookie | `http.ts` interceptor |
| Route guard | `GET /users/me` with credentials | cookie | `router/guards.ts` |

States: idle / loading / error (credentials, validation, network) / success → redirect.

## Profile

| Capability | Endpoint | Frontend |
| ---------- | -------- | -------- |
| Current user | `GET /users/me` → id, username, email, user_credit, folder_id | `ProfileView` |
| Provider credentials list | `GET /user-credentials/{provider}` | `ProfileView` |
| Add credential | `POST /user-credentials` | `ProfileView` |
| Revoke credential | `DELETE /user-credentials/{id}` | `ProfileView` |

Not available: in-session password change, profile edit (username/email). Use recovery flow.

## Catalog (summary form options)

All require `X-API-KEY` (`VITE_API_KEY`).

| Endpoint | Used for |
| -------- | -------- |
| `GET /brevio/languages` | Language select (enum **names**, e.g. `SPANISH`) |
| `GET /brevio/models` | Model select |
| `GET /brevio/categories-styles` | Category → styles |
| `GET /brevio/output-formats` | Output format |
| `GET /brevio/summary-levels` | Summary depth |

Loaded by `catalog.store` → `SummaryParamsForm`.

## Summaries

| Capability | Endpoint | Frontend |
| ---------- | -------- | -------- |
| Estimate docs | `POST /brevio/estimate-documents` multipart | Summary → Documents tab |
| Submit docs | `POST /brevio/summary-documents` → `task_id`, `folder_entry_id` | Summary → Documents |
| Submit media | `POST /brevio/summary-media` (.mp3) | Summary → Media |
| YouTube playlist | `POST /brevio/summary-yt-playlist` JSON | Summary → YouTube |
| Poll job | `POST /users/entries` `{ entries_refs }` | `useJobPolling` |
| Download | `GET /brevio/download/{id}?format=&result_index=` | Summary + Store |

Multipart fields (docs/media): `files`, `language`, `model`, `category`, `style`, `format`, `summary_level`. Estimate also accepts optional `source_types`.

Job result statuses: `PROCESSING` | `COMPLETED` | `FAILED` (+ `phase`, errors).

## Store / history

| Capability | Endpoint | Frontend |
| ---------- | -------- | -------- |
| List all entries | `GET /users/entries` | `StoreView` |
| Detail / download | same entry payload + download endpoint | Store drawer |
| Delete entry | `DELETE /users/entries/{id}` | Store card/table/drawer |
| Entry metadata | `language`, `model`, `category`, `style`, `format`, `summary_level`, `source_type`, `created_at` | filters, cards, detail |
| Client filter/sort | *local only* | Store toolbar |

Not in backend: server pagination / search endpoint.

Media jobs now also return `folder_entry_id` (same as documents) so polling works immediately.

## UI library

**PrimeVue 4 (Aura)** — DataTable, FileUpload, Toast, Dialog, Select; fast SaaS build without Material lock-in.
