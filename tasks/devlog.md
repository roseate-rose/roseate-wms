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

## 2026-03-12 Bulk Inbound + Bulk Orders Import (Column Mapping)
- Why: 运营需要用表格批量入库与批量处理订单，并兼容菜鸟/顺丰等多种模板头；同时要保留未用字段，方便未来对接物流商 API 而不改表结构。
- How: Added `backend/services/tabular_service.py` to read CSV/XLSX and support column guessing and extra-field preservation. Implemented inbound bulk import endpoints `POST /api/v1/inventory/inbound-import/preview` and `POST /api/v1/inventory/inbound-import` that reuse the single-inbound logic to generate `InboundReceipt/InboundLine/InventoryTransaction(IN)` and support per-row or shared receipt numbers. Implemented orders bulk import endpoints `POST /api/v1/orders/import/preview` and `POST /api/v1/orders/import` that resolve `ChannelMapping`, reserve FIFO stock, and store unmapped columns in `extra_data.row_extra` for future logistics integration. Added frontend pages `InboundImportView.vue` and `OrdersImportView.vue`, wired routes and links under “其他”, and updated README. Added pytest coverage for inbound conversion+merge and orders import reservation+extra_data.
- Result: `python3 -m pytest backend/tests` passes (23 tests). `npm run build` passes.

## 2026-03-13 Local Dev Port Overrides
- Why: 本机常见会有其他项目占用 `5000`（后端）或需要并行跑 WebTest；需要能快速切换后端端口并让 Vite 代理跟随。
- How: Updated `backend/app.py` to accept `--host/--port` for local dev server startup, and updated `frontend/vite.config.js` to allow overriding the backend proxy target via `VITE_API_PROXY_TARGET`. Documented the workflow in `README.md`.
- Result: Backend can run on `http://127.0.0.1:5001` and frontend dev server can proxy `/api` to that port; both backend tests and frontend build remain passing.

## 2026-03-13 Regression Fixes: Weighted Cost on Merge + Expiry Boundary
- Why: WebTest discovered two edge regressions: merging the same expiry batch overwrote `cost` instead of computing a weighted average, and batches expiring today were classified as `warning` instead of `expired`.
- How: Updated `apply_inbound_payload()` in `backend/app.py` and the `accumulate` branch in `backend/services/import_service.py` to compute weighted average cost on merges. Updated `classify_expiry_status()` in `backend/services/import_service.py` to treat `expiry_date == today` as `expired`. Added pytest regression coverage in `backend/tests/test_inventory.py`.
- Result: `python3 -m pytest backend/tests` passes (25 tests). `npm run build` passes.

## 2026-03-13 WebTest Feedback Tracker
- Why: We need a single place in this repo to track bugfix progress driven by `roseate-wms-webtest`, while keeping the webtest repo read-only.
- How: Added `tasks/webtest-bugs.md` to record bug IDs, severity, status, fix commit hashes, and pending confirmation items (idempotency/RBAC decisions).
- Result: Tracker is in place; future webtest findings can be triaged and progressed without editing the webtest repo.

## 2026-03-13 Order Idempotency + Fulfill RBAC
- Why: WebTest flagged duplicate order reservations under webhook retries and noted that `staff` could fulfill orders (irreversible stock deduction).
- How: Added `ExternalOrderRef` table to implement idempotency via `(channel_name, external_order_no)` without requiring a migration on `sales_orders`. Updated `/api/v1/orders/sync` to accept optional `external_order_no` and return `idempotent_replay` when a retry is detected. Restricted `/api/v1/orders/fulfill` to admins via `@admin_required`. Added pytest coverage for idempotent sync and staff fulfill restriction.
- Result: `python3 -m pytest backend/tests` passes (27 tests). Frontend build unaffected.

## 2026-03-13 Barcode Uniqueness + Product RBAC + Debug Endpoint Hardening
- Why: WebTest reported barcode collision risks (ambiguous inbound matching), RBAC inconsistency where staff could create products, and a debug endpoint leaking user identity.
- How: Enforced barcode uniqueness at the API layer (`POST /api/v1/products` rejects duplicates) and made inbound reject ambiguous barcode matches. Updated product import to reject barcode collisions both within the file and against existing data. Switched `POST /api/v1/products` to `@admin_required`. Gated `/api/v1/inventory/test` behind debug/testing and removed username/role from its response. Updated frontend to hide product create UI for non-admin and show a hint on inbound when staff cannot build archives. Added pytest coverage.
- Result: `python3 -m pytest backend/tests` passes (30 tests). `npm run build` passes.

## 2026-03-13 Local Default DB Resolution (WebTest Compatibility)
- Why: `roseate-wms-webtest` seeds into `instance/roseate_wms.db`, but the backend previously defaulted to `sqlite:///roseate_wms.db` when `DATABASE_URL` was unset, causing seed data to be ignored and E2E runs to behave like an empty system.
- How: Added `resolve_database_url()` in `backend/app.py` so that when `DATABASE_URL` is not provided, the backend prefers an existing SQLite file under `instance/` (supporting both `instance/wms.db` and `instance/roseate_wms.db`) and otherwise initializes a new DB at `instance/wms.db`. Updated `README.md` to document the behavior and the cleanup note for both filenames.
- Result: `python3 -m pytest backend/tests` still passes (30 tests). Local dev can run with webtest seed without needing to export `DATABASE_URL` manually.

## 2026-03-13 Local Test Services Keep-Alive Scripts
- Why: 本地需要一个“测试服务常驻运行”的方式，避免关掉终端后 Flask/Vite dev server 退出，影响人工测试与外部 E2E runner 调用。
- How: Fixed the backend dev CLI flag so `--debug` is opt-in (stable default for long-running process). Added `scripts/local_test_up.sh`, `scripts/local_test_down.sh`, and `scripts/local_test_status.sh` which start backend + frontend via `nohup`, record pid files under `instance/run`, and write logs to `instance/run/*.log` (default ports `5001/5174`, `--strictPort` enabled to avoid silent port switching). Added `scripts/local_test_screen_up.sh` / `scripts/local_test_screen_down.sh` as a more robust keep-alive option via `screen`. Backend startup prefers `gunicorn` if installed, falling back to `python3 backend/app.py`.
- Result: Local test services can be started once and left running; logs/pids are isolated under `instance/run`, can be stopped deterministically, and are easier to keep attached via `screen`.

## 2026-03-15 Main Menu: Add Inbound Entry
- Why: 入库是高频操作，需要在主菜单（桌面侧边栏与移动端底部 tab）直接可达，不应该藏在“其他”里。
- How: Updated `frontend/src/layouts/MainLayout.vue` nav ordering to include `/inbound` as a first-class item (Home -> Inbound -> Products -> Orders -> Stock -> Other -> Settings). Mobile tab bar now supports 6 items by switching grid columns to `grid-cols-6` automatically when inbound is present.
- Result: `npm run build` passes; inbound is accessible from main navigation on both desktop and mobile.

## 2026-03-15 Local Test Port Contract (Stable Ports + Kill Conflicts)
- Why: 本地运行涉及 `roseate-wms` 与 `roseate-wms-webtest` 两个项目，端口信息必须稳定且准确；自动换端口会导致 webtest/人工测试连错服务。
- How: Documented the fixed local ports (`backend=5001`, `frontend=5174`) in `README.md`. Updated `scripts/local_test_up.sh` to refuse port switching and instruct users to kill conflicting listeners instead. Added `scripts/local_test_kill_conflicts.sh` which detects current listeners and only kills them when `CONFIRM=1` is set.
- Result: Local test services have a stable port contract; conflicts are handled deterministically without “悄悄换端口”。

## 2026-03-15 WebTest New Bugs: Expired FIFO, Orphan Reserve, Strict Lookup, Cancel API
- Why: `roseate-wms-webtest/tasks/bugs.md` 提出了新的边界问题：FIFO 预占会命中过期批次（BUG-06），`/inventory/reserve` 会创建无法释放的孤儿预占（BUG-07），入库商品查找会在 hb_code 不存在时静默退化为 barcode（BUG-08），以及缺少订单取消 API（OBS-03）。
- How: Filtered reservations to skip expired batches in `reserve_product_inventory()` and excluded expired batches from `Product.sellable_stock`. Changed `find_product()` so that an explicit `hb_code` miss returns `404` and does not fall through to barcode. Reworked `POST /api/v1/inventory/reserve` to persist a `manual` `SalesOrder` + `OrderAllocation` so holds are auditable and releasable, and added `POST /api/v1/orders/cancel` to release reserved allocations (staff can cancel only manual reserves; admin required for external orders).
- Result: Added pytest coverage for all four items; `python3 -m pytest backend/tests` passes (33 tests). README updated with the new cancel endpoint and reserve semantics.

## 2026-03-17 Local Screen Scripts Hardening
- Why: 本地常驻服务使用 `screen`，但 macOS 下 `screen -list` 即使存在 session 也可能返回退出码 1，配合 `set -euo pipefail` 会导致 up/down 脚本异常退出，从而出现重复 session 或 restart 失败，进而引发“5001 跑旧进程”的错觉。
- How: Fixed `scripts/local_test_screen_up.sh` and `scripts/local_test_screen_down.sh` to ignore `screen -list` non-zero exit codes and still parse output. Added a lesson note so后续脚本一律容错该行为。
- Result: Re-running `./scripts/local_test_screen_up.sh` now correctly detects existing `roseate-wms` session and refuses to spawn duplicates; down script reliably stops all matching sessions.

## 2026-03-19 Expired JWT UX Recovery
- Why: 线上 token 过期后，前端没有统一处理 `401 token has expired`，导致商品、入库等所有受保护页面持续报错，但不会清理登录态或跳回登录页，用户只能困在坏状态里。
- How: Kept the backend JWT expiry policy unchanged (`8h`) and fixed the frontend recovery path instead. Added a response interceptor in `frontend/src/api/http.js` that, for non-login `401` token failures, clears the stored token and user state and redirects to `/login` with the current route preserved in `redirect`. Added `clearStoredUser()` in `frontend/src/auth/session.js`.
- Result: `python3 -m pytest backend/tests` passes (33 tests) and `npm --prefix frontend run build` passes. Expired sessions now fail closed and recover by forcing a fresh login instead of spamming API errors.
