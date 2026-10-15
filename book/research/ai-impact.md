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

# AI Impact Watch: From Claims to Measurable Outcomes

```{raw} html
<p class="castalia-kicker">BIOTECH PIPELINES · TRIAL OPERATIONS · COMPANY VALUE</p>
```

Quant. will monitor AI's impact across drug discovery, clinical development, and biopharma companies. The watch is designed around dated evidence and comparison groups. A company describing itself as “AI-powered” is an exposure claim; it is not evidence that a candidate is safer, more effective, faster to develop, or more valuable.

## Live evidence monitor

```{raw} html
<section class="ai-impact-monitor" aria-live="polite" aria-labelledby="ai-monitor-title">
  <h3 id="ai-monitor-title">What can we measure today?</h3>
  <p class="ai-monitor-status">Loading the versioned evidence ledger…</p>
  <div class="ai-monitor-literature">Loading published cohort context…</div>
  <div class="ai-monitor-grid"></div>
  <p class="ai-monitor-note"></p>
</section>
<script src="../_static/ai-impact-monitor.js" defer></script>
```

The monitor is deliberately a coverage instrument. Its three lanes are scientific outcomes (molecule or trial results), operational outcomes (time, cost, or trial execution), and economic outcomes (issuer value, revenue, or market response). The large number is the count of reviewed outcomes that directly contrast AI exposure; comparator coverage is shown separately. A populated clinical comparator is not an estimate of AI's effect: the rentosertib comparison is drug versus placebo, not AI-assisted versus conventional discovery.

## What current evidence says—and doesn't say

- A 2024 analysis of clinical pipelines at AI-native biotech companies reported 80–90% Phase I success and about 40% Phase II success for AI-discovered molecules. The authors described the Phase II sample as limited. This is an early, selected pipeline cohort, not a randomized comparison or a mature Phase III estimate. It motivates a replication with explicit molecule-level inclusion rules; Quant. does not use these percentages as simulator priors. [Jayatunga et al., *Drug Discovery Today* (2024)](https://www.sciencedirect.com/science/article/pii/S135964462400134X).
- A newer cross-sectional analysis identified 129 AI-enabled therapeutic assets across 69 companies that had entered interventional trials by March 1, 2026. It reported observed Phase I and Phase II probabilities of success of 77.8% and 19.5%; 72 assets had completed Phase I, 24 had completed Phase II, and five had entered or completed Phase III. This is a larger, later snapshot, but still a descriptive cohort without a matched conventional control; AI enablement was based on public reporting and its definition may vary. The 2024 and 2026 rates have different cohort construction and follow-up and must not be pooled or read as evidence that AI caused either rate. Quant. records this as published cohort context, not an AI uplift or simulator prior. [*Cancer Treatment Reviews* (online October 8, 2026)](https://doi.org/10.1016/j.ctrv.2026.103223).
- A 2010–2023 ClinicalTrials.gov analysis identified 3,106 registered AI/ML studies across health care, not just drug discovery. It found rapid growth in registrations but only 5.6% of completed studies had results posted in the registry. Keyword matches therefore measure visible registration activity, and incomplete results can create serious selection bias. [Maru et al., *Journal of Medical Internet Research* (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11549584/).
- FDA reports more than 500 submissions with AI components from 2016–2023, spanning nonclinical, clinical, postmarketing, and manufacturing activity. This shows regulatory use is broader than AI-designed molecules. FDA's 2025 draft guidance and January 2026 good-practice principles are useful for the watch's application taxonomy, but submission counts alone do not establish better development outcomes. [FDA AI for Drug Development](https://www.fda.gov/about-fda/center-drug-evaluation-and-research-cder/artificial-intelligence-drug-development).
- A useful molecule-level case is rentosertib (formerly ISM001-055), linked to NCT05938920. Its Phase IIa paper describes a generative-AI-discovered TNIK target and AI-generated molecule. At week 12, the 60 mg once-daily arm (n=18) had mean FVC change of +98.4 mL (95% CI 10.9 to 185.9), versus −20.3 mL (95% CI −116.1 to 75.6) for placebo (n=17). FVC was a secondary measure in a 71-person, 12-week study. This is a clinical signal for one candidate; it does not estimate AI's contribution versus conventional discovery, and it does not measure development-time savings or market impact. [Peer-reviewed Phase IIa report](https://pmc.ncbi.nlm.nih.gov/articles/PMC12353801/).

These sources differ in population, AI definition, follow-up, and outcome. The two clinical-pipeline studies, broad registry census, and FDA submission count must remain separate evidence rows—not be combined into one “AI success rate.” The newer cohort adds a reason to keep phase-specific advancement and time-to-transition under observation: the pipeline is growing, but the observed Phase II progression is not a demonstrated improvement over a matched conventional cohort.

## Three research questions

### 1. Does AI-associated discovery change clinical progression?

Define exposure at the **molecule-program** level, before first-in-human entry: what AI application was used, how material its role was, which candidate it affected, and when the claim first became public. Compare phase transitions with conventional programs matched or stratified by indication, modality, phase, start era, sponsor type, and geography. Treat withdrawal, suspension, and missing follow-up explicitly; estimate progression and time-to-transition separately. A sponsor's AI status cannot stand in for evidence that a specific candidate was AI-derived.

Report phase-specific numerator/denominator, censoring, missing outcome coverage, effect intervals, and leave-one-sponsor-out sensitivity. A small Phase I cohort can look unusually successful because it contains few events and selected candidates. Do not extrapolate it through Phase III or to approval.

### 2. Does AI change trial execution?

Tag clinical-operations applications separately from molecule discovery: site selection, patient recruitment, eligibility matching, protocol design, monitoring, data capture, and endpoint analysis. Compare enrollment and completion timelines within comparable phase/indication/design cohorts. Adjust for study size, number of sites, geography, pandemic-era disruption, and changes in registration practices. Trial duration is an operational outcome; it is not a measure of treatment efficacy.

### 3. Does public AI evidence move a company's value?

Create a dated catalog of first verifiable disclosures: validated candidate entry, trial milestone, partnership, licensing deal, platform revenue, or material capital/expense commitment. Estimate issuer CAR and event-window downside with broad-market and biotech-sector controls. Separate AI-discovery catalysts from general partnerships, financing, acquisitions, and ordinary earnings news. A price reaction measures changed expectations at the disclosure; it does not prove scientific impact or durable revenue.

## Exposure classification and evidence ledger

The tracked unit is a **company, candidate/program, trial, or disclosure**, with explicit links among them. Classify each record along two axes:

| Axis | Values to curate | Example distinction |
| --- | --- | --- |
| AI application | target discovery; molecule design/optimization; biomarker or patient stratification; trial design/recruitment; clinical data analysis; manufacturing/quality; regulatory/postmarket; general productivity | Generative molecule design and LLM-written regulatory summaries answer different scientific and economic questions |
| Evidence strength | public claim; specific workflow disclosed; candidate-level attribution; independently supported use; measured comparative result | A press release saying “AI-powered platform” is weaker evidence than a named molecule with a peer-reviewed or regulatory-verified AI role |

Every record needs a public-availability date and its precision (date-only or exact timestamp), source URL and hash, entity mapping, curator status, and taxonomy version. Outcome rows explicitly indicate whether their comparator contrasts AI exposure (`ai_exposure_contrast=yes/no/unclear`). Keep AI exposure records separate from transition outcomes and stock returns so future evidence cannot leak into a historical feature. The exposure ledger is [`data/biopharma/ai_evidence.csv`](../../data/biopharma/ai_evidence.csv), with fields defined in [`ai_evidence.schema.csv`](../../data/biopharma/ai_evidence.schema.csv). Outcome observations live separately in [`ai_outcomes.csv`](../../data/biopharma/ai_outcomes.csv), defined by [`ai_outcomes.schema.csv`](../../data/biopharma/ai_outcomes.schema.csv).

The new [`scripts/monitor_ai_trials.py`](../../scripts/monitor_ai_trials.py) creates a versioned ClinicalTrials.gov AI/ML-keyword discovery snapshot. The current snapshot contains 6,734 broad candidates, not 6,734 AI-discovered medicines. It does **not** label studies as AI drug discovery: keyword results can concern medical AI interventions, imaging, decision support, or incidental mentions. The raw records and manifest stay under ignored `data/raw/`; a curator must screen them against the application taxonomy. The ClinicalTrials.gov API serves current study records, so retrieve historical versions and original public disclosures before using any registry attribute as a past feature.

Run [`scripts/audit_ai_impact.py`](../../scripts/audit_ai_impact.py) to update the coverage report at [`_static/ai-impact-monitor.json`](../_static/ai-impact-monitor.json). It reads three separate inputs: the dated exposure ledger, outcome ledger, and [`ai_literature.csv`](../../data/biopharma/ai_literature.csv), a curated bibliography of published cohort context. It counts reviewed dated and exact-timestamp exposures, plus reviewed outcomes with comparison groups and study designs; the live panel also shows the latest reviewed cohort and whether it reports a direct AI comparator. It deliberately reports **coverage only**: populated comparator records do not establish causality without a defensible cohort design, confounder handling, sensitivity analysis, and enough observations. The seeded rentosertib case gives us one reviewed program-level clinical observation; the published 2026 cohort adds context but no direct AI-versus-conventional comparison. Market impact remains unmeasured until verified catalyst timestamps and licensed price data are joined. Revisit publications and registry snapshots as assets advance, reclassifications appear, and outcomes become available; preserve dated cohort versions instead of overwriting historical evidence.

## How this enters the simulator and model

The RL gym should represent AI as a **scenario dimension with uncertainty**, not a guaranteed bonus to efficacy. Candidate forks can vary discovery hit rate, time/cost to candidate, trial execution time, and downstream transition probability independently. Each parameter needs a source-backed interval, a named population, and correlation assumptions; only training-window observations may update a historical replay. Policies are evaluated across pessimistic, central, and optimistic scenarios, against a no-AI baseline and simple operating policies.

For market prediction, use AI evidence only after it was public by the decision cutoff, and only for the relevant company or program. Compare incremental Brier/log-loss skill for event risk and net benchmark-relative performance for any strategy. Control for issuer size, pipeline concentration, therapeutic area, modality, prior volatility, and market regime. Keep CAR, clinical advancement, trial time/cost, and commercial value as separate targets.

## First monitor release and evidence gates

1. Snapshot registry keyword candidates and preserve the query, API data timestamp, and content hash.
2. Manually curate a pilot molecule/program cohort from primary sources; record inclusion/exclusion reason, AI role, sponsor/ticker, first-human date, and evidence grade.
3. Link registry records and publications to the molecule and sponsor, then independently verify reported phase outcomes and dates.
4. Add licensed prices and disclosure timestamps before publishing event-return estimates.
5. Compare against matched non-AI programs and conventional trial-operation cohorts, disclose missing results, and preserve a chronological holdout.

Until those gates pass, the public monitor reports source coverage and curation status only. It does not present an AI-versus-non-AI success gap or stock-return edge.
