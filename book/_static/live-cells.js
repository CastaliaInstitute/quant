(() => {
  const workerBase = "https://cells.quant.castalia.institute";
  const cells = [...document.querySelectorAll(".cell")].filter((cell) => cell.querySelector(".cell_input pre"));
  if (!cells.length) return;

  const getSource = (cell) => cell.querySelector(".cell_input pre")?.innerText ?? "";
  const toolbar = document.createElement("div");
  toolbar.className = "live-cell-toolbar";
  toolbar.innerHTML = '<span>CASTALIA PYTHON WORKER · STATE REBUILT PER RUN · NO EXTERNAL DATA</span><button type="button">Run all live cells</button>';
  const article = document.querySelector("article.bd-article, main .bd-content .bd-article");
  const firstHeading = article?.querySelector("h1");
  if (firstHeading) firstHeading.after(toolbar);

  const state = new Map();
  const showOutput = (cell, result) => {
    let output = state.get(cell)?.output;
    if (!output) {
      output = document.createElement("pre");
      output.className = "live-cell-output";
      const controls = state.get(cell)?.controls;
      (controls ?? cell).after(output);
      if (state.get(cell)) state.get(cell).output = output;
    }
    output.textContent = result?.output ?? "No output";
    output.classList.toggle("error", result?.ok === false);
  };

  cells.forEach((cell, index) => {
    const controls = document.createElement("div");
    controls.className = "live-cell-controls";
    const run = document.createElement("button");
    run.type = "button";
    run.className = "live-cell-run";
    run.textContent = "Run cell";
    const status = document.createElement("span");
    status.className = "live-cell-status";
    status.setAttribute("aria-live", "polite");
    controls.append(run, status);
    cell.after(controls);
    state.set(cell, { controls, status, run, output: null });

    run.addEventListener("click", async () => {
      await runThrough(index);
    });
  });

  async function runThrough(lastIndex) {
    const pageCells = cells.slice(0, lastIndex + 1);
    for (const cell of pageCells) {
      const item = state.get(cell);
      item.run.disabled = true;
      item.status.textContent = "Running on Worker…";
    }
    if (toolbar) toolbar.querySelector("button").disabled = true;
    try {
      const response = await fetch(`${workerBase}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cells: pageCells.map(getSource) }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error ?? `Worker returned ${response.status}`);
      (payload.outputs ?? []).forEach((result, index) => {
        const cell = pageCells[index];
        showOutput(cell, result);
        state.get(cell).status.textContent = result.ok ? "Executed · synthetic lesson code" : "Cell rejected or failed";
      });
    } catch (error) {
      const last = pageCells[pageCells.length - 1];
      showOutput(last, { ok: false, output: `Worker unavailable: ${error.message}` });
      state.get(last).status.textContent = "Execution unavailable";
    } finally {
      for (const cell of pageCells) state.get(cell).run.disabled = false;
      if (toolbar) toolbar.querySelector("button").disabled = false;
    }
  }

  toolbar?.querySelector("button")?.addEventListener("click", () => runThrough(cells.length - 1));
})();
