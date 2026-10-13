"use strict";

// The calculation functions are also exported for Node.js regression tests.
const Z95 = 1.959963984540054;

function positiveCount(value, name, allowZero = true) {
  const raw = String(value).trim();
  if (!/^(0|[1-9][0-9]*)$/.test(raw)) throw new Error(name + " must be a whole number.");
  const n = Number(raw);
  if (!Number.isSafeInteger(n) || (!allowZero && n === 0)) {
    throw new Error(name + (allowZero ? " must be a safe non-negative integer." : " must be greater than zero."));
  }
  return n;
}

function estimateCoverage(population, vaccinated, firstDose = null, finalDose = null) {
  const n = positiveCount(population, "Eligible population", false);
  const k = positiveCount(vaccinated, "Vaccinated people");
  if (k > n) throw new Error("Vaccinated people cannot exceed the eligible population.");
  const hasFirst = firstDose !== null && firstDose !== "";
  const hasFinal = finalDose !== null && finalDose !== "";
  if (hasFirst !== hasFinal) throw new Error("Enter both first-dose and final-dose counts, or leave both blank.");

  const p = k / n;
  const z2 = Z95 ** 2;
  const denom = 1 + z2 / n;
  const center = (p + z2 / (2 * n)) / denom;
  const margin = Z95 * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom;
  const round = n => Math.round((n + Number.EPSILON) * 100) / 100;
  const result = {
    population: n, vaccinated: k,
    coverage_percent: round(100 * p),
    ci_lower_percent: round(100 * Math.max(0, center - margin)),
    ci_upper_percent: round(100 * Math.min(1, center + margin)),
    dropout_percent: null
  };

  if (hasFirst) {
    const first = positiveCount(firstDose, "First dose");
    const final = positiveCount(finalDose, "Final dose");
    if (first > n || final > first) {
      throw new Error("Dose counts must satisfy final dose ≤ first dose ≤ eligible population.");
    }
    result.first_dose = first;
    result.final_dose = final;
    result.dropout_percent = first === 0 ? null : round(100 * (first - final) / first);
  }
  return result;
}

function parseCsv(text) {
  const rows = [];
  let field = "", row = [], inQuotes = false, afterQuotes = false;
  const input = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    if (inQuotes) {
      if (ch === '"') {
        if (input[i + 1] === '"') { field += '"'; i++; }
        else { inQuotes = false; afterQuotes = true; }
      } else { field += ch; }
    } else if (ch === ',') {
      row.push(field); field = ""; afterQuotes = false;
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && input[i + 1] === '\n') i++;
      row.push(field);
      if (row.some(x => x !== "")) rows.push(row);
      field = ""; row = []; afterQuotes = false;
    } else if (ch === '"') {
      if (field !== "" || afterQuotes) throw new Error("Malformed CSV quotes.");
      inQuotes = true;
    } else {
      if (afterQuotes) throw new Error("Unexpected text after a quoted CSV field.");
      field += ch;
    }
  }
  if (inQuotes) throw new Error("Unclosed quoted field in CSV.");
  row.push(field);
  if (row.some(x => x !== "")) rows.push(row);
  return rows;
}

function readCsv(text) {
  const rows = parseCsv(text);
  if (!rows.length) throw new Error("The CSV is empty.");
  const keys = rows[0].map(x => x.trim().toLowerCase());
  for (const field of ["population", "vaccinated"]) {
    if (!keys.includes(field)) throw new Error("Missing required CSV column: " + field);
  }
  if (new Set(keys).size !== keys.length) throw new Error("Duplicate CSV column headers.");
  if (rows.length > 10001) throw new Error("Maximum 10,000 data rows per file.");
  const results = [];
  const errors = [];
  for (const [idx, values] of rows.slice(1).entries()) {
    if (values.length !== keys.length) {
      errors.push("Row " + (idx + 2) + ": expected " + keys.length + " columns."); continue;
    }
    const record = Object.fromEntries(keys.map((key, i) => [key, values[i].trim()]));
    try {
      const result = estimateCoverage(record.population, record.vaccinated,
        record.first_dose || null, record.final_dose || null);
      result.group = record.group || ("Row " + (idx + 2));
      results.push(result);
    } catch (error) { errors.push("Row " + (idx + 2) + ": " + error.message); }
  }
  return {results, errors};
}

function csvSafe(value) {
  const raw = value == null ? "" : String(value);
  // Prevent formula execution when results are opened in a spreadsheet.
  const safe = /^[\s]*[=+@\-]/.test(raw) ? "'" + raw : raw;
  return '"' + safe.replace(/"/g, '""') + '"';
}

function resultCsv(rows) {
  const fields = ["group", "population", "vaccinated", "coverage_percent",
    "ci_lower_percent", "ci_upper_percent", "first_dose", "final_dose", "dropout_percent"];
  return [fields.join(","), ...rows.map(row => fields.map(key => csvSafe(row[key])).join(","))].join("\r\n") + "\r\n";
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {estimateCoverage, parseCsv, readCsv, resultCsv};
}

function init() {
  const byId = id => document.getElementById(id);
  const form = byId("coverage-form"), result = byId("result"), error = byId("form-error");
  const create = (tag, className, value) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value != null) node.textContent = value;
    return node;
  };
  const add = (parent, tag, className, value) => parent.appendChild(create(tag, className, value));
  const pct = value => value == null ? "Not defined" : value.toFixed(2) + "%";

  function display(r) {
    result.replaceChildren();
    add(result, "p", "unit", "VACCINATION COVERAGE");
    add(result, "p", "coverage-number", pct(r.coverage_percent));
    add(result, "p", "unit", r.vaccinated.toLocaleString() + " of " + r.population.toLocaleString() + " eligible people");
    const progress = add(result, "div", "progress");
    progress.setAttribute("role", "meter");
    progress.setAttribute("aria-label", "Coverage");
    progress.setAttribute("aria-valuemin", "0");
    progress.setAttribute("aria-valuemax", "100");
    progress.setAttribute("aria-valuenow", String(r.coverage_percent));
    const bar = add(progress, "div", "progress-inner");
    bar.style.width = r.coverage_percent + "%";
    const ci = add(result, "div", "ci-panel");
    add(ci, "span", "", "95% Wilson confidence interval");
    add(ci, "strong", "", pct(r.ci_lower_percent) + " – " + pct(r.ci_upper_percent));
    const drop = add(result, "div", "dropout");
    add(drop, "span", "unit", "DOSE-SERIES DROPOUT");
    add(drop, "strong", "", pct(r.dropout_percent));
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    error.hidden = true;
    try {
      display(estimateCoverage(byId("population").value, byId("vaccinated").value,
        byId("first-dose").value || null, byId("final-dose").value || null));
    } catch (err) { error.textContent = err.message; error.hidden = false; }
  });

  const upload = byId("csv-file"), button = byId("download-csv"), notice = byId("batch-message");
  const table = byId("preview-container"), body = byId("preview-body");
  let batchRows = [];
  upload.addEventListener("change", async () => {
    batchRows = []; button.disabled = true; table.hidden = true; body.replaceChildren();
    const file = upload.files && upload.files[0];
    if (!file) { notice.textContent = "No file selected."; return; }
    if (file.size > 2 * 1024 * 1024) { notice.textContent = "File exceeds 2 MB limit."; return; }
    try {
      const data = readCsv(await file.text());
      batchRows = data.results;
      button.disabled = batchRows.length === 0;
      notice.textContent = batchRows.length + " valid row(s); " + data.errors.length +
        " rejected. " + data.errors.slice(0, 3).join(" ");
      const visible = batchRows.slice(0, 10);
      for (const r of visible) {
        const tr = document.createElement("tr");
        for (const value of [r.group, r.population, r.vaccinated,
          pct(r.coverage_percent), pct(r.ci_lower_percent) + " – " + pct(r.ci_upper_percent), pct(r.dropout_percent)]) {
          add(tr, "td", "", value);
        }
        body.appendChild(tr);
      }
      byId("preview-caption").textContent = "First " + visible.length + " of " + batchRows.length + " valid rows";
      table.hidden = !visible.length;
    } catch (err) { notice.textContent = "Could not read CSV: " + err.message; }
  });

  button.addEventListener("click", () => {
    if (!batchRows.length) return;
    const url = URL.createObjectURL(new Blob([resultCsv(batchRows)], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "vaccine-coverage-results.csv";
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}

if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", init);
