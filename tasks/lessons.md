# Lessons

- Keep unit conversion as a single source of truth (`base_unit`, `purchase_unit`, `conversion_rate`); do not introduce a second representation (e.g. fractional “0.2盒” storage or extra factor columns) unless explicitly approved.
- `extra_data` is extensible but should be operator-visible; default UI should render it collapsed/folded with an explicit expand action.
