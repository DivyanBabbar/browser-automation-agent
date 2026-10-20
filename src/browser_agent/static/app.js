const form = document.querySelector("#planForm");
const busy = document.querySelector("#busy");
const errorPanel = document.querySelector("#error");
const runPanel = document.querySelector("#runPanel");
const history = document.querySelector("#history");
let currentRun = null;
function showError(message) {
  const clean = typeof message === "string" ? message : message?.message || JSON.stringify(message);
  document.querySelector("#errorText").textContent = clean;
  errorPanel.hidden = false;
}
function updateCount() {
  document.querySelector("#runCount").textContent = history.querySelectorAll("[data-run-id]").length || "";
}
function addHistory(run) {
  history.querySelector(".empty-history")?.remove();
  const button = document.createElement("button"); button.className = "history-row"; button.dataset.runId = run.run_id;
  const dot = document.createElement("span"); dot.className = `run-indicator ${run.status}`;
  const goal = document.createElement("span"); goal.textContent = run.goal;
  button.append(dot, goal); history.prepend(button); updateCount();
}
function renderRun(run) {
  currentRun = run;
  document.querySelector("#runCode").textContent = `· ${run.run_id.slice(0, 8)}`;
  document.querySelector("#planSummary").textContent = run.plan.summary;
  document.querySelector("#runMeta").textContent = `${run.start_url} · Created ${new Date(run.created_at).toLocaleString()}`;
  document.querySelector("#pageTitle").textContent = run.snapshot.title || "Untitled page";
  document.querySelector("#pageLink").href = run.snapshot.url;
  document.querySelector("#beforeShot").src = run.snapshot.screenshot_url;
  document.querySelector("#pageText").textContent = run.snapshot.text;
  document.querySelector("#controlCount").textContent = `${run.snapshot.controls.length} found`;
  const controls = document.querySelector("#controls"); controls.replaceChildren();
  run.snapshot.controls.forEach((item) => {
    const row = document.createElement("div"); row.className = "control-row";
    const tag = document.createElement("b"); tag.textContent = item.tag || "element";
    const info = [item.text, item.id && `#${item.id}`, item.name && `[name=${item.name}]`, item.placeholder && `placeholder: ${item.placeholder}`].filter(Boolean).join(" · ");
    row.append(tag, document.createTextNode(` ${info || "(no label)"}`)); controls.append(row);
  });
  const steps = document.querySelector("#steps"); steps.replaceChildren();
  const approvalIds = [];
  run.plan.steps.forEach((step, index) => {
    const card = document.createElement("article"); card.className = "step-card";
    const number = document.createElement("span"); number.className = "step-number"; number.textContent = String(index + 1).padStart(2, "0");
    const main = document.createElement("div"); main.className = "step-main";
    const title = document.createElement("strong"); title.textContent = `${step.action.replace("_", " ")} · ${step.id}`;
    const rationale = document.createElement("p"); rationale.textContent = step.rationale;
    main.append(title, rationale);
    if (step.selector) { const selector = document.createElement("code"); selector.className = "step-selector"; selector.textContent = step.selector; main.append(selector); }
    if (step.action === "fill") { const value = document.createElement("code"); value.className = "step-selector"; value.textContent = `value: ${step.value}`; main.append(value); }
    const kind = document.createElement("span"); kind.className = "step-type"; kind.textContent = step.action;
    card.append(number, main, kind);
    if (step.requires_approval) {
      approvalIds.push(step.id);
      const approval = document.createElement("label"); approval.className = "approval-required";
      const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.value = step.id; checkbox.className = "approval-check";
      const label = document.createElement("span"); label.textContent = "I approve this action";
      approval.append(checkbox, label); main.append(approval);
    } else {
      const safe = document.createElement("div"); safe.className = "auto-label"; safe.textContent = "Read-only · no approval needed"; main.append(safe);
    }
    steps.append(card);
  });
  document.querySelector("#stepCounter").textContent = `${run.plan.steps.length} STEPS`;
  document.querySelector("#approvalSummary").textContent = approvalIds.length ? `${approvalIds.length} action${approvalIds.length === 1 ? "" : "s"} need your approval.` : "This plan contains only read-only actions.";
  const done = run.status === "completed" || run.status === "failed";
  document.querySelector("#executeButton").disabled = done;
  document.querySelector("#executeButton").innerHTML = done ? "Run finished ✓" : "Approve &amp; run <span>→</span>";
  const results = document.querySelector("#executionResults"); results.replaceChildren();
  if (run.execution?.length) run.execution.forEach((item) => {
    const row = document.createElement("div"); row.className = "result-row";
    row.textContent = `${item.step_id}: ${item.result}${item.url ? ` · ${item.url}` : ""}`; results.append(row);
  });
  runPanel.hidden = false;
  runPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}
async function loadRun(id) {
  const response = await fetch(`/runs/${encodeURIComponent(id)}`);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || "Could not load this run.");
  renderRun(payload);
}
form.addEventListener("submit", async (event) => {
  event.preventDefault(); errorPanel.hidden = true; runPanel.hidden = true; busy.hidden = false;
  const button = document.querySelector("#planButton"); button.disabled = true;
  try {
    const allowed = form.allowed_domains.value.split(",").map((host) => host.trim()).filter(Boolean);
    const response = await fetch("/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start_url: form.start_url.value.trim(), goal: form.goal.value.trim(), allowed_domains: allowed, max_steps: Number(form.max_steps.value) }) });
    const payload = await response.json(); if (!response.ok) throw new Error(payload.detail || "Could not create the plan.");
    renderRun(payload); addHistory(payload);
  } catch (err) { showError(err.message || "Check the URL and try again."); }
  finally { busy.hidden = true; button.disabled = false; }
});
document.querySelectorAll(".example-prompts button").forEach((button) => button.addEventListener("click", () => { form.goal.value = button.textContent; form.goal.focus(); }));
document.querySelector("#newRun").addEventListener("click", () => { document.querySelector("#intro").scrollIntoView({ behavior: "smooth" }); form.start_url.focus(); });
document.querySelector("#closeError").addEventListener("click", () => { errorPanel.hidden = true; });
document.querySelector("#executeButton").addEventListener("click", async () => {
  if (!currentRun) return;
  errorPanel.hidden = true;
  const approved = [...document.querySelectorAll(".approval-check:checked")].map((box) => box.value);
  const button = document.querySelector("#executeButton"); button.disabled = true; button.textContent = "Running…";
  try {
    const response = await fetch(`/runs/${encodeURIComponent(currentRun.run_id)}/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approved_step_ids: approved }) });
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 409 && payload.detail?.required_step_ids) throw new Error(`Approve these steps first: ${payload.detail.required_step_ids.join(", ")}`);
      throw new Error(payload.detail || "Execution failed.");
    }
    renderRun(payload);
    const indicator = history.querySelector(`[data-run-id="${CSS.escape(payload.run_id)}"] .run-indicator`);
    if (indicator) indicator.className = `run-indicator ${payload.status}`;
  } catch (err) { showError(err.message); }
  finally { button.disabled = false; if (currentRun) renderRun(currentRun); }
});
document.querySelector("#refreshRun").addEventListener("click", async () => { if (currentRun) try { await loadRun(currentRun.run_id); } catch (err) { showError(err.message); } });
history.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-run-id]"); if (!button) return;
  errorPanel.hidden = true; busy.hidden = false;
  try { await loadRun(button.dataset.runId); } catch (err) { showError(err.message); }
  finally { busy.hidden = true; }
});
updateCount();
