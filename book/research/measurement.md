---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
kernelspec:
  name: python3
  display_name: Python 3
---

# Measurement: Biomedical Events Meet the Market Clock

```{raw} html
<p class="castalia-kicker">INQUIRY 001 · TIMESTAMPS · FEATURE CUTS</p>
```

In biotech event research, a feature is valid only if the information was public and available before the decision timestamp. A trial's present-day ClinicalTrials.gov record is not automatically a historical record of what the market knew when the company announced results. The current data pull explicitly labels latest-record trial and publication attributes as hindsight annotations; do not pass those fields to a historical prediction model.

## Market context before the catalyst

For adjusted close `P[t]`, simple return is `P[t] / P[t-1] - 1`. A five-session momentum feature compounds returns ending at the last close before the public catalyst. Realized volatility uses only prior sessions. Relative volume compares that last complete session with a trailing reference; the event-day volume is a response, not a pre-event feature.

```{code-cell} python
prices = [100.0, 101.0, 100.5, 102.0, 103.0, 102.5, 104.0, 105.0]
returns = []
for index in range(1, len(prices)):
    returns.append(prices[index] / prices[index - 1] - 1)

momentum = 1.0
for value in returns[-5:]:
    momentum = momentum * (1.0 + value)
momentum = momentum - 1.0
print("Synthetic trailing five-session momentum:", round(momentum, 4))
```

The numbers above are synthetic to demonstrate the arithmetic. They are not market prices. Real trial, publication, and price sources with their current limitations are listed in the [biopharma data guide](../data-sources.md).

## Feature and source ledger

| Candidate field | Potential use | Availability condition / failure mode |
| --- | --- | --- |
| Price trend, volatility, relative volume | Market-implied risk context | Compute from licensed bars ending strictly before the event; do not include reaction sessions |
| Trial phase, enrollment, design, indication, intervention | Clinical development context | Require a point-in-time study-record version; latest registry values can include later changes |
| Primary and secondary endpoints | Trial design / statistical context | Freeze endpoint wording, analysis population, and version before outcome disclosure |
| Biomedical publication evidence | Scientific context and competing evidence | Keep DOI/PMID, first-online date, version, and accessible text rights; papers linked to a trial today may have been linked later |
| Company press release / SEC exhibit | Catalyst timestamp and reported result | Preserve first public time, time zone, URL, source type, and correction/republication history |
| Biotech index and broad market returns | Common-factor control | Match session calendar and corporate actions; preserve vendor/feed lineage |

The initial model target is market downside in a declared post-disclosure window. It does not predict clinical efficacy. Scientific readout outcome and stock return are separate labels: trial success may already be expected, may affect only a small part of a diversified company's pipeline, or may be offset by other news.

## Freeze lineage before model fit

For every dataset, preserve source URL or identifier, retrieval timestamp, API/data version, coverage dates, checksum, missing-value and update policy, timezone, and license. Resolve issuer/ticker history—including mergers, delistings, ADRs, and name changes—before building the panel. The local event panel intentionally labels latest-record fields as hindsight-only until archival versions are added.
