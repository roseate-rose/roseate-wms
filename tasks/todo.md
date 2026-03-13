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
- [ ] Backend: add inbound bulk import endpoints (upload -> preview -> commit) that generate `InboundReceipt/InboundLine/InventoryTransaction(IN)` like single inbound
- [ ] Backend: add orders bulk import endpoints (upload -> preview -> commit) that resolve `ChannelMapping` and reserve FIFO stock like `/orders/sync`
- [ ] Backend: support column mapping (user can choose which columns map to required fields) and preserve unmapped columns into `extra_data` for future logistics API integration
- [ ] Backend tests: cover unit conversion, batch merge in bulk inbound, and channel mapping lookup + reservation in bulk orders import
- [ ] Frontend: add “批量入库导入” 页面（/inbound-import），支持映射调整与预览
- [ ] Frontend: add “批量订单导入” 页面（/orders-import），支持菜鸟/顺丰模板通过映射适配（后续可加 preset）
- [ ] Docs: update README with new endpoints + expected template columns; update devlog
- [ ] Verify: backend pytest + frontend build; then commit in two batches (backend then frontend) and deploy to Fly
