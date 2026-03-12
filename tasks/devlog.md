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

## 2026-03-09 Stage 3 TDD Start
- Why: Stage 3 changes stock semantics from plain on-hand quantities to base-unit conversion, sellable inventory, and FIFO reservations; these rules need to be locked down before implementation.
- How: Extended `backend/tests/test_inventory.py` with new tests for purchase-unit conversion on inbound, reservation impact on sellable stock, and channel mapping lookup by external SKU.
- Result: Stage 3 behavior is now specified as executable tests and ready to drive the backend changes.

## 2026-03-09 Stage 3 Backend Domain
- Why: Unit conversion, reservation, and cross-channel SKU resolution all belong to the inventory domain layer; if they are not modeled consistently, downstream sellable stock numbers will drift.
- How: Extended `Product` with `base_unit`, `purchase_unit`, and `conversion_rate`; extended `Batch` with `reserved_quantity`; and added `ChannelMapping` in `backend/models.py`. Updated `backend/app.py` to normalize inbound quantities into base units, expose product detail with stock summaries, reserve inventory FIFO by earliest expiry date, and create/list/lookup channel mappings.
- Result: Backend now has a single source of truth for total, reserved, and sellable stock, and the Stage 3 APIs are in place for verification.

## 2026-03-09 Stage 3 Frontend Workflow
- Why: The new stock semantics need visible UI surfaces, otherwise reservation and channel mapping remain backend-only features that operators cannot use.
- How: Updated `frontend/src/views/ProductsView.vue` to capture unit metadata and link into a new detail page, added `frontend/src/views/ProductDetailView.vue` to display total/reserved/sellable stock plus reservation actions, added `frontend/src/views/ChannelMappingsView.vue` for manual external SKU binding, and extended `frontend/src/views/InboundView.vue` with base-vs-purchase unit selection.
- Result: Stage 3 frontend entry points are in place and wired to the new backend APIs.

## 2026-03-09 Stage 3 Verification & Docs
- Why: Stage 3 changes persisted schema and inventory semantics, so the handoff needs both verification evidence and an explicit note about the absence of migrations.
- How: Ran the full backend test suite and frontend production build, then updated `README.md` and `tasks/todo.md` with the new model fields, APIs, pages, and SQLite schema refresh note.
- Result: `python3 -m pytest backend/tests` passes with 9 tests, `npm run build` passes, and the documentation now reflects the Stage 3 system state and local schema caveat.

## 2026-03-09 Stage 4 TDD Start
- Why: CSV import and expiry warning logic both affect persisted inventory state, so they need explicit tests before implementation to avoid silent stock drift.
- How: Added Stage 4 tests for missing expiry date fallback, CSV purchase-unit conversion, and warning classification for a batch expiring tomorrow.
- Result: Stage 4 behavior is specified in tests and ready to drive the import service and dashboard APIs.

## 2026-03-09 Stage 4 Backend Import & Monitoring
- Why: Stage 4 needs a repeatable bulk initialization path and a single expiry-monitoring source of truth for both dashboard cards and detailed batch views.
- How: Added `backend/services/import_service.py` to parse CSV files, default missing expiry dates to `2099-12-31`, normalize purchase units into base units, and apply `accumulate` or `overwrite` merge rules. Extended `backend/app.py` with import preview/commit endpoints, dashboard stats, and expiry report APIs using shared expiry-status logic.
- Result: Backend now supports CSV-driven inventory initialization and expiry analytics, and the new Stage 4 tests pass against those flows.

## 2026-03-09 Stage 4 Frontend Dashboard & Import
- Why: The CSV import and expiry warning features need visible operator workflows; otherwise Stage 4 would remain backend-only.
- How: Replaced the placeholder home page with live dashboard cards tied to `/api/v1/dashboard/stats`, upgraded `frontend/src/views/StockView.vue` into a filterable expiry report with status-colored rows, added `frontend/src/views/DataManagementView.vue` for upload/preview/save import flow, and exposed the new data route in navigation.
- Result: Stage 4 frontend entry points are wired to the backend import and monitoring APIs and ready for build verification.

## 2026-03-09 Stage 4 Verification & Docs
- Why: Stage 4 adds both new workflows and new schema-dependent behavior, so the handoff needs explicit verification evidence and updated operator-facing docs.
- How: Ran the full backend test suite and frontend production build, then updated `README.md` and `tasks/todo.md` with import behavior, dashboard endpoints, expiry report filtering, and the new data-management UI route.
- Result: `python3 -m pytest backend/tests` passes with 12 tests, `npm run build` passes, and the documentation now reflects the complete Stage 4 system state.

## 2026-03-09 Stage 5 TDD Start
- Why: Stage 5 changes inventory from standalone reserve operations to a full order lifecycle with persistent status and RBAC, which is easy to break if implemented piecemeal.
- How: Extended test fixtures with a seeded `staff` user and added tests for channel-driven order sync, admin-only export restrictions, and fulfill-time stock deduction plus OUT transaction creation.
- Result: Stage 5 requirements are now encoded as executable tests and ready to drive the order and permission implementation.

## 2026-03-09 Stage 5 Backend Domain
- Why: The system needed persistent order state and transaction traces to support a true reserve-to-fulfill lifecycle; at the same time, export/import and mapping actions needed hard server-side role gates.
- How: Added `SalesOrder`, `OrderAllocation`, and `InventoryTransaction` models in `backend/models.py`; introduced `admin_required` in `backend/app.py`; implemented order sync, order listing, fulfillment, and export endpoints; and restricted import, export, and channel-mapping creation to admin users.
- Result: Stage 5 backend now has a persisted order lifecycle, OUT transaction records, and enforceable RBAC boundaries ready for verification.

## 2026-03-09 Stage 5 Frontend RBAC & Order Console
- Why: Stage 5 also requires operator-facing workflows for order processing, role-based menu exposure, report download, and quick remediation when H5 scans return an unknown code.
- How: Added local auth session helpers under `frontend/src/auth/session.js`, persisted the logged-in user in `frontend/src/views/LoginView.vue`, and extended `frontend/src/router/index.js` plus `frontend/src/layouts/MainLayout.vue` to hide admin-only routes and block direct navigation to `财务统计` and `用户设置` for staff. Added `frontend/src/views/OrdersView.vue`, `frontend/src/views/FinanceView.vue`, and `frontend/src/views/SettingsView.vue`, expanded `frontend/src/views/DataManagementView.vue` with CSV/XLSX report download actions, and added an admin-only quick channel-mapping entry point in `frontend/src/views/InboundView.vue`.
- Result: The frontend now covers the Stage 5 order loop, admin-only report operations, and UI-level role gating expected for Web and H5 flows.

## 2026-03-09 Stage 5 Verification & Runtime Export Check
- Why: Stage 5 introduces a runtime-only dependency path (`pandas`/`openpyxl`) that the existing pytest suite did not exercise on the happy path, so a compile-only check would be insufficient.
- How: Installed the backend requirements from `backend/requirements.txt`, re-ran `python3 -m pytest backend/tests`, re-ran `npm run build` in `frontend/`, and executed a Flask test-client script that logged in as admin and requested `/api/v1/reports/export?format=csv` plus `format=xlsx`.
- Result: Backend tests pass with `15 passed`, the frontend production build passes, and the export endpoint now returns valid CSV and XLSX attachments for an admin user.

## 2026-03-09 Docker Packaging & Static Serving
- Why: The project needed a production-ready container path that builds Vue separately, runs Flask under Gunicorn, and serves the compiled H5/Web frontend from the same process.
- How: Added a root `Dockerfile` with frontend build, backend dependency install, and runtime stages; added `.dockerignore`; updated `backend/app.py` to serve `frontend/dist` with SPA history fallback while preserving JSON 404s for unknown `/api/...` requests; and added backend tests that exercise index serving, asset serving, and missing-route behavior.
- Result: The repository now contains a container build path that packages both apps together and a backend path capable of serving the built frontend bundle directly. Verification passed with `python3 -m pytest backend/tests` (`17 passed`) and `npm run build`; an actual `docker build` could not be executed here because the local environment does not have the `docker` CLI installed.

## 2026-03-09 Fly.io Deployment Config
- Why: Fly.io deployment needs an explicit app definition, persistent SQLite mount, and a runtime port that matches the container listener; otherwise deployment would come up unhealthy.
- How: Added `fly.toml` with app name `roseate-wms`, `roseate_storage` mounted at `/app/instance`, and `DATABASE_URL=sqlite:////app/instance/wms.db`. Updated `Dockerfile` so Gunicorn binds to `0.0.0.0:8000` and exposed port `8000`, then documented the Fly workflow in `README.md`.
- Result: The repo now contains a coherent Fly.io deployment config where the declared internal service port matches the Gunicorn listener and SQLite points at the mounted persistent volume.

## 2026-03-10 Fly.io Deploy Script
- Why: Repeating the Fly volume bootstrap and deploy commands manually is error-prone, and JWT secret setup needs to be called out explicitly so deployment is not left with a weak default.
- How: Added a root `deploy.sh` that checks for `flyctl`, ensures the `roseate_storage` volume exists for `roseate-wms`, and then runs `flyctl deploy`. Updated the script to pass `--yes` so non-interactive deployments can proceed. Updated `README.md` with script usage and the required `flyctl secrets set JWT_SECRET_KEY=...` command. Aligned `fly.toml` to use the `sin` region (closest available to Hong Kong) with `shared-cpu-1x` / `256MB` for a low-cost footprint.
- Result: The repository now includes a minimal deployment helper for Fly.io plus explicit operator guidance for configuring the JWT secret outside the repo, and the default Fly config targets Singapore with a small VM size.

## 2026-03-10 Fly.io Deployment Execution
- Why: The application needed to be deployed to the `roseate` org with a low-cost VM in the closest available region to Hong Kong.
- How: Verified Fly org access, staged a JWT secret, created the `roseate_storage` volume in `sin`, and deployed the app with `flyctl deploy`. Confirmed the running machine via `flyctl status`.
- Result: `roseate-wms` is running in `sin` with a single shared-cpu-1x machine, and is reachable at `https://roseate-wms.fly.dev/`.

## 2026-03-12 Inbound Receipts & Ledger Export
- Why: The ledger-style table header requires a document-numbered IN/OUT trace and a deterministic running-balance calculation; without inbound receipts and IN transactions, export would be incomplete.
- How: Added `InboundReceipt` and `InboundLine` models in `backend/models.py`, updated `/api/v1/inventory/inbound` to create receipt/line records and write `InventoryTransaction(transaction_type=\"IN\")`, enriched OUT transactions with `doc_no` metadata, and implemented `/api/v1/reports/ledger-export` supporting `balance_scope=product|batch` (plus optional batch columns). Added pytest coverage for receipt creation and running balances.
- Result: Backend tests pass with 20 tests and the new ledger export endpoint can generate CSV/XLSX matching the reference header while computing on-the-fly balances.

## 2026-03-12 Frontend Navigation Refresh + Changelog
- Why: The sidebar needed to reflect the operator mental model (dashboard -> products -> orders -> inventory) and consolidate non-core features under a single entry. The website also needed a simple changelog page.
- How: Added `OtherView.vue` to host non-core navigation links, added `ChangelogView.vue`, and updated `frontend/src/router/index.js` route `meta.title` plus `frontend/src/layouts/MainLayout.vue` to enforce the new sidebar order: 首页、商品、订单、库存、其他、设置.
- Result: `npm run build` passes and the UI now includes a consolidated "其他" hub and a changelog page.

## 2026-03-12 Product Archive Import + Units/extra_data UX
- Why: 商品建档在真实业务里通常来自表格初始化；同时需要把单位换算表达统一成一个口径，并让扩展字段可被运营查看（但默认不占空间）。
- How: Added `backend/services/product_import_service.py` to parse CSV/XLSX via pandas, validate required columns (`hb_code`, `name`, `spec`), and tolerate `extra_data` JSON escaping. Implemented admin-only endpoints `POST /api/v1/products/import/preview` and `POST /api/v1/products/import` in `backend/app.py`, with pytest coverage in `backend/tests/test_inventory.py`. Updated `frontend/src/views/ProductsView.vue` to add an admin import panel (upload -> preview -> commit), renamed the product create form label to “计量单位”, added a computed conversion hint, and rendered `extra_data` as a collapsed JSON block with expand/collapse on both desktop and mobile layouts.
- Result: `python3 -m pytest backend/tests` passes (21 tests). `npm run build` passes.
