---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: '0.13'
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Evidence Review: Clinical Development and Market Response

```{raw} html
<p class="castalia-kicker">PUBLISHED HISTORY · ESTIMAND DISCIPLINE · SIMULATOR PRIORS</p>
```

This page records what published historical evidence can and cannot contribute to Quant.'s biotech research system. The distinction that governs the platform is simple: a development program advancing, a trial meeting an endpoint, and an issuer's stock rising are three different outcomes. We keep them separate in datasets, simulator states, and model claims.

## Clinical-development prior: progression is not an endpoint

The BIO, Informa Pharma Intelligence, and QLS Advisors report analyzed 12,728 phase transitions from Biomedtracker and Pharmapremia for 2011–2020. Its transition definition counts a program as successful when it advances to the next phase rather than being suspended. Reported all-disease transition rates were 28.9% from Phase II (4,933 transitions) and 57.8% from Phase III to NDA/BLA (1,928 transitions). These estimates vary by disease area and modality; for example, the report's infectious-disease estimates differ from its oncology estimates. [Source report](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf).

Quant.'s synthetic catalyst assumptions use 0.289 and 0.578 as *broad advancement-prior settings* for Phase II and Phase III events. This is a transparent starting point for the simulator, not a fitted forecast. The source cohort is proprietary, covers program transitions rather than the probability that a particular disclosed trial meets its primary endpoint, and aggregates many diseases and modalities. The simulator samples recurring independent catalyst events; it does not yet model a molecule's sequential path through development. Therapeutic-area priors and transition dependence belong in a later version once they can be estimated from a documented, fit-for-purpose dataset.

The separate Clinical Trial Outcome (CTO) human-label subset audited for this project is not substituted for the general prior. Its selected human-labeled sample deliberately omits easy cases and contains registry fields that may be hindsight. It remains an audited benchmark candidate, not a representative clinical-transition population or a market-return dataset; see the [CTO audit](../_static/cto-human-labels-audit.json).

## Market evidence: issuer type and event surprise matter

A 2013 event study matched manually collected announcements for 24 investigational compounds at seven large pharmaceutical firms to stock returns. It reported median announcement-window CAR of +0.8% for positive events and −2.0% for negative events; negative-event losses persisted into the following session, while positive returns partially corrected. The authors explicitly cautioned that their small, large-firm sample was not designed to support many predictors. [Open article](https://pmc.ncbi.nlm.nih.gov/articles/PMC3737210/).

A broader 2024 study analyzed 503,107 news articles for 1,012 biopharma companies from RavenPack, matched to CRSP returns. It reports that biotech firms and pharmaceutical firms react differently, with biotech stocks showing larger abnormal-return magnitudes, especially around negative product-development news. The article uses commercial news and return datasets; its aggregate results are evidence for model structure, not data Quant. can claim to reproduce. [PLOS One article](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0296927).

Together these studies motivate (a) asymmetric downside and tail reporting, (b) separate biotech and diversified-pharma strata, (c) issuer/pipeline concentration and event-surprise context, and (d) short event windows aligned to the first public disclosure. They do not justify assigning a stock return from a clinical outcome. The synthetic gym therefore draws advancement and market response separately. Its probabilities of a positive reaction conditional on advancement or suspension, and all gap sizes, remain explicitly uncalibrated.

## What changes in the platform

| Evidence | Platform decision | Boundary |
| --- | --- | --- |
| Phase-specific program transition rates | Set Phase II and III advancement-prior values in `config/biopharma_rl_synthetic.json` to 0.289 and 0.578 | Broad all-disease historical settings; not primary-endpoint success probabilities or a current biotech base rate |
| Negative trial/product news has consequential, potentially asymmetric market reactions | Keep downside and expected-shortfall metrics primary for catalyst risk; make success and stock response independent simulator draws | Published effect sizes are not directly imported as our synthetic gap distribution |
| Biotech and pharmaceutical reactions differ | Record issuer type, market/sector context, and pipeline concentration as planned cohort fields and evaluation strata | The current nine-disclosure, multi-area fixture cannot estimate these effects |
| Announcement time determines the first affected trading session | Preserve source, local timestamp, timezone, precision, and the next executable session convention | Date-only records stay lower precision and require sensitivity analysis |

The return hierarchy is documented in [Return Metrics](metrics.md): use net CAGR and benchmark-relative compounded wealth with maximum drawdown for an investable policy; use Brier score and log loss against fold-local base-rate forecasts for event probabilities; and report market-model CAR with event/issuer counts for descriptive event studies. No single metric can establish a robust edge.

## Data needed to move from prior to estimate

The historical pilot now contains nine sourced disclosures across vaccine, Alzheimer's, asthma, and oncology programs, but no licensed market-price bars. The event count remains too small and clustered for fitting or calibration. Expand the ledger across therapeutic areas, outcomes, issuer types, and market periods; preserve inactive and acquired issuers; verify first public disclosures; acquire point-in-time study versions; and join a price feed whose terms allow the intended local analysis and public summaries. Then preregister the windows, event/issuer grouping, sector and market controls, and chronological holdout. Until that exists, the advancement prior is the only historical aggregate used by the gym; return-generating market assumptions remain synthetic.
