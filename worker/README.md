# QuantLab cell Worker

This Cloudflare Python Worker executes the small code examples embedded in the QuantLab research book. It is a teaching runtime, not a general-purpose notebook server.

## Runtime contract

- `POST /execute` accepts 1–12 ordered code cells. The Worker reconstructs a fresh namespace and executes them in order for that request.
- Cell source is limited to 4,000 characters each and 20,000 characters per page request.
- Only basic expressions, assignments, bounded loops and comprehensions, comparisons, and documented helper calls are allowed.
- Imports, attribute access, filesystem and network operations, arbitrary function definitions, and brokerage calls are unavailable.
- Outputs and arithmetic/collection growth are capped. No state is persisted between requests.
- Browser calls are accepted only from the QuantLab site origin and local preview origin.

These restrictions reduce the available surface; they are not a substitute for a dedicated adversarially audited sandbox. Keep the Worker free of secrets and privileged bindings.

## Local development

Install `uv` 0.12.3 or later and Node.js, then run:

```bash
uv sync --group dev
uv run pywrangler dev
```

The book's browser runner targets `https://cells.quant.castalia.institute`. For local browser development, temporarily point `workerBase` in `book/_static/live-cells.js` at the local Worker and use the listed local CORS origin.

## Deploy

```bash
uv run --group dev pywrangler deploy
```

Cloudflare provisions the `cells.quant.castalia.institute` custom domain from the Wrangler configuration.
