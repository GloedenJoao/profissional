# Routers

Routers translate HTTP requests into service calls.

## Rules

- Do not put strategy execution, metric, or data-fetching logic here.
- Use redirects after mutating POST requests.
- Render templates with already-computed service outputs.
- Keep API routes deterministic and easy to test with `TestClient`.
- Legacy `/predictions/new` should redirect to the strategy run form.
