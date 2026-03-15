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
| BUG-04 | High | Open | fixed | API-level barcode uniqueness + inbound rejects ambiguous barcode. Also product import rejects barcode collisions. Commit `4dfb0ad`. |
| BUG-05 | Medium | Open | fixed | `POST /api/v1/products` is now admin-only (`@admin_required`). Commit `4dfb0ad`. |
| OBS-01 | Medium | Open | fixed | `/api/v1/inventory/test` is now debug-only and no longer returns username/role. Commit `4dfb0ad`. |
| OBS-02 | Medium | Open | fixed | `POST /api/v1/orders/fulfill` is now admin-only (`@admin_required`). Commit `8a3f36a`. |
| BUG-06 | High | Open | fixed | FIFO reservation skips expired batches; `sellable_stock` excludes expired. Commit `a86db35`. |
| BUG-07 | High | Open | fixed | `/inventory/reserve` now creates `manual` order + allocations; releasable via `/orders/cancel`. Commit `a86db35`. |
| BUG-08 | Medium | Open | fixed | `find_product()` returns 404 if hb_code not found; no barcode fallthrough. Commit `a86db35`. |
| OBS-03 | Medium | Open | fixed | Added `POST /api/v1/orders/cancel` to release reserved allocations. Commit `a86db35`. |

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
Fix commit: `8a3f36a`
Verification: pytest regression `test_order_sync_idempotency_with_external_order_no`; deployed to Fly after merge.

### BUG-04 Barcode Uniqueness (Fixed)
Risk:
- Duplicate barcodes make `find_product()` ambiguous and inbound matching non-deterministic.

Fix (safe without DB migrations):
- Enforce uniqueness at API level:
  - `POST /api/v1/products`: reject if `barcode` already exists (`409`)
  - product import overwrite: reject/skip rows that would collide barcodes across hb_code
- Enforce deterministic lookup:
  - If multiple products share a barcode, return an error instead of picking first.

Note:
- DB-level `unique=True` on the model won’t retroactively apply to existing SQLite without migrations.
Fix commit: `4dfb0ad`
Verification: added pytest regression for duplicate barcode create and ambiguous inbound barcode; deployed to Fly after merge.

### BUG-05 RBAC Consistency (Fixed)
Observation:
- `POST /api/v1/products` currently allows `staff`, while import/mapping writes are admin-only.

Fix:
- Change `POST /api/v1/products` decorator to `@admin_required`.
Fix commit: `4dfb0ad`
Verification: pytest `test_staff_cannot_create_product`; deployed to Fly after merge.

### OBS-01 Debug Endpoint Leakage (Fixed)
Current:
- `/api/v1/inventory/test` returns `username/role` for any valid JWT.

Fix:
- Make it DEBUG-only (register route only when `app.debug` or an explicit `ENABLE_DEBUG_ENDPOINTS=1`), or sanitize response.
Fix commit: `4dfb0ad`
Verification: auth tests no longer depend on this endpoint; deployed to Fly after merge.

### OBS-02 Staff Fulfill Permission (Fixed)
Observation:
- `orders/fulfill` permanently deducts `current_quantity`, which is irreversible.

Decision:
- We require admin for fulfill (`@admin_required`) to avoid irreversible stock deductions by staff.
Fix commit: `8a3f36a`
Verification: pytest `test_staff_cannot_fulfill_order`; deployed to Fly after merge.

### BUG-06 FIFO Should Skip Expired Batches (Triaged)
Problem:
- FIFO reservation currently considers expired batches first, which can allocate expired stock to customer orders.

Fix:
- Update reservation query to filter `Batch.expiry_date > today`.
- Update `Product.sellable_stock` to also exclude expired batches, so "可售库存" and reservation logic are consistent.
Fix commit: `a86db35`
Verification: pytest `test_order_reserve_skips_expired_batches`.

### BUG-07 Manual Reserve Creates Orphan Holds (Fixed)
Problem:
- `/api/v1/inventory/reserve` modifies `Batch.reserved_quantity` but creates no order/allocation record, so the hold cannot be released.

Fix:
- Persist manual reserves as a `SalesOrder(channel_name='manual')` with `OrderAllocation` rows.
- Add `/api/v1/orders/cancel` to release allocations and change status to `cancelled`.
Fix commit: `a86db35`
Verification: pytest `test_cancel_manual_reservation_releases_stock`.

### BUG-08 `find_product()` Fallthrough (Fixed)
Problem:
- If the caller provides an invalid `hb_code` plus a valid `barcode`, inbound silently matches by barcode and may stock the wrong product.

Fix:
- If `hb_code` is provided and not found, return `404` immediately and do not fall through to barcode matching.
Fix commit: `a86db35`
Verification: pytest `test_inbound_product_lookup_does_not_fall_through_to_barcode`.

### OBS-03 Missing Order Cancel API (Fixed)
Problem:
- There is no supported API to release a reserved order.

Fix:
- Add `POST /api/v1/orders/cancel` and release `reserved_quantity` for all allocations.
Fix commit: `a86db35`
Verification: pytest `test_cancel_manual_reservation_releases_stock`.
