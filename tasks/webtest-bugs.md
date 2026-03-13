# WebTest Bug Feedback Tracker (Read-Only Source)

This file tracks bug feedback coming from `roseate-wms-webtest` and the corresponding fix progress in **this** repository (`roseate-wms`).

Rules:
- We only **read** feedback from the webtest repo; we do **not** modify webtest code or its bug file.
- All fixes, progress notes, and verification are recorded here (and in `tasks/devlog.md` for implementation details).

Legend:
- `webtest_status`: status as written in webtest bug list.
- `wms_status`: status in this repo.
  - `triaged`: confirmed and scoped, pending fix
  - `needs-confirmation`: blocked by business decision / API contract decision
  - `fixed`: merged to `main`, tests passing, deployed to Fly

## Summary Table

| ID | Severity | webtest_status | wms_status | Notes / Linkage |
|---|---|---|---|---|
| BUG-01 | High | Open | fixed | Weighted average cost on batch merge. Commit `28e49eb`. |
| BUG-02 | Medium | Open | fixed | `expiry_date == today` treated as `expired`. Commit `28e49eb`. |
| BUG-03 | High | Open | needs-confirmation | Order idempotency key: webtest suggests `channel+sku`, but real orders need `external_order_no` (order id) to avoid blocking legit repeated purchases of same SKU. |
| BUG-04 | High | Open | triaged | Barcode uniqueness enforcement: at minimum API-level guard (`409` on duplicate) and disallow ambiguous barcode lookup. DB unique constraint needs migration strategy. |
| BUG-05 | Medium | Open | triaged | RBAC consistency: align `POST /products` with other admin-only write ops. |
| OBS-01 | Medium | Open | triaged | `/inventory/test` leaks `username/role`; likely make it DEBUG-only or sanitize response. |
| OBS-02 | Medium | Open | needs-confirmation | Whether `staff` should be allowed to `orders/fulfill` (irreversible stock deduction). |

## Details

### BUG-01 (Fixed) Weighted Average Cost on Batch Merge
- Fix scope:
  - `POST /api/v1/inventory/inbound` merge path
  - `POST /api/v1/inventory/import` with `merge_mode=accumulate`
- Fix commit: `28e49eb`
- Verification: `python3 -m pytest backend/tests` (25 passed); deployed to Fly after merge.

### BUG-02 (Fixed) Expiry Boundary: Today Is Expired
- Behavior:
  - `expiry_date < today` => `expired`
  - `expiry_date == today` => `expired`
  - `today < expiry_date <= today+30` => `warning`
- Fix commit: `28e49eb`
- Verification: added pytest regression `test_expiry_today_is_expired`.

### BUG-03 Order Sync Idempotency (Pending Confirmation)
Problem:
- Repeated webhook retries may create duplicated orders and over-reserve inventory.

Open decision:
- Idempotency key:
  - Webtest suggestion: `channel_name + external_sku_id` (simple, but may block a legit second order of the same SKU)
  - Recommended for real-world: `channel_name + external_order_no (+ external_sku_id)` (requires API payload support)

Next step:
- Confirm desired idempotency behavior and whether `external_order_no` should be added/required for `/orders/sync` and `/orders/import`.

### BUG-04 Barcode Uniqueness (Triaged)
Risk:
- Duplicate barcodes make `find_product()` ambiguous and inbound matching non-deterministic.

Proposed fix (safe without DB migrations):
- Enforce uniqueness at API level:
  - `POST /api/v1/products`: reject if `barcode` already exists (`409`)
  - product import overwrite: reject/skip rows that would collide barcodes across hb_code
- Enforce deterministic lookup:
  - If multiple products share a barcode, return an error instead of picking first.

Note:
- DB-level `unique=True` on the model won’t retroactively apply to existing SQLite without migrations.

### BUG-05 RBAC Consistency (Triaged)
Observation:
- `POST /api/v1/products` currently allows `staff`, while import/mapping writes are admin-only.

Proposed fix:
- Change `POST /api/v1/products` decorator to `@admin_required`.

### OBS-01 Debug Endpoint Leakage (Triaged)
Current:
- `/api/v1/inventory/test` returns `username/role` for any valid JWT.

Proposed fix:
- Make it DEBUG-only (register route only when `app.debug` or an explicit `ENABLE_DEBUG_ENDPOINTS=1`), or sanitize response.

### OBS-02 Staff Fulfill Permission (Pending Confirmation)
Observation:
- `orders/fulfill` permanently deducts `current_quantity`, which is irreversible.

Open decision:
- If warehouse staff must fulfill, keep as-is.
- If only admin can fulfill, switch to `@admin_required`.

