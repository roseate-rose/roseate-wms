# Stage 5 Todo

## Scope
- [x] Add persistent order, order allocation, and inventory transaction models for the order lifecycle
- [x] Add pytest coverage for external order sync, admin-only export access, and fulfill stock deduction
- [x] Implement reusable role decorators including `admin_required`
- [x] Implement `POST /api/v1/orders/sync` using `channel_name + external_sku_id -> hb_code -> FIFO reserve`
- [x] Implement `POST /api/v1/orders/fulfill` to convert reserved stock into OUT transactions and deduct on-hand stock
- [x] Implement `GET /api/v1/orders` for frontend order status display
- [x] Implement `GET /api/v1/reports/export` with CSV/XLSX export support
- [x] Restrict import/export and other admin-only write actions via RBAC
- [x] Persist user role in frontend auth state and use it for UI gating
- [x] Add orders page with sync/fulfill visibility and status display
- [x] Add report download UI and admin-only quick mapping flow from unknown scan result
- [x] Add hidden-by-role sidebar items for `财务统计` and `用户设置`
- [x] Synchronize `README.md`, `tasks/devlog.md`, and this file with verification evidence

## Implementation Notes
- Orders must carry a real persisted status, at minimum `reserved` and `fulfilled`.
- Fulfillment must reduce both `current_quantity` and `reserved_quantity` by the same allocated amount.
- Export endpoint should support `format=csv|xlsx`; non-admin users must be rejected before performing heavy export work.
- UI role checks are only presentation controls; server-side RBAC remains authoritative.
- Unknown barcode mapping in H5 flow should only be exposed to admin users.

## Review / Summary
- [x] Order lifecycle and RBAC verified with `python3 -m pytest backend/tests` (`15 passed`)
- [x] Frontend role-aware navigation and order/export views verified with `npm run build`
- [x] Admin export path verified with Flask test client for both `format=csv` and `format=xlsx`
- [x] README and task logs updated for Stage 5 handoff
