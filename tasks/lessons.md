# Lessons

- Keep unit conversion as a single source of truth (`base_unit`, `purchase_unit`, `conversion_rate`); do not introduce a second representation (e.g. fractional “0.2盒” storage or extra factor columns) unless explicitly approved.
- `extra_data` is extensible but should be operator-visible; default UI should render it collapsed/folded with an explicit expand action.
- Irreversible inventory actions (e.g. fulfill that permanently deducts stock) should default to `admin_required` unless the business explicitly wants staff权限.
- In this sandbox, some Python operations may fail when writing `.pyc` into system cache paths; prefer `PYTHONDONTWRITEBYTECODE=1` when running scripts outside the repo or when debugging unexpected PermissionError.
- Cross-repo E2E tooling depends on stable local ports. Do not silently switch ports; keep backend/frontend ports fixed and kill conflicting listeners explicitly when needed.
- `screen -list` on macOS may exit with code 1 even when sessions exist; scripts must tolerate this (avoid `set -euo pipefail` pipeline exits).
- When the user changes auth policy or seeded-account expectations, update all four surfaces together: backend config, tests, operator-facing docs, and deployment state.
