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
| BUG-03 | High | Open | fixed | Idempotency via `external_order_no` using `external_order_refs` table. If caller omits `external_order_no`, behavior remains non-idempotent. Commit `8a3f36a`. |
| BUG-04 | High | Open | fixed | API-level barcode uniqueness + inbound rejects ambiguous barcode. Also product import rejects barcode collisions. Commit TBD. |
| BUG-05 | Medium | Open | fixed | `POST /api/v1/products` is now admin-only (`@admin_required`). Commit TBD. |
| OBS-01 | Medium | Open | fixed | `/api/v1/inventory/test` is now debug-only and no longer returns username/role. Commit TBD. |
| OBS-02 | Medium | Open | fixed | `POST /api/v1/orders/fulfill` is now admin-only (`@admin_required`). Commit `8a3f36a`. |

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

Implemented approach:
- We treat `(channel_name, external_order_no)` as the idempotency key.
- Storage uses `external_order_refs` table with a uniqueness constraint (no migrations required for `sales_orders`).
- `/api/v1/orders/sync` accepts optional `external_order_no`. When provided:
  - First call creates order and reserves FIFO stock.
  - Subsequent calls return the existing order and do not reserve again.
- If `external_order_no` is omitted, the system cannot reliably dedupe repeated purchases of the same SKU, so it preserves existing non-idempotent behavior.

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

Decision:
- We require admin for fulfill (`@admin_required`) to avoid irreversible stock deductions by staff.
