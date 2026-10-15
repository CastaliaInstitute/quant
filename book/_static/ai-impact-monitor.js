(() => {
  const root = document.querySelector('.ai-impact-monitor');
  if (!root) return;
  const status = root.querySelector('.ai-monitor-status');
  const literature = root.querySelector('.ai-monitor-literature');
  const grid = root.querySelector('.ai-monitor-grid');
  const note = root.querySelector('.ai-monitor-note');
  const lanes = [
    ['scientific', 'Scientific impact', 'Clinical efficacy or progression'],
    ['operational', 'Operational impact', 'Trial time, execution, cost, or productivity'],
    ['economic', 'Economic impact', 'Company value, revenue, market response, or labor'],
    ['patient_access_and_safety', 'Patient impact', 'Access, safety, and health equity'],
    ['workforce_and_society', 'Workforce impact', 'Employment, work quality, and scientific roles'],
    ['environmental', 'Environmental impact', 'Energy, compute, and emissions'],
  ];
  fetch('../_static/ai-impact-monitor.json', { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(data => {
      const cohort = data.literature_watch?.latest_abstract_reviewed_study;
      if (cohort) {
        const heading = document.createElement('strong');
        heading.textContent = `Latest published cohort · ${cohort.publication_date}`;
        const summary = document.createElement('p');
        summary.textContent = `${cohort.asset_count} assets across ${cohort.company_count} companies through ${cohort.cohort_cutoff}; reported Phase I / II success rates ${cohort.phase_1_success_rate} / ${cohort.phase_2_success_rate}. No direct AI comparator; descriptive context only.`;
        const source = document.createElement('a');
        source.href = cohort.source_url;
        source.textContent = 'Open source';
        source.rel = 'noopener noreferrer';
        source.target = '_blank';
        literature.replaceChildren(heading, summary, source);
      } else {
        literature.textContent = 'No reviewed published cohort summary is available.';
      }
      for (const [key, title, description] of lanes) {
        const lane = data.outcome_ledger?.impact_lanes?.[key] ?? {};
        const card = document.createElement('article');
        card.className = 'ai-monitor-card';
        const heading = document.createElement('h4'); heading.textContent = title;
        const value = document.createElement('strong'); value.textContent = lane.estimate_available ? 'Estimate available' : `${lane.direct_ai_exposure_contrasts ?? 0} direct AI contrasts`;
        const dimensions = Object.entries(lane.dimensions ?? {}).map(([name, count]) => `${name.replaceAll('_', ' ')} (${count})`).join(', ');
        const affected = Object.entries(lane.affected_groups ?? {}).map(([name, count]) => `${name.replaceAll('_', ' ')} (${count})`).join(', ');
        const detail = document.createElement('p'); detail.textContent = `${lane.reviewed_records ?? 0} reviewed outcomes · ${lane.reviewed_comparator_records ?? 0} with a comparator · ${description}${dimensions ? ` · observed dimensions: ${dimensions}` : ''}${affected ? ` · affected groups: ${affected}` : ''}`;
        const tag = document.createElement('span'); tag.className = 'ai-monitor-pill'; tag.textContent = lane.estimate_available ? 'Reviewed estimate' : 'No AI effect estimate';
        card.append(heading, value, detail, tag); grid.append(card);
      }
      const exposure = data.exposure_ledger ?? {};
      const outcomes = data.outcome_ledger ?? {};
      status.textContent = `${exposure.reviewed_records ?? 0} reviewed AI exposure record(s) · ${outcomes.reviewed_records ?? 0} reviewed outcome(s) · ${outcomes.reviewed_direct_ai_exposure_contrasts ?? 0} direct AI-exposure comparisons. Coverage is not an AI score.`;
      note.textContent = data.current_case_note ?? data.interpretation ?? '';
    })
    .catch(() => { status.textContent = 'Monitor data could not be loaded. See the linked evidence ledger and audit JSON.'; });
})();
