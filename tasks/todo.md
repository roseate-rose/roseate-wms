# Import Alignment + Item Master + Decimal Inventory Todo

## Scope
- [x] Fix product CSV/Excel parsing so imported columns remain strictly aligned with the product schema, especially `unit` and trailing fields
- [x] Add admin-facing item master CRUD so product records can be corrected in the UI without re-importing
- [x] Implement WeChat shop order import support from the provided standard-export CSV headers and preserve all unmapped fields losslessly
- [x] Support decimal inventory quantities and show unit suffixes across stock, inbound, and outbound-adjacent views
- [x] Make product/order import templates visually explicit so operators can see required headers and recognition results before importing
- [x] Verify backend/frontend changes and sync README/devlog/tracking notes

## Implementation Notes
- Keep unit modeling as a single source of truth: `base_unit`, `purchase_unit`, `conversion_rate`.
- Do not touch `roseate-wms-webtest`; publish verification needs through main-repo records only.
- The provided WeChat CSV header sample is now the source of truth for `template=wechat_shop`; unmatched columns are preserved in `extra_data.row_extra` instead of being dropped.

## Review / Summary
- [x] Product import no longer shifts `unit`/trailing columns under malformed CSV/Excel input
- [x] Admin can create, edit, and delete item-master records from the UI
- [x] WeChat shop order imports recognize the provided 50+ field export and preserve row-level extra data
- [x] Decimal inventory flows and unit-suffixed displays behave consistently
- [x] Import pages now show explicit template headers, mapping status, and preview recognition results
- [x] Verification results documented

### Outcome
- Product import now uses sanitized tabular reads plus explicit field alias mapping, so common Chinese headers and empty `Unnamed:*` trailing columns no longer push `unit` / `base_unit` / `purchase_unit` / `conversion_rate` out of alignment.
- Added admin-only product update/delete APIs and extended the Products UI so operators can directly edit master data instead of re-importing.
- Added a dedicated WeChat shop order-template matcher keyed to the provided export headers. Core fields such as `订单号` / `SKU编码(自定义)` / `商品编码(自定义)` / `商品数量` are mapped directly, while the remaining 50+ fields are preserved in `extra_data.row_extra`.
- Inventory-related displays now render quantity with unit suffixes and derived decimal purchase-unit views (for example, base stock can render as `1 支 (0.2 盒)` when `conversion_rate=5`).
- Product and order import pages now expose visible header chips, template descriptions, required/optional mapping cards, and preview recognition badges so operators can confirm the schema before committing.
- Added README/docs coverage and regression tests for the import-alignment, item-master CRUD, and WeChat-template work.

### Remaining Gap
- Quantity presentation already supports decimal-style business display with unit binding, but database inventory quantities are still stored as integer base units. A true decimal stock-storage migration would be a larger schema/business change and is intentionally not included in this fix set.

### Verification
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest backend/tests`
- `npm --prefix frontend run build`

# Orders Import Selector + Sample Todo

## Scope
- [x] Change the order-import default channel from free-text input to guided selection
- [x] Put `微信小店` first in the channel list and keep template matching operator-friendly
- [x] Provide downloadable CSV sample files directly from the order-import UI
- [x] Verify the frontend build and sync operator-facing docs

## Review / Summary
- [x] Channel selection is now explicit and WeChat-first
- [x] Custom-channel fallback is still available when presets do not fit
- [x] Generic and WeChat Shop CSV samples are available from the page

### Outcome
- The order-import entry now starts from a channel selector rather than a free-text field, which reduces operator input errors and makes the default path more obvious.
- `微信小店` is the first and default option, and selecting a preset channel automatically recommends the closest template.
- Operators can download a ready-to-fill CSV sample directly from the import page before uploading.

### Verification
- `npm --prefix frontend run build`

# WebTest Handoff Protocol Todo

## Scope
- [x] Define a machine-readable handoff file for the separate webtest agent to poll
- [x] Seed the file with the current BUG-09 verification request
- [x] Document the producer/consumer contract in main-repo task records

## Implementation Notes
- The handoff lives in `tasks/webtest-handoff.json` so the main repo can publish verification requests without touching the webtest repo.
- The webtest agent should treat this file as read-only input and only consume requests whose status is `ready_for_webtest`.

## Review / Summary
- [x] JSON handoff contract created
- [x] BUG-09 is published as the first `ready_for_webtest` request
- [x] Main-repo records explain how downstream polling should work

# BUG-09 Settings RBAC Fix Todo

## Scope
- [x] Mark frontend `/settings` as admin-only in the router guard flow
- [x] Hide the sidebar "设置" entry for non-admin users
- [x] Verify the frontend still builds and document the fix in tracker/devlog

## Implementation Notes
- Keep the fix frontend-only; backend `/users` is already admin-only and does not need behavior changes.
- Prefer reusing the existing `meta.adminOnly` guard pattern instead of adding a second RBAC mechanism.

## Review / Summary
- [x] `staff` can no longer navigate to `/settings`
- [x] Non-admin users no longer see the "设置" sidebar entry
- [x] Verification recorded

### Outcome
- `/settings` now reuses the existing frontend `meta.adminOnly` guard, matching `/finance`.
- The sidebar now treats "设置" as an admin-only nav item and filters it out for non-admin users before rendering.
- Verified with `npm --prefix frontend run build`.

### Remaining Verification Gap
- Browser-level RBAC confirmation is intentionally deferred to the dedicated webtest project, per user instruction not to run commands in that repo.

# WebTest Unresolved Bug Review Todo

## Scope
- [x] Review current webtest tracking notes in `roseate-wms`
- [x] Inspect the dedicated `roseate-wms-webtest` project for bug lists, test cases, and recent results
- [x] Cross-check unresolved items against the current local app behavior and identify gaps
- [x] Add a Review / Summary section with the remaining bug list and supporting evidence

## Implementation Notes
- Treat `roseate-wms-webtest` as the source of truth for outstanding browser-test feedback; this repo's tracker may be stale.
- Focus on unresolved bugs, regressions, and verification gaps rather than repeating already-fixed items.
- Per user correction, follow-up work for these findings must happen only in `roseate-wms`; do not run or modify anything inside `roseate-wms-webtest` unless explicitly re-authorized.

## Review / Summary
- [x] Outstanding webtest bugs enumerated with evidence
- [x] Any mismatches between tracker state and actual test project state documented
- [x] Main-repo tracker updated again after the local RBAC fix landed

### Outcome
- Synced the main repo tracker with the currently outstanding browser-test finding: `BUG-09`.
- The previous main-repo tracker was stale: it claimed all webtest bugs were fixed, but the dedicated webtest project had already added a new open item for frontend RBAC on `/settings`.
- After the frontend RBAC patch landed in the main repo, the tracker and handoff contract were updated again so `BUG-09` now sits at `implemented` / `ready_for_webtest`, waiting only for downstream browser confirmation.

### Remaining Verification Gap
- `BUG-09` is fixed locally in the main repo, but still needs the separate `roseate-wms-webtest` runner to confirm the browser behavior and mark the handoff request as passed or failed.

# Local Environment Startup Todo

## Scope
- [x] Review the current local run workflow, ports, and helper scripts for backend/frontend
- [x] Check whether Python and frontend dependencies are already present and note any missing prerequisites
- [x] Start the local backend/frontend with the repo-supported script path
- [x] Verify the local environment is reachable on the documented URLs and inspect runtime logs/status
- [x] Add a Review / Summary section with exact startup commands, observed ports, and any blockers/workarounds

## Implementation Notes
- Prefer the repository's local helper scripts over ad-hoc commands so port management and logs stay consistent.
- Keep backend/frontend ports fixed unless the documented workflow requires an explicit override.
- The plain `local_test_up.sh` flow did not stay alive when launched from the sandboxed tool shell; `local_test_screen_up.sh` was the stable path for a persistent local environment in this session.
- Python deps required for runtime are present; `gunicorn` is not installed in the current Python 3.9 environment, but the project scripts can fall back to `python3 backend/app.py`.

## Review / Summary
- [x] Local startup workflow validated or blockers documented
- [x] Exact commands, URLs, and verification results recorded

### Outcome
- Cleared stale listeners on fixed ports `5001` / `5174`, stopped the old `screen` session, then started a fresh detached session with `./scripts/local_test_screen_up.sh`.
- Verified detached `screen` session exists as `roseate-wms`, backend listens on `127.0.0.1:5001`, and frontend listens on `127.0.0.1:5174`.
- Verified frontend responds with `HTTP/1.1 200 OK` on `http://127.0.0.1:5174/`.
- Verified backend login responds with `HTTP/1.1 200 OK` on `POST http://127.0.0.1:5001/api/v1/auth/login` using `admin / Admin@123456`.

### Exact Commands
- Clear fixed-port conflicts if needed: `CONFIRM=1 ./scripts/local_test_kill_conflicts.sh`
- Start persistent local services: `./scripts/local_test_screen_up.sh`
- Attach to the running session: `screen -r roseate-wms`
- Stop the running session: `./scripts/local_test_screen_down.sh`
- Check PID-based service status (for `local_test_up.sh` mode only): `./scripts/local_test_status.sh`
- Tail logs: `tail -f instance/run/backend.log` and `tail -f instance/run/frontend.log`

# Auth Session Policy Todo

## Scope
- [x] Review current auth/user/session changes and fix any blocking regression before verification
- [x] Change JWT access token validity to 7 days and verify via backend tests
- [x] Seed several non-admin default users and expose them to admins in settings
- [x] Make user settings support explicit logout for all logged-in users
- [x] Update README, devlog, lessons, and review notes to match actual behavior
- [x] Commit, push, and deploy the auth/session updates to Fly

## Review / Summary
- [x] Backend tests pass after auth/session changes
- [x] Frontend build passes with settings/logout updates
- [x] Fly deployment completed with the new auth/session behavior

# Fly Deploy Script Todo

## Scope
- [x] Inspect repository deployment conventions before adding a Fly helper script
- [x] Add `deploy.sh` to create the Fly volume when missing and run `flyctl deploy`
- [x] Document `flyctl secrets set JWT_SECRET_KEY=...` in the README
- [x] Verify the script content and deployment docs are internally consistent
- [x] Align Fly region and VM sizing with a small Hong Kong footprint

## Implementation Notes
- The helper should be safe to re-run by checking for an existing volume first.
- The script should target the existing `fly.toml` app name and mount name by default.
- JWT secrets must stay out of git and be configured with `flyctl secrets set`.

## Review / Summary
- [x] `deploy.sh` covers volume creation and deployment
- [x] README and dev log updated with secrets guidance
- [x] Script syntax verified with `bash -n deploy.sh`
- [x] `fly.toml` now targets `sin` with `shared-cpu-1x` / `256MB`
- [x] Fly deployment executed; app is running in `sin`

---

# Ledger & Receipt Todo

## Scope
- [x] Add `InboundReceipt` / `InboundLine` models
- [x] Update inbound API to create receipt + line and record `IN` inventory transactions
- [x] Update fulfill path to attach `doc_no` metadata to `OUT` transactions
- [x] Add `/api/v1/reports/ledger-export` with product/batch running balance support
- [x] Add pytest coverage for receipts and ledger running balance

## Review / Summary
- [x] `python3 -m pytest backend/tests` passes (20 tests)
- [x] `npm run build` passes

---

# Product Import + Units UI Todo

## Scope
- [x] Add admin-only product import preview/commit endpoints
- [x] Implement CSV/XLSX parsing with tolerant `extra_data` JSON parsing
- [x] Add pytest coverage for RBAC + preview/commit behavior
- [x] Add Products page import panel (upload -> preview -> commit)
- [x] Keep unit conversion as a single expression: `base_unit + purchase_unit + conversion_rate`
- [x] Update product create form label to “计量单位” and show a computed conversion hint
- [x] Show `extra_data` to users but collapsed by default (desktop table + mobile cards)
- [x] Verify: `python3 -m pytest backend/tests` and `npm run build`

## Review / Summary
- [x] `python3 -m pytest backend/tests` passes (21 tests)
- [x] `npm run build` passes

---

# Bulk Inbound + Bulk Orders Import Todo

## Scope
- [x] Backend: add inbound bulk import endpoints (upload -> preview -> commit) that generate `InboundReceipt/InboundLine/InventoryTransaction(IN)` like single inbound
- [x] Backend: add orders bulk import endpoints (upload -> preview -> commit) that resolve `ChannelMapping` and reserve FIFO stock like `/orders/sync`
- [x] Backend: support column mapping (user can choose which columns map to required fields) and preserve unmapped columns into `extra_data` for future logistics API integration
- [x] Backend tests: cover unit conversion, batch merge in bulk inbound, and channel mapping lookup + reservation in bulk orders import
- [x] Frontend: add “批量入库导入” 页面（/inbound-import），支持映射调整与预览
- [x] Frontend: add “批量订单导入” 页面（/orders-import），支持菜鸟/顺丰模板通过映射适配（后续可加 preset）
- [x] Docs: update README with new endpoints + expected template columns; update devlog
- [x] Verify: backend pytest + frontend build; then commit in two batches (backend then frontend) and deploy to Fly

---

# WebTest Bug Tracking Todo

## Scope
- [x] Add `tasks/webtest-bugs.md` as the single source of truth for webtest bug progress in this repo
- [x] Re-scan webtest bug list and sync remaining open items into tracker
- [x] Implement BUG-01..BUG-05 + OBS-01..OBS-02 fixes in roseate-wms (see `tasks/webtest-bugs.md`)

## Review / Summary
- [x] Bulk inbound/orders import exists end-to-end (preview -> mapping -> commit), preserves unmapped columns to `extra_data`, and has pytest coverage
- [x] Webtest bug list is fully implemented in this repo; remaining work is to re-run playwright E2E and triage any new findings

---

# Expired Token UX Todo

## Scope
- [x] Review current JWT expiry behavior and frontend auth/session handling
- [x] Add centralized frontend handling for expired/invalid token responses
- [x] Clear local auth state and redirect to `/login` instead of leaving the UI stuck on repeated `token has expired`
- [x] Verify with backend pytest + frontend build
- [x] Deploy updated frontend to Fly

## Review / Summary
- [x] Backend JWT expiry remains 8 hours; no server-side expiry change was made
- [x] Frontend now clears stale auth state and redirects to `/login` on non-login 401 token failures
- [x] Verified with `python3 -m pytest backend/tests` and `npm --prefix frontend run build`
