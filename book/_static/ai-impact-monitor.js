(() => {
  const root = document.querySelector('.ai-impact-monitor');
  if (!root) return;
  const status = root.querySelector('.ai-monitor-status');
  const grid = root.querySelector('.ai-monitor-grid');
  const note = root.querySelector('.ai-monitor-note');
  const lanes = [
    ['scientific', 'Scientific impact', 'Clinical efficacy or progression'],
    ['operational', 'Operational impact', 'Trial time, execution, or development cost'],
    ['economic', 'Economic impact', 'Company value, revenue, or market response'],
  ];
  fetch('../_static/ai-impact-monitor.json', { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(data => {
      for (const [key, title, description] of lanes) {
        const lane = data.outcome_ledger?.impact_lanes?.[key] ?? {};
        const card = document.createElement('article');
        card.className = 'ai-monitor-card';
        const heading = document.createElement('h4'); heading.textContent = title;
        const value = document.createElement('strong'); value.textContent = `${lane.direct_ai_exposure_contrasts ?? 0} AI contrasts`;
        const detail = document.createElement('p'); detail.textContent = `${lane.reviewed_records ?? 0} reviewed outcomes · ${lane.reviewed_comparator_records ?? 0} with a comparator · ${description}`;
        const tag = document.createElement('span'); tag.className = 'ai-monitor-pill'; tag.textContent = 'No AI effect estimate';
        card.append(heading, value, detail, tag); grid.append(card);
      }
      const exposure = data.exposure_ledger ?? {};
      status.textContent = `${exposure.reviewed_records ?? 0} reviewed AI exposure record(s); ${data.outcome_ledger?.records ?? 0} outcome record(s). This is evidence coverage, not an AI score.`;
      note.textContent = data.current_case_note ?? data.interpretation ?? '';
    })
    .catch(() => { status.textContent = 'Monitor data could not be loaded. See the linked evidence ledger and audit JSON.'; });
})();
