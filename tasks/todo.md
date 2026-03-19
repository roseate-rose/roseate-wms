# Auth Session Policy Todo

## Scope
- [x] Review current auth/user/session changes and fix any blocking regression before verification
- [x] Change JWT access token validity to 7 days and verify via backend tests
- [x] Seed several non-admin default users and expose them to admins in settings
- [x] Make user settings support explicit logout for all logged-in users
- [x] Update README, devlog, lessons, and review notes to match actual behavior
- [ ] Commit, push, and deploy the auth/session updates to Fly

## Review / Summary
- [x] Backend tests pass after auth/session changes
- [x] Frontend build passes with settings/logout updates
- [ ] Fly deployment completed with the new auth/session behavior

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
