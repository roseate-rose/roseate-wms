# Fly Deploy Script Todo

## Scope
- [x] Inspect repository deployment conventions before adding a Fly helper script
- [x] Add `deploy.sh` to create the Fly volume when missing and run `flyctl deploy`
- [x] Document `flyctl secrets set JWT_SECRET_KEY=...` in the README
- [x] Verify the script content and deployment docs are internally consistent

## Implementation Notes
- The helper should be safe to re-run by checking for an existing volume first.
- The script should target the existing `fly.toml` app name and mount name by default.
- JWT secrets must stay out of git and be configured with `flyctl secrets set`.

## Review / Summary
- [x] `deploy.sh` covers volume creation and deployment
- [x] README and dev log updated with secrets guidance
- [x] Script syntax verified with `bash -n deploy.sh`
