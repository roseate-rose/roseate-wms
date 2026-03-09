# Docker Packaging Todo

## Scope
- [x] Inspect current Flask app and determine how built Vue assets should be served in production
- [x] Add a multi-stage Dockerfile that builds the frontend, installs backend dependencies, and runs Flask with Gunicorn
- [x] Ensure the backend serves `frontend/dist` static assets and SPA history fallback correctly
- [x] Add targeted backend tests for built asset serving and missing API/static 404 behavior
- [x] Synchronize `README.md`, `tasks/devlog.md`, and this file with container runtime guidance
- [x] Verify pytest and frontend build still pass after the packaging changes

## Implementation Notes
- The runtime image should contain only Python, backend code, and the compiled `frontend/dist` bundle.
- Vue history routing needs an `index.html` fallback for non-API paths, while `/api/...` misses must remain JSON 404 responses.
- Missing hashed/static asset paths should return 404 instead of incorrectly falling back to `index.html`.

## Review / Summary
- [x] Docker packaging changes verified with `python3 -m pytest backend/tests` (`17 passed`)
- [x] Docker packaging changes verified with `npm run build`
- [x] README and dev log updated with build/run instructions
- [x] Docker CLI availability checked; local `docker build` was not run because `docker` is not installed in this environment
