# Stage 2 Todo

## Scope
- [x] Extend backend models with `Product` and `Batch`, both preserving `extra_data`
- [x] Add model helpers for JSON payloads, stock aggregation, and date serialization
- [x] Write pytest coverage for product creation, inbound batch creation, and same-expiry merge behavior
- [x] Implement `GET /api/v1/products` with fuzzy search and total stock aggregation
- [x] Implement `POST /api/v1/products` for product archive creation
- [x] Implement `POST /api/v1/inventory/inbound` for inbound stock merge/create behavior
- [x] Build a product center page showing product info and computed total stock
- [x] Build an H5-first inbound flow: scan/input barcode, resolve product, then submit batch data
- [x] Update routing and navigation to expose the product center cleanly
- [x] Synchronize `README.md`, `tasks/devlog.md`, and this file with verification evidence

## Implementation Notes
- Product stock must always be derived from batches where `current_quantity > 0`; do not persist a product-level stock field.
- `Batch` merge behavior for inbound follows `hb_code + expiry_date` as the inventory consolidation key.
- All tables keep `extra_data` as a JSON-compatible `Text` field to satisfy the “only add fields” rule.
- APIs continue using the unified response format `{ "code": ..., "data": ..., "msg": ... }`.
- Prefer secure default behavior: product and inventory APIs should require JWT authentication.

## Review / Summary
- [x] Model and API behavior verified with pytest
- [x] Frontend route changes and responsive UI verified with Vite build
- [x] README and task logs updated for Stage 2 handoff

### Delivery Notes
- Backend now includes `Product` and `Batch` entities with JSON-compatible `extra_data`, relationship-based stock aggregation, and inbound merge logic keyed by `hb_code + expiry_date`.
- Product APIs support archive creation and fuzzy retrieval; inbound API resolves products by `hb_code` or `barcode` and either merges or creates a batch.
- Frontend now exposes a product center and an H5-first inbound workflow, both wired to the Stage 2 backend APIs.
