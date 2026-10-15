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

## Source-linked cohort expansion

The manually curated event ledger now has eighteen issuer disclosures linked to nineteen trial records. These additions broaden the source fixture beyond pandemic vaccines and include mixed oncology outcomes, rare disease, and chronic respiratory disease. Each URL is the sponsor or issuer announcement used to establish its public date; the exact-time entries preserve the time shown by the issuer/newswire, and date-only entries do not invent one. The linked source audit records the complete catalog and precision counts. This is a traceability sample; inclusion remains selective and does not make it representative.

| Public date/time | Issuer and program | Curated event label | Primary disclosure |
| --- | --- | --- | --- |
| 2017-12-14 16:45 EST | Merck, KEYNOTE-061 (NCT02370498) | Phase III primary OS endpoint miss | [Merck release](https://www.merck.com/news/merck-provides-update-on-keynote-061-a-phase-3-study-of-keytruda-pembrolizumab-in-previously-treated-patients-with-gastric-or-gastroesophageal-junction-adenocarcinoma/) |
| 2018-11-14 06:45 EST | Merck, KEYNOTE-181 (NCT02564263) | Phase III positive in prespecified PD-L1 subgroup | [Merck release](https://www.merck.com/news/mercks-keytruda-pembrolizumab-significantly-improved-overall-survival-os-compared-to-chemotherapy-in-patients-with-advanced-esophageal-or-esophagogastric-junction-carcinoma-whose-tu/) |
| 2019-05-20 15:30 EDT | Merck, KEYNOTE-119 (NCT02555657) | Phase III primary OS endpoint miss | [Merck release](https://www.merck.com/news/merck-provides-update-on-phase-3-keynote-119-study-of-keytruda-pembrolizumab-monotherapy-in-previously-treated-patients-with-metastatic-triple-negative-breast-cancer/) |
| 2022-09-11 18:05 EDT | Amgen, CodeBreaK 200 (NCT04303780) | Phase III positive PFS readout | [Amgen release](https://www.amgen.com/newsroom/press-releases/2022/09/lumakraslumykras-sotorasib-demonstrates-superior-progressionfree-survival-over-docetaxel-in-first-positive-phase-3-trial-of-a-kras-g12c-inhibitor-in-nonsmall-cell-lung-cancer) |
| 2022-09-27, date-only | Biogen/Eisai, CLARITY AD (NCT03887455) | Phase III positive readout | [Biogen release](https://investors.biogen.com/news-releases/news-release-details/lecanemab-confirmatory-phase-3-clarity-ad-study-met-primary) |
| 2023-10-30 16:01 EDT | Sarepta, EMBARK (NCT05096221) | Primary endpoint miss; secondary endpoints favored treatment | [Sarepta release](https://sarepta.gcs-web.com/node/22976) |
| 2024-11-07, date-only | Amgen/AstraZeneca, WAYPOINT (NCT04851964) | Phase III positive co-primary endpoints | [Amgen release](https://www.amgen.com/newsroom/press-releases/2024/11/tezspire-met-both-co-primary-endpoints-in-phase-3-trial-for-chronic-rhinosinusitis-with-nasal-polyps) |

These labels summarize what the release says, not a harmonized endpoint adjudication. For example, KEYNOTE-181's positive label applies to the prespecified PD-L1 CPS ≥10 population, and EMBARK missed its primary endpoint despite positive secondary outcomes. The event catalog also preserves joint-development relationships while assigning one price series per disclosure to avoid duplicating a single market event.

## What changes in the platform

| Evidence | Platform decision | Boundary |
| --- | --- | --- |
| Phase-specific program transition rates | Set Phase II and III advancement-prior values in `config/biopharma_rl_synthetic.json` to 0.289 and 0.578 | Broad all-disease historical settings; not primary-endpoint success probabilities or a current biotech base rate |
| Negative trial/product news has consequential, potentially asymmetric market reactions | Keep downside and expected-shortfall metrics primary for catalyst risk; make success and stock response independent simulator draws | Published effect sizes are not directly imported as our synthetic gap distribution |
| Biotech and pharmaceutical reactions differ | Record issuer type, market/sector context, and pipeline concentration as planned cohort fields and evaluation strata | The current eighteen-disclosure, multi-area fixture cannot estimate these effects |
| Announcement time determines the first affected trading session | Preserve source, local timestamp, timezone, precision, and the next executable session convention | Date-only records stay lower precision and require sensitivity analysis |

The return hierarchy is documented in [Return Metrics](metrics.md): use net CAGR and benchmark-relative compounded wealth with maximum drawdown for an investable policy; use Brier score and log loss against fold-local base-rate forecasts for event probabilities; and report market-model CAR with event/issuer counts for descriptive event studies. No single metric can establish a robust edge.

## Data needed to move from prior to estimate

The historical pilot now contains eighteen sourced disclosures across vaccines, Alzheimer’s disease, asthma, oncology, eosinophilic esophagitis, heart failure, chronic rhinosinusitis with nasal polyps, and Duchenne muscular dystrophy, but no licensed market-price bars. The event count remains far too small and clustered for fitting or calibration. Expand the ledger across therapeutic areas, outcomes, issuer types, and market periods; preserve inactive and acquired issuers; verify first public disclosures; acquire point-in-time study versions; and join a price feed whose terms allow the intended local analysis and public summaries. Then preregister the windows, event/issuer grouping, sector and market controls, and chronological holdout. Until that exists, the advancement prior is the only historical aggregate used by the gym; return-generating market assumptions remain synthetic.
