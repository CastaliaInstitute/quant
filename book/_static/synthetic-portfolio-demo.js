(() => {
  const root = document.querySelector('.portfolio-simulation-monitor');
  if (!root) return;
  const status = root.querySelector('.portfolio-demo-status');
  const tableRoot = root.querySelector('.portfolio-demo-table');
  const labels = {
    cash: 'Cash',
    equal_weight: 'Equal-weight issuers',
    inverse_volatility: 'Inverse-volatility issuers',
    '20d_trend': '20-session trend',
  };
  const pct = value => `${(100 * value).toFixed(1)}%`;
  fetch('../_static/synthetic-portfolio-demo.json', { cache: 'no-store' })
    .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(report => {
      const table = document.createElement('table');
      const thead = document.createElement('thead');
      const header = document.createElement('tr');
      for (const text of ['Policy', 'Relative wealth vs synthetic XBI · 1× / 2× / 4× costs', 'Net CAGR · 1×', 'Max drawdown', '5% expected shortfall', 'Annual turnover']) {
        const cell = document.createElement('th'); cell.textContent = text; header.append(cell);
      }
      thead.append(header);
      const tbody = document.createElement('tbody');
      for (const [key, label] of Object.entries(labels)) {
        const policy = report.policies[key];
        if (!policy) continue;
        const costs = policy.cost_sensitivity;
        const row = document.createElement('tr');
        const cells = [
          label,
          costs.map(result => pct(result.benchmark_relative_compounded_return)).join(' / '),
          pct(costs[0].annualized_return),
          pct(costs[0].max_drawdown),
          pct(costs[0].expected_shortfall_95),
          `${costs[0].annual_turnover.toFixed(1)}×`,
        ];
        for (const value of cells) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }
        tbody.append(row);
      }
      table.append(thead, tbody);
      tableRoot.replaceChildren(table);
      status.textContent = `${report.market.periods} synthetic sessions · ${report.market.assets.length} synthetic issuers · ${Object.values(report.market.scheduled_catalyst_counts).reduce((a, b) => a + b, 0)} generated catalysts. ${report.interpretation}`;
    })
    .catch(() => { status.textContent = 'Simulation report unavailable; rebuild it with scripts/build_synthetic_portfolio_demo.py.'; });
})();
