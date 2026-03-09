# Dev Log

## 2026-03-09 Stage 1 Setup
- Why: Stage 1 requires a full project bootstrap across backend, frontend, auth, responsive layout, and TDD coverage in an otherwise empty repository.
- How: Initialized task tracking files and prepared the repo for backend/frontend scaffolding, documentation updates, and verification.
- Result: Planning artifacts created. Implementation and verification pending.

## 2026-03-09 Stage 1 Implementation
- Why: The repository needed a runnable Stage 1 baseline covering authentication, protected API access, frontend navigation security, and mobile-first responsive layout.
- How: Added Flask app factory wiring in `backend/app.py`, database/JWT extensions in `backend/extensions.py`, and the extensible `User` model in `backend/models.py`. Wrote pytest fixtures and auth tests under `backend/tests/`. Built a Vue 3 + Vite + Tailwind frontend with router guard in `frontend/src/router/index.js`, axios token injection in `frontend/src/api/http.js`, and responsive shell navigation in `frontend/src/layouts/MainLayout.vue`. Updated `README.md` with structure and startup instructions.
- Result: Backend tests pass via `python3 -m pytest backend/tests`. Frontend production build passes via `npm run build` in `frontend/`. Also fixed two environment-driven issues during verification: Werkzeug default `scrypt` hashing was incompatible with the local Python build, so password hashing now uses `pbkdf2:sha256`; JWT identity encoding was adjusted to use a string subject plus claims to satisfy token validation.

## 2026-03-09 Stage 1 Acceptance Fixes
- Why: Runtime acceptance exposed two practical blockers that unit tests alone did not catch: `python3 backend/app.py` failed due to package import path resolution, and a fresh app instance had no initial user to log in with.
- How: Updated `backend/app.py` to support direct script execution by appending the project root to `sys.path` when needed, and added `ensure_default_admin()` to seed a default admin user from config or environment on startup. Updated pytest fixtures to validate the seeded-admin path and added an explicit bootstrap test.
- Result: `python3 -m pytest backend/tests` now passes with 3 tests. Runtime acceptance succeeded with the backend serving on `http://127.0.0.1:5000` and the frontend on `http://127.0.0.1:5173/`. Verified `POST /api/v1/auth/login` returns `200` plus JWT for `admin / Admin@123456`, and verified `GET /api/v1/inventory/test` without a token returns `401`.

## 2026-03-09 Stage 2 TDD Start
- Why: Stage 2 adds inventory domain rules that are easy to get subtly wrong, especially batch merge behavior and product-level stock derivation.
- How: Added auth-enabled pytest fixtures and introduced `backend/tests/test_inventory.py` to codify product creation, inbound stock creation, and same-expiry batch merge expectations before implementing the new models and APIs.
- Result: Test definitions are in place and ready to drive the backend implementation.

## 2026-03-09 Stage 2 Backend Domain
- Why: The system needed a persistent product archive and batch-based stock ledger so inventory can be derived from remaining batch quantities instead of mutating product totals directly.
- How: Reworked `backend/models.py` to add a reusable `ExtraDataMixin`, plus `Product` and `Batch` entities with relationships, stock aggregation, and serialized date output. Extended `backend/app.py` with product listing/creation endpoints and inbound inventory logic that resolves by `hb_code` or `barcode`, then merges or creates batches using `hb_code + expiry_date`.
- Result: Backend implementation is in place and ready for rule verification through the Stage 2 pytest suite.

## 2026-03-09 Stage 2 Frontend Workflow
- Why: Stage 2 also needs a usable UI surface for product archiving and mobile-first inbound operations; backend APIs alone are not enough for acceptance.
- How: Added a dedicated `/products` route and navigation entry, then implemented `frontend/src/views/ProductsView.vue` for searchable product listing plus archive creation. Replaced the placeholder inbound page with a step-based H5 flow in `frontend/src/views/InboundView.vue` that resolves products by barcode/HB code, routes missing items to the product center, and submits batch data to the inbound API.
- Result: Frontend implementation is ready for build verification against the new Stage 2 routes and components.

## 2026-03-09 Stage 2 Verification & Docs
- Why: Stage 2 needs a clear handoff baseline so later stages can build on the exact batch model, API contract, and UI entry points without re-discovering context.
- How: Ran the full backend test suite and frontend production build, then updated `README.md` and `tasks/todo.md` to reflect the new product center, inbound workflow, and batch merge behavior.
- Result: `python3 -m pytest backend/tests` passes with 6 tests, `npm run build` passes, and project documentation now reflects the Stage 2 system state.
