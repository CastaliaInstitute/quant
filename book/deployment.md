# Cloudflare Deployment Runbook

```{raw} html
<p class="castalia-kicker">PAGES · PYTHON WORKER · CUSTOM DOMAIN</p>
```

The production workflow is [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml). It runs project checks and builds the Jupyter Book, provisions the `quantlab` Pages project, deploys the bounded Python cell Worker, publishes the book, then attaches `quant.castalia.institute` and updates its DNS record. The Pages project and domain are managed by [`scripts/configure_cloudflare_pages.py`](../scripts/configure_cloudflare_pages.py); the Worker custom domain is declared in [`worker/wrangler.toml`](../worker/wrangler.toml).

## Create the Cloudflare API token

Create a custom API token in Cloudflare and restrict it to the Castalia account and `castalia.institute` zone. The current workflow needs these permissions:

| Resource | Permission | Why the workflow needs it |
| --- | --- | --- |
| Account | Account Settings: Read | Wrangler account and deployment metadata |
| Account | Cloudflare Pages: Edit | Create the Pages project, upload deployments, and attach the custom domain |
| Account | Workers Scripts: Edit | Publish `quantlab-cells` |
| Zone `castalia.institute` | Zone: Read | Find and validate the zone before DNS changes |
| Zone `castalia.institute` | DNS: Read, DNS: Edit | Inspect and replace the `quant` CNAME |
| Zone `castalia.institute` | Workers Routes: Edit/Write | Provision the Worker custom domain `cells.quant.castalia.institute` |
| User | User Details: Read, Memberships: Read | Wrangler identity and account-membership checks |

Cloudflare's [API token permission reference](https://developers.cloudflare.com/fundamentals/api/reference/permissions/), [Pages project API](https://developers.cloudflare.com/api/resources/pages/subresources/projects/methods/create/), and [Workers CI/CD configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/) document these permission families. Workers custom domains also require Worker access and zone-scoped Workers Routes permission (labeled Edit or Write across Cloudflare's token interfaces), as described in [Workers roles and permissions](https://developers.cloudflare.com/workers/authorization/workers/).

## Add the GitHub Actions secret

In the `CastaliaInstitute/quant` repository, open **Settings → Secrets and variables → Actions → New repository secret** and create:

| Name | Value |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | The new custom token |

`CLOUDFLARE_ACCOUNT_ID` is already configured as a repository secret. Keep both values in GitHub Actions secrets; do not commit them or paste them into an issue, notebook, or chat. GitHub's [Actions secret instructions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets) show the repository settings path.

## Deploy and verify

After saving the secret, open **Actions → Build and deploy QuantLab → Run workflow**, select `main`, and start the run. A push to `main` triggers the same workflow. The build job runs the automated project checks and produces the book before any deployment steps begin.

The domain step replaces a single existing CNAME for `quant.castalia.institute` with a proxied CNAME to `quantlab.pages.dev`. It stops before changing DNS if it finds multiple records or a non-CNAME record at that hostname. Once the workflow succeeds, verify all three routes:

```bash
curl -fsS https://quant.castalia.institute/
curl -fsS https://quantlab.pages.dev/
curl -fsS https://cells.quant.castalia.institute/health
```

The Worker health route should return JSON with `"status":"ok"`. Also open the research book and execute one of its teaching cells to verify the browser-to-Worker path. A successful GitHub build alone does not confirm that the custom domain, TLS certificate, DNS, or Worker is serving correctly.
