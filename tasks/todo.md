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
