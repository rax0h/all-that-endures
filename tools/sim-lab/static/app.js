"use strict";

const view = document.querySelector("#view");
const nav = document.querySelector("#nav");
const live = document.querySelector("#live");
const identity = document.querySelector("#identity");
const banner = document.querySelector("#banner");

const state = {
  module: "control",
  status: null,
  overview: null,
  benchmarks: null,
  checkpoints: [],
  samples: [],
  run: null,
  person: null,
  household: null,
  timeline: null,
  event: null,
  checkpointDetail: null,
  compare: null,
  field: "fertility",
};

window.__ATE_READY = false;

function el(tag, attrs = {}, kids = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (value === true) node.setAttribute(key, "");
    else if (value !== false && value != null) node.setAttribute(key, String(value));
  }
  for (const kid of [].concat(kids)) {
    if (kid == null || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

function svg(tag, attrs = {}, kids = []) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  for (const kid of kids) node.append(kid);
  return node;
}

function val(metric) {
  if (!metric || metric.quality === "unavailable") return null;
  return metric.value;
}

function num(value) {
  if (value == null || Number.isNaN(value)) return "—";
  if (typeof value !== "number") return String(value);
  if (Number.isInteger(value)) return value.toLocaleString("en-US");
  const abs = Math.abs(value);
  if (abs >= 100) return value.toFixed(2);
  if (abs >= 1) return value.toFixed(3);
  return value.toFixed(4);
}

function bytes(value) {
  if (value == null) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1048576) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1048576).toFixed(1)} MB`;
}

function pill(metric) {
  if (!metric) return null;
  return el("span", {class: `q ${metric.quality || ""}`, title: metric.method || ""}, [metric.quality || ""]);
}

function metric(label, metricObj, formatter = num) {
  const shown = val(metricObj);
  return el("div", {class: "metric"}, [
    el("span", {class: "k"}, [label]),
    el("span", {class: "v"}, [shown == null ? "—" : formatter(shown)]),
    pill(metricObj),
  ]);
}

function showError(error) {
  if (!error) {
    banner.hidden = true;
    banner.textContent = "";
    return;
  }
  banner.hidden = false;
  banner.textContent = error;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || response.statusText);
  showError("");
  return payload;
}

function pointsOf(metricObj) {
  const value = val(metricObj);
  return Array.isArray(value) ? value : [];
}

function lineChart(host, series, note) {
  host.replaceChildren();
  const usable = series.filter((item) => item.points && item.points.length);
  if (!usable.length) {
    host.append(el("div", {class: "empty"}, ["Unavailable. This chart is hidden because the series was not produced."]));
    if (note) note.textContent = series.map((item) => item.missing).filter(Boolean).join(" ");
    return;
  }
  const width = 720;
  const height = 210;
  const pad = {l: 48, r: 12, t: 16, b: 28};
  const xs = usable.flatMap((item) => item.points.map((point) => point.year));
  const ys = usable.flatMap((item) => item.points.map((point) => Number(point.value) || 0));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(0, ...ys);
  const maxY = Math.max(...ys, 1);
  const sx = (x) => pad.l + (maxX === minX ? 0 : (x - minX) / (maxX - minX)) * (width - pad.l - pad.r);
  const sy = (y) => pad.t + (1 - (y - minY) / (maxY - minY)) * (height - pad.t - pad.b);
  const axis = svg("path", {
    d: `M${pad.l} ${pad.t} V${height - pad.b} H${width - pad.r}`,
    fill: "none", stroke: "#3d4b58", "stroke-width": 1,
  });
  const labels = [
    svg("text", {x: pad.l, y: height - 8, fill: "#8b98a5", "font-size": 10}, [String(minX)]),
    svg("text", {x: width - pad.r - 24, y: height - 8, fill: "#8b98a5", "font-size": 10}, [String(maxX)]),
    svg("text", {x: 4, y: pad.t + 8, fill: "#8b98a5", "font-size": 10}, [num(maxY)]),
  ];
  const lines = usable.map((item) => {
    const d = item.points.map((point, index) => `${index ? "L" : "M"}${sx(point.year).toFixed(1)} ${sy(Number(point.value) || 0).toFixed(1)}`).join(" ");
    return svg("path", {d, fill: "none", stroke: item.color, "stroke-width": 1.6});
  });
  const legend = el("div", {class: "chart-note"});
  usable.forEach((item) => {
    legend.append(el("span", {style: `color:${item.color};margin-right:12px`}, [`${item.name}`]));
  });
  const readout = el("div", {class: "chart-note"}, [""]);
  const plot = svg("svg", {class: "chart", viewBox: `0 0 ${width} ${height}`}, [axis, ...lines, ...labels]);
  plot.addEventListener("mousemove", (event) => {
    const rect = plot.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    const year = Math.round(minX + ratio * (maxX - minX));
    const bits = usable.map((item) => {
      let nearest = item.points[0];
      for (const point of item.points) if (Math.abs(point.year - year) < Math.abs(nearest.year - year)) nearest = point;
      return `${item.name} y${nearest.year}: ${num(Number(nearest.value))}`;
    });
    readout.textContent = bits.join("   ");
  });
  host.append(plot, legend, readout);
  if (note) note.textContent = "";
}

function bars(host, rows, label, value, color = "") {
  host.replaceChildren();
  if (!rows || !rows.length) {
    host.append(el("div", {class: "empty"}, ["Unavailable."]));
    return;
  }
  const max = Math.max(...rows.map((row) => Number(row[value]) || 0), 1);
  const wrap = el("div", {class: "bars"});
  for (const row of rows) {
    const amount = Number(row[value]) || 0;
    wrap.append(el("div", {class: "bar-row"}, [
      el("span", {}, [String(row[label])]),
      el("div", {class: "bar-track"}, [el("div", {class: `bar-fill ${color}`, style: `width:${(100 * amount / max).toFixed(1)}%`})]),
      el("span", {class: "mono"}, [num(amount)]),
    ]));
  }
  host.append(wrap);
}

function fieldPlot(canvas, cells, settlements, field) {
  const context = canvas.getContext("2d");
  const width = canvas.clientWidth || 360;
  const height = canvas.clientHeight || 210;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  const data = val(cells) || [];
  if (!data.length) {
    context.fillStyle = "#8b98a5";
    context.font = "12px sans-serif";
    context.fillText("Cell fields are unavailable.", 12, 24);
    return;
  }
  const maxX = Math.max(...data.map((cell) => cell.x));
  const maxY = Math.max(...data.map((cell) => cell.y));
  const cw = width / (maxX + 1);
  const ch = height / (maxY + 1);
  for (const cell of data) {
    const tone = Math.max(0, Math.min(1, Number(cell[field]) || 0));
    context.fillStyle = `rgb(${Math.round(10 + tone * 90)}, ${Math.round(16 + tone * 170)}, ${Math.round(22 + tone * 140)})`;
    context.fillRect(cell.x * cw, cell.y * ch, cw + 0.6, ch + 0.6);
  }
  context.fillStyle = "#d7b56d";
  for (const settlement of settlements || []) {
    context.beginPath();
    context.arc((settlement.x + 0.5) * cw, (settlement.y + 0.5) * ch, Math.max(3, cw * 0.18), 0, Math.PI * 2);
    context.fill();
  }
}

function table(headers, records) {
  return el("table", {}, [
    el("thead", {}, [el("tr", {}, headers.map((header) => el("th", {}, [header])))]),
    el("tbody", {}, records),
  ]);
}

function passMark(metricObj) {
  if (!metricObj || metricObj.quality === "unavailable" || metricObj.value == null) {
    return el("span", {class: "q unavailable", title: metricObj && metricObj.method || "No recorded pass flag"}, ["No pass recorded"]);
  }
  if (metricObj.value === true) return el("span", {class: "q measured", title: metricObj.method}, ["Pass recorded"]);
  if (metricObj.value === false) return el("span", {class: "q bad", title: metricObj.method}, ["Fail recorded"]);
  return el("span", {class: "q unavailable"}, ["No pass recorded"]);
}

function paintTop() {
  const run = state.run || {};
  const sample = state.samples[state.samples.length - 1];
  const year = sample ? val(sample.year) : run.year;
  const population = sample ? val(sample.population) : run.population;
  const step = sample ? val(sample.step_seconds) : null;
  const rss = sample ? val(sample.rss_bytes) : null;
  live.replaceChildren(
    el("div", {class: "stat"}, [el("i", {class: `dot ${run.state || "idle"}`}), el("b", {}, [run.state || "idle"]), el("span", {}, ["state"])]),
    el("div", {class: "stat"}, [el("b", {}, [year == null ? "—" : num(year)]), el("span", {}, ["year"])]),
    el("div", {class: "stat"}, [el("b", {}, [run.seed == null ? "—" : num(run.seed)]), el("span", {}, ["seed"])]),
    el("div", {class: "stat"}, [el("b", {}, [population == null ? "—" : num(population)]), el("span", {}, ["population"])]),
    el("div", {class: "stat"}, [el("b", {}, [step == null ? "—" : num(step)]), el("span", {}, ["s/year"])]),
    el("div", {class: "stat"}, [el("b", {}, [rss == null ? "—" : bytes(rss)]), el("span", {}, ["memory"])]),
  );
  const version = state.status && state.status.version || {};
  const commit = val(version.commit_short) || "unknown";
  const branch = val(version.branch) || "unknown";
  identity.replaceChildren(
    el("span", {}, [`${branch} @ ${commit}`]),
    el("span", {}, [`lab ${version.lab_version || ""}`]),
  );
}

function paintNav() {
  nav.replaceChildren();
  const modules = (state.status && state.status.modules) || [];
  let group = "";
  for (const item of modules) {
    if (item.group !== group) {
      group = item.group;
      nav.append(el("div", {class: "nav-group"}, [group]));
    }
    nav.append(el("button", {
      class: "nav-btn",
      type: "button",
      "aria-current": item.id === state.module ? "page" : false,
      onclick: () => { location.hash = item.id; },
    }, [item.label]));
  }
}

function page(title, lede, body) {
  view.replaceChildren(el("div", {class: "page-head"}, [
    el("div", {}, [el("h1", {}, [title]), lede ? el("p", {class: "lede"}, [lede]) : null]),
  ]), body);
}

async function render() {
  window.__ATE_READY = false;
  paintNav();
  paintTop();
  try {
    if (state.module === "control") await renderControl();
    else if (state.module === "observatory") await renderObservatory();
    else if (state.module === "inspector") await renderInspector();
    else if (state.module === "timeline") await renderTimeline();
    else if (state.module === "performance") await renderPerformance();
    else if (state.module === "checkpoints") await renderCheckpoints();
    else if (state.module === "settings") await renderSettings();
    else page("Unknown module", "This module is not built.", el("div"));
    window.__ATE_READY = true;
  } catch (error) {
    showError(error.message);
    window.__ATE_READY = true;
  }
}

function formDefaults() {
  const settings = (state.status && state.status.settings) || {};
  return {
    seed: settings.default_seed ?? 843000,
    years: settings.default_years ?? 25,
    width: 24,
    height: 18,
    settlements: 5,
    timebox_seconds: settings.default_timebox_seconds ?? 60,
    pace_seconds: 0,
    instrument: false,
  };
}

async function renderControl() {
  const defaults = formDefaults();
  const form = el("form", {class: "panel", onsubmit: async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    data.instrument = event.target.instrument.checked;
    if (state.run && state.run.loaded && !confirm("Start a new world in memory? Checkpoints on disk are not modified.")) return;
    try {
      state.run = await api("/api/run/new", {method: "POST", body: data});
      state.samples = state.run.samples || [];
      paintTop();
      paintLive(liveHost, chartHost);
    } catch (error) { showError(error.message); }
  }}, [
    el("h2", {}, ["New world"]),
    el("div", {class: "form-row"}, [
      el("label", {}, ["Seed", el("input", {name: "seed", type: "number", value: defaults.seed, required: true})]),
      el("label", {}, ["Years", el("input", {name: "years", type: "number", min: 1, value: defaults.years, required: true})]),
    ]),
    el("div", {class: "form-row"}, [
      el("label", {}, ["Width", el("input", {name: "width", type: "number", min: 8, max: 36, value: defaults.width})]),
      el("label", {}, ["Height", el("input", {name: "height", type: "number", min: 8, max: 28, value: defaults.height})]),
    ]),
    el("div", {class: "form-row"}, [
      el("label", {}, ["Settlements", el("input", {name: "settlements", type: "number", min: 1, max: 8, value: defaults.settlements})]),
      el("label", {}, ["Timebox seconds", el("input", {name: "timebox_seconds", type: "number", min: 0, step: "0.1", value: defaults.timebox_seconds})]),
    ]),
    el("label", {}, ["Replay pacing seconds", el("input", {name: "pace_seconds", type: "number", min: 0, max: 2, step: "0.05", value: 0})]),
    el("label", {style: "margin-top:8px;text-transform:none;letter-spacing:0"}, [
      el("span", {}, [el("input", {name: "instrument", type: "checkbox", style: "width:auto"}), " Instrument subsystems"]),
    ]),
    el("p", {class: "note"}, ["Pacing sleeps after the measured step and does not enter the timing. Pause, stop, and the timebox all take effect on a year boundary because Simulation.step is one year. Instrumentation uses the existing ScalingTelemetry wrappers and is off unless checked."]),
    el("div", {class: "actions"}, [
      el("button", {class: "primary", type: "submit"}, ["Start"]),
      el("button", {type: "button", onclick: () => act("/api/run/pause")}, ["Pause"]),
      el("button", {type: "button", onclick: () => act("/api/run/resume")}, ["Resume"]),
      el("button", {class: "danger", type: "button", onclick: () => act("/api/run/stop")}, ["Stop"]),
      el("button", {type: "button", onclick: continueRun}, ["Continue"]),
      el("button", {type: "button", onclick: saveCheckpoint}, ["Save new checkpoint"]),
    ]),
  ]);
  const liveHost = el("div", {id: "live-readout"});
  const chartHost = el("div", {id: "live-chart"});
  const right = el("div", {class: "panel"}, [el("h2", {}, ["This run"]), liveHost, chartHost]);
  page("Simulation control", "Runs call generate_world and Simulation.step in this install. The year cap refuses multi-thousand-year jobs. Nothing is written unless you save a new checkpoint into the laboratory folder.", el("div", {class: "grid-2"}, [form, right]));
  paintLive(liveHost, chartHost);
  state.liveHost = liveHost;
  state.chartHost = chartHost;
}

function paintLive(host, chartHost) {
  if (!host) return;
  const run = state.run || {};
  const sample = state.samples[state.samples.length - 1];
  const steps = state.samples.map((item) => val(item.step_seconds)).filter((item) => item != null);
  const mean = steps.length ? steps.reduce((sum, item) => sum + item, 0) / steps.length : null;
  host.replaceChildren(el("div", {class: "metrics"}, [
    metric("Year", sample && sample.year),
    metric("Step seconds", sample && sample.step_seconds),
    metric("Mean s/year", mean == null ? {quality: "unavailable", value: null, method: "no completed years in this session"} : {quality: "calculated", value: mean, method: "mean of measured step seconds in this session, pacing excluded"}),
    metric("Population", sample && sample.population),
    metric("Living households", sample && sample.living_households),
    metric("Events", sample && sample.events),
    metric("Memory", sample && sample.rss_bytes, bytes),
  ]), el("p", {class: "note"}, [run.reason || ""]));
  if (run.error) host.append(el("p", {class: "note"}, [run.error]));
  if (chartHost) {
    const stepPoints = state.samples.map((item) => ({year: val(item.year), value: val(item.step_seconds)})).filter((point) => point.year != null && point.value != null);
    const popPoints = state.samples.map((item) => ({year: val(item.year), value: val(item.population)})).filter((point) => point.year != null && point.value != null);
    chartHost.replaceChildren(el("h2", {}, ["Step seconds"]), el("div"), el("h2", {}, ["Population"]), el("div"));
    const [stepHost, popHost] = chartHost.querySelectorAll("div");
    lineChart(stepHost, [{name: "Step seconds", color: "#7eddd2", points: stepPoints, missing: "No year has finished in this run."}]);
    lineChart(popHost, [{name: "Population", color: "#d7b56d", points: popPoints}]);
  }
}

async function act(path) {
  try {
    state.run = await api(path, {method: "POST", body: {}});
    state.samples = state.run.samples || state.samples;
    paintTop();
    paintLive(state.liveHost, state.chartHost);
  } catch (error) { showError(error.message); }
}

async function continueRun() {
  const years = Number(document.querySelector('input[name="years"]').value || 1);
  const pace = Number(document.querySelector('input[name="pace_seconds"]').value || 0);
  const timebox = Number(document.querySelector('input[name="timebox_seconds"]').value || 0);
  const instrument = document.querySelector('input[name="instrument"]').checked;
  try {
    state.run = await api("/api/run/continue", {method: "POST", body: {years, pace_seconds: pace, timebox_seconds: timebox, instrument}});
    state.samples = state.run.samples || [];
    paintTop();
  } catch (error) { showError(error.message); }
}

async function saveCheckpoint() {
  const seed = state.run && state.run.seed != null ? state.run.seed : "world";
  const year = state.run && state.run.year != null ? state.run.year : "x";
  const filename = `lab-s${seed}-y${year}-${Date.now()}.checkpoint`;
  try {
    const saved = await api("/api/checkpoints/save", {method: "POST", body: {filename}});
    showError("");
    banner.hidden = false;
    banner.textContent = `Saved a new checkpoint at ${saved.path}. Existing checkpoints were not modified.`;
  } catch (error) { showError(error.message); }
}

async function renderObservatory() {
  state.overview = await api("/api/overview");
  if (!state.benchmarks) state.benchmarks = await api("/api/benchmarks");
  const world = state.overview;
  const loaded = el("div", {class: "stack"});
  if (!world.loaded) {
    loaded.append(el("div", {class: "panel"}, [
      el("h2", {}, ["Loaded world"]),
      el("p", {class: "empty"}, ["No world is loaded. Start a bounded run or open a checkpoint. Charts of a loaded world are omitted rather than filled with placeholders."]),
    ]));
  } else {
    const popChart = el("div");
    const flowChart = el("div");
    const note = el("div", {class: "chart-note"});
    const canvas = el("canvas", {class: "field", width: 360, height: 210});
    const fieldSelect = el("select", {class: "compact", onchange: (event) => {
      state.field = event.target.value;
      fieldPlot(canvas, world.cells, world.settlements, state.field);
    }}, ["fertility", "elevation", "moisture", "forest", "hazard"].map((name) => el("option", {value: name, selected: name === state.field}, [name])));
    loaded.append(el("div", {class: "panel"}, [
      el("div", {class: "metrics"}, [
        metric("Year", world.year), metric("Seed", world.seed), metric("Population", world.population),
        metric("People ever", world.people_total), metric("Living households", world.living_households),
        metric("Events", world.events), metric("Essence users", world.essence_users_living),
      ]),
      el("p", {class: "note"}, [world.lifespan_note || ""]),
    ]));
    loaded.append(el("div", {class: "grid-charts"}, [
      el("div", {class: "panel"}, [el("h2", {}, ["Population"]), popChart, el("h2", {}, ["Births and deaths"]), flowChart, note]),
      el("div", {class: "panel"}, [
        el("h2", {}, ["Cell field"]),
        el("p", {class: "note"}, ["Measured stored cell values, rounded for transport. Amber marks are settlement coordinates. This is not a rendered map, and historical settlement population is not retained."]),
        fieldSelect, canvas,
        pill(world.cells), pill(world.historical_settlement_population),
      ]),
    ]));
    const speciesHost = el("div");
    const rankHost = el("div");
    const ageHost = el("div");
    loaded.append(el("div", {class: "grid-3"}, [
      el("div", {class: "panel"}, [el("h2", {}, ["Species"]), speciesHost, pill(world.species)]),
      el("div", {class: "panel"}, [el("h2", {}, ["Advancement rank"]), rankHost, pill(world.advancement_ranks), el("p", {class: "note"}, [`Living without an essence path: ${num(val(world.living_without_essence_path))}`])]),
      el("div", {class: "panel"}, [el("h2", {}, ["Age"]), ageHost, pill(world.age && world.age.histogram)]),
    ]));
    const settlements = el("div", {class: "scroll"});
    const economy = el("div");
    loaded.append(el("div", {class: "grid-2"}, [
      el("div", {class: "panel"}, [el("h2", {}, ["Settlements now"]), settlements]),
      el("div", {class: "panel"}, [el("h2", {}, ["Stocks"]), economy, el("h2", {style: "margin-top:12px"}, ["Death causes"]), deathTable(world)]),
    ]));
    lineChart(popChart, [
      {name: "Population", color: "#d7b56d", points: pointsOf(world.series && world.series.population), missing: world.series && world.series.population && world.series.population.quality === "unavailable" ? world.series.population.method : ""},
    ], note);
    lineChart(flowChart, [
      {name: "Births", color: "#7eddd2", points: pointsOf(world.series && world.series.births)},
      {name: "Deaths", color: "#e08b8b", points: pointsOf(world.series && world.series.deaths)},
    ]);
    bars(speciesHost, val(world.species) || [], "species", "count");
    bars(rankHost, val(world.advancement_ranks) || [], "name", "count", "alt");
    bars(ageHost, val(world.age && world.age.histogram) || [], "label", "count", "amber");
    settlements.append(table(["Id", "Living", "Food", "Defense", "Prosperity"], (world.settlements || []).map((item) => el("tr", {}, [
      el("td", {class: "mono"}, [String(item.id)]),
      el("td", {class: "mono"}, [num(val(item.living))]),
      el("td", {class: "mono"}, [num(val(item.food_stock))]),
      el("td", {class: "mono"}, [num(val(item.defense))]),
      el("td", {class: "mono"}, [num(val(item.prosperity))]),
    ]))));
    const stocks = world.economy || {};
    economy.append(el("div", {class: "metrics"}, Object.entries(stocks).map(([key, item]) => metric(
      key.replaceAll("_", " "),
      item,
      (value) => typeof value === "object" ? JSON.stringify(value) : num(value),
    ))));
    requestAnimationFrame(() => fieldPlot(canvas, world.cells, world.settlements, state.field));
  }
  loaded.append(millenniumPanel());
  page("Civilization observatory", "Every figure is measured from the loaded world or calculated from its event ledger and checked. Recorded benchmark snapshots stay in their own panel.", loaded);
}

function deathTable(world) {
  const rows = val(world.death_causes) || [];
  if (!rows.length) return el("p", {class: "empty"}, ["No death events."]);
  return table(["Cause", "Deaths"], rows.map((row) => el("tr", {}, [
    el("td", {}, [row.cause]), el("td", {class: "mono"}, [num(row.count)]),
  ])));
}

function millenniumPanel() {
  const source = (state.benchmarks && state.benchmarks.sources || []).find((item) => item.kind === "millennium-pass");
  const panel = el("div", {class: "panel"}, [el("h2", {}, ["Recorded millennium snapshot"])]);
  if (!source) {
    panel.append(el("p", {class: "empty"}, ["millennium-pass.json was not found in a watched benchmark folder."]));
    return panel;
  }
  panel.append(el("p", {class: "note"}, ["These numbers are copied from the benchmark file. The laboratory did not re-run the 1,000 years."]));
  if (source.note) panel.append(el("pre", {class: "note"}, [source.note]));
  const accepted = (source.runs || []).find((run) => String(run.title).includes("accepted")) || (source.runs || [])[0];
  if (accepted && accepted.snapshot && accepted.snapshot.available) {
    const fields = accepted.snapshot.fields || {};
    panel.append(el("div", {class: "metrics"}, [
      metric("Alive", fields.alive), metric("People", fields.people_total), metric("Events", fields.events_total),
      metric("Households living", fields.living_households),
    ]));
    const species = val(fields.species_population);
    const host = el("div");
    if (species) {
      bars(host, Object.entries(species).map(([name, count]) => ({name, count})), "name", "count");
      panel.append(el("h2", {}, ["Recorded species at the snapshot year"]), host, pill(fields.species_population));
    }
    const buckets = el("div");
    lineChart(buckets, (source.runs || []).map((run, index) => ({
      name: `${run.title} living`,
      color: index ? "#7eddd2" : "#8eafc9",
      points: (run.buckets || []).map((bucket) => ({year: bucket.last_year, value: val(bucket.living)})).filter((point) => point.value != null),
    })));
    panel.append(el("h2", {}, ["Living population at recorded bucket ends"]), el("p", {class: "note"}, ["Not an annual series. Only the bucket boundaries stored in the file."]), buckets);
  }
  return panel;
}

async function renderInspector() {
  if (!state.overview || !state.overview.loaded) state.overview = await api("/api/overview");
  const species = (val(state.overview.species) || []).map((row) => row.species);
  const filters = el("form", {class: "actions", onsubmit: async (event) => {
    event.preventDefault();
    await loadPeople(new FormData(event.target));
  }}, [
    el("input", {name: "q", placeholder: "id, species, or occupation", style: "width:200px"}),
    el("select", {name: "alive"}, [el("option", {value: ""}, ["alive or dead"]), el("option", {value: "yes"}, ["alive"]), el("option", {value: "no"}, ["dead"])]),
    el("select", {name: "species"}, [el("option", {value: ""}, ["any species"]), ...species.map((name) => el("option", {value: name}, [name]))]),
    el("select", {name: "essence"}, [el("option", {value: ""}, ["any path"]), el("option", {value: "yes"}, ["essence user"]), el("option", {value: "no"}, ["no path"])]),
    el("button", {class: "primary", type: "submit"}, ["Search"]),
  ]);
  const list = el("div", {class: "scroll", id: "people-list"});
  const detail = el("div", {class: "detail", id: "person-detail"}, [el("p", {class: "empty"}, [state.overview.loaded ? "Select a person. People have no stored personal names." : "No world is loaded."])]);
  const split = el("div", {class: "split"}, [el("div", {}, [filters, list]), el("div", {class: "split-handle", onpointerdown: startSplit}), detail]);
  page("Individual and household inspector", "Search uses the in-memory index. Opening a person does not call social.get or currency.wallet, which would create records.", split);
  state.peopleList = list;
  state.personDetail = detail;
  if (state.overview.loaded) await loadPeople(new FormData());
  const handle = split.querySelector(".split-handle");
  function startSplit(event) {
    event.preventDefault();
    const move = (ev) => {
      const rect = split.getBoundingClientRect();
      const ratio = Math.min(0.7, Math.max(0.25, (ev.clientX - rect.left) / rect.width));
      split.style.setProperty("--split", `${(ratio * 100).toFixed(1)}%`);
    };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }
  handle.onpointerdown = startSplit;
}

async function loadPeople(form) {
  const params = new URLSearchParams();
  for (const [key, value] of form.entries()) if (value) params.set(key, value);
  const payload = await api(`/api/people?${params.toString()}`);
  state.peopleList.replaceChildren(el("p", {class: "note"}, [`${payload.total} people`]), table(
    ["Id", "Age", "Alive", "Species", "Occupation", "Settlement", "Rank"],
    payload.people.map((person) => el("tr", {class: "row-select", tabindex: "0", onclick: () => openPerson(person.id), onkeydown: (event) => {
      if (event.key === "Enter") openPerson(person.id);
    }}, [
      el("td", {class: "mono"}, [String(person.id)]),
      el("td", {class: "mono"}, [num(person.age)]),
      el("td", {}, [person.alive ? "yes" : "no"]),
      el("td", {}, [person.species]),
      el("td", {}, [person.occupation]),
      el("td", {class: "mono"}, [String(person.settlement)]),
      el("td", {}, [person.advancement_rank_name || "—"]),
    ])),
  ));
}

async function openPerson(id) {
  const person = await api(`/api/people/${id}`);
  if (person.error) { state.personDetail.textContent = person.error; return; }
  const host = state.personDetail;
  host.replaceChildren(el("h2", {}, [`Person ${person.id}`]), pill(person.name));
  const identity = person.identity || {};
  host.append(kvBlock([
    ["Born", identity.born], ["Age", identity.age], ["Lifespan", identity.lifespan], ["Alive", identity.alive],
    ["Species", identity.species], ["Occupation", identity.occupation], ["Settlement", identity.settlement],
    ["Household", identity.household], ["Stored rank", identity.stored_rank], ["Health", identity.health], ["Wealth", identity.wealth],
  ]));
  host.append(el("h3", {}, ["Dispositions and emotions"]));
  host.append(kvBlock(Object.entries(val(person.dispositions) || {}).map(([key, value]) => [key, {quality: "measured", value, method: person.dispositions.method}])));
  host.append(kvBlock(Object.entries(val(person.emotions) || {}).map(([key, value]) => [key, {quality: "measured", value, method: person.emotions.method}])));
  host.append(el("h3", {}, ["Capabilities"]));
  host.append(el("p", {class: "note"}, ["Unmodeled capabilities stay unavailable. They are not shown as zero."]));
  const family = person.family || {};
  host.append(el("h3", {}, ["Family"]));
  host.append(el("p", {class: "mono note"}, [
    `Children ${JSON.stringify(val(family.children) || [])}`,
  ]));
  host.append(el("p", {class: "note"}, [`Descendants capped: ${(val(family.descendants) || []).join(", ") || "—"}${family.descendants_truncated ? " (truncated)" : ""}`]));
  const essence = person.essence;
  host.append(el("h3", {}, ["Essence path"]));
  if (!essence || essence.quality === "unavailable") host.append(el("p", {class: "empty"}, [essence ? essence.method : "Unavailable."]));
  else {
    const path = essence.value;
    host.append(el("p", {class: "note"}, [`Essences ${path.base_essences.join(", ") || "—"}; confluence ${path.confluence_name || "—"}`]), pill(essence));
    host.append(table(["Ability", "Essence", "Rank", "Level", "Awakened"], (path.abilities || []).map((ability) => el("tr", {}, [
      el("td", {}, [ability.name]), el("td", {}, [ability.essence]), el("td", {class: "mono"}, [String(ability.rank)]),
      el("td", {class: "mono"}, [String(ability.level)]), el("td", {class: "mono"}, [String(ability.awakened_year)]),
    ]))));
  }
  host.append(el("h3", {}, ["Skills"]));
  if (!person.skills.length) host.append(el("p", {class: "empty"}, ["No skill records."]));
  else host.append(table(["Domain", "Level", "Practice", "Teachers"], person.skills.map((skill) => el("tr", {}, [
    el("td", {}, [skill.domain]), el("td", {class: "mono"}, [num(val(skill.level))]),
    el("td", {class: "mono"}, [num(val(skill.practice))]), el("td", {class: "mono"}, [skill.teachers.join(", ") || "—"]),
  ]))));
  const relationships = val(person.relationships) || [];
  host.append(el("h3", {}, ["Relationships"]), pill(person.relationships));
  host.append(table(["Person", "Trust", "Attachment", "Familiarity"], relationships.slice(0, 40).map((item) => el("tr", {class: "row-select", onclick: () => openPerson(item.person)}, [
    el("td", {class: "mono"}, [String(item.person)]), el("td", {class: "mono"}, [num(item.trust)]),
    el("td", {class: "mono"}, [num(item.attachment)]), el("td", {class: "mono"}, [num(item.familiarity)]),
  ]))));
  if (relationships.length > 40) host.append(el("p", {class: "note"}, [`Showing 40 of ${relationships.length}.`]));
  host.append(el("h3", {}, ["Household"]), el("button", {type: "button", onclick: () => openHousehold(val(identity.household))}, ["Open household"]));
  host.append(el("h3", {}, ["Indexed events"]));
  host.append(el("p", {class: "note"}, [`${person.events_indexed} indexed${person.events_truncated ? "; showing the latest 120" : ""}.`]));
  host.append(eventTable(person.events || []));
}

function kvBlock(pairs) {
  const wrap = el("div", {class: "kv"});
  for (const [key, item] of pairs) {
    wrap.append(el("div", {class: "k"}, [key]), el("div", {}, [item && typeof item === "object" && "quality" in item ? `${item.quality === "unavailable" ? "—" : num(item.value)} ` : String(item), item && item.quality ? pill(item) : null]));
  }
  return wrap;
}

async function openHousehold(id) {
  if (id == null) return;
  const household = await api(`/api/households/${id}`);
  const host = state.personDetail;
  host.replaceChildren(el("h2", {}, [`Household ${household.id}`]));
  host.append(kvBlock([
    ["Settlement", household.settlement], ["Alive", household.alive], ["Lineage", household.lineage],
    ["Wealth", household.wealth], ["Food", household.food], ["Preparedness", household.preparedness],
  ]));
  const members = val(household.members) || [];
  host.append(table(["Id", "Alive", "Age", "Species", "Occupation"], members.map((member) => el("tr", {class: "row-select", onclick: () => member.record ? null : openPerson(member.id)}, [
    el("td", {class: "mono"}, [String(member.id)]),
    el("td", {}, [member.record ? "missing" : member.alive ? "yes" : "no"]),
    el("td", {class: "mono"}, [member.age == null ? "—" : num(member.age)]),
    el("td", {}, [member.species || "—"]),
    el("td", {}, [member.occupation || "—"]),
  ]))));
}

function eventTable(events) {
  return table(["Year", "Kind", "Layer", "Actors"], events.map((event) => el("tr", {class: "row-select", onclick: () => openEvent(event.id)}, [
    el("td", {class: "mono"}, [String(event.year)]),
    el("td", {}, [event.kind]),
    el("td", {}, [event.layer]),
    el("td", {class: "mono"}, [event.actors.map((actor) => `${actor.kind}:${actor.id}`).join(" ")]),
  ])));
}

async function openEvent(id) {
  const payload = await api(`/api/event/${id}`);
  const host = el("div", {class: "panel"});
  if (payload.error) { host.append(el("p", {}, [payload.error])); }
  else {
    host.append(el("h2", {}, [`Event ${id}`]), el("pre", {class: "note mono"}, [JSON.stringify(val(payload.event), null, 2)]));
    host.append(el("h2", {}, ["Causal ancestors"]), pill(payload.causal_ancestors));
    if (payload.causal_truncated) host.append(el("p", {class: "note"}, ["Chain truncated at 40."]));
    host.append(eventTable(val(payload.causal_ancestors) || []));
  }
  view.append(host);
}

async function renderTimeline() {
  if (!state.overview || !state.overview.loaded) state.overview = await api("/api/overview");
  if (!state.overview.loaded) {
    page("Historical timeline", "The timeline reads events_between for one year.", el("div", {class: "panel"}, [el("p", {class: "empty"}, ["No world is loaded."])]));
    return;
  }
  const year = val(state.overview.year) || 0;
  const kinds = (val(state.overview.event_kinds) || []).map((row) => row.kind);
  const list = el("div", {class: "scroll"});
  const form = el("form", {class: "actions", onsubmit: async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target).entries());
    const params = new URLSearchParams(data);
    state.timeline = await api(`/api/timeline?${params.toString()}`);
    paintTimeline(list);
  }}, [
    el("label", {}, ["Year", el("input", {name: "year", type: "number", value: year, style: "width:100px"})]),
    el("label", {}, ["Kind", el("select", {name: "kind"}, [
      el("option", {value: ""}, ["any"]),
      ...kinds.map((kind) => el("option", {value: kind}, [kind])),
    ])]),
    el("label", {}, ["Layer", el("select", {name: "layer"}, ["", "reality", "society", "knowledge", "narrative"].map((name) => el("option", {value: name}, [name || "any"])))]),
    el("button", {class: "primary", type: "submit"}, ["Show year"]),
  ]);
  page("Historical timeline", "One year at a time, from the event archive. Filters do not infer events that were not recorded.", el("div", {class: "stack"}, [el("div", {class: "panel"}, [form, list])]));
  state.timelineHost = list;
  state.timeline = await api(`/api/timeline?year=${year}`);
  paintTimeline(list);
}

function paintTimeline(host) {
  const payload = state.timeline;
  if (!payload) return;
  host.replaceChildren(
    el("p", {class: "note"}, [`${payload.count} events in year ${payload.year}. ${payload.coverage}`]),
    pill(payload.events),
    eventTable(val(payload.events) || []),
  );
}

async function renderPerformance() {
  state.benchmarks = await api("/api/benchmarks");
  if (!state.run) state.run = await api("/api/run");
  state.samples = state.run.samples || [];
  const gate = state.benchmarks.gate;
  const gatePanel = el("div", {class: "panel"}, [
    el("h2", {}, ["Documented threshold"]),
    gate && gate.quality === "documented"
      ? el("p", {}, [`${gate.value} seconds of simulation time. `, pill(gate)])
      : el("p", {class: "empty"}, ["Threshold unavailable."]),
    el("p", {class: "note"}, [gate && gate.method || ""]),
    el("p", {class: "note"}, ["A pass badge appears only when the file itself records performance_passed true. Short laboratory runs are not that benchmark."]),
  ]);
  const runs = [];
  for (const source of state.benchmarks.sources || []) {
    for (const item of source.runs || []) runs.push({source, item});
  }
  const rows = runs.map(({source, item}) => el("tr", {}, [
    el("td", {}, [item.title || item.id]),
    el("td", {class: "mono"}, [num(val(item.metrics.simulation_seconds))]),
    el("td", {class: "mono"}, [num(val(item.metrics.digest_seconds))]),
    el("td", {class: "mono"}, [num(val(item.metrics.validation_seconds))]),
    el("td", {}, [passMark(item.metrics.performance_passed)]),
    el("td", {}, [item.metrics.gate_comparison ? pill(item.metrics.gate_comparison) : null, item.metrics.gate_comparison && item.metrics.gate_comparison.value === true ? " under threshold" : item.metrics.gate_comparison && item.metrics.gate_comparison.value === false ? " over threshold" : ""]),
    el("td", {class: "mono"}, [source.path.split(/[\\/]/).pop()]),
  ]));
  const chart = el("div");
  lineChart(chart, runs.filter(({item}) => item.buckets && item.buckets.length).map(({item}, index) => ({
    name: item.title,
    color: ["#8eafc9", "#7eddd2", "#d7b56d", "#e08b8b"][index % 4],
    points: item.buckets.map((bucket) => ({year: bucket.last_year, value: val(bucket.seconds_per_year)})).filter((point) => point.value != null),
  })));
  const subsystem = el("div");
  const accepted = runs.find(({item}) => String(item.title).includes("accepted"));
  const lastBucket = accepted && accepted.item.buckets && accepted.item.buckets[accepted.item.buckets.length - 1];
  if (lastBucket && val(lastBucket.subsystem_seconds)) {
    const entries = Object.entries(val(lastBucket.subsystem_seconds)).sort((a, b) => b[1] - a[1]).slice(0, 12);
    bars(subsystem, entries.map(([name, seconds]) => ({name, seconds})), "name", "seconds", "alt");
  } else subsystem.append(el("p", {class: "empty"}, ["No subsystem seconds are stored on the latest accepted bucket."]));
  const session = el("div");
  lineChart(session, [{
    name: "This session step seconds",
    color: "#7eddd2",
    points: state.samples.map((item) => ({year: val(item.year), value: val(item.step_seconds)})).filter((point) => point.value != null),
    missing: "No year has been stepped in this session.",
  }]);
  const tools = el("div", {class: "panel"}, [
    el("h2", {}, ["Measure this world"]),
    el("p", {class: "note"}, ["Digest and checkpoint save are explicit. They are not run in the background."]),
    el("div", {class: "actions"}, [
      el("button", {type: "button", onclick: async () => {
        try {
          const result = await api("/api/digest", {method: "POST", body: {}});
          tools.append(el("p", {class: "mono"}, [`${val(result.digest)} in ${num(val(result.digest_seconds))} s`]), pill(result.digest));
        } catch (error) { showError(error.message); }
      }}, ["Time canonical digest"]),
    ]),
  ]);
  page("Performance laboratory", "Historical bars come from files already in the repository or from logs this laboratory wrote. Nothing here is a fresh 1,000-year run.", el("div", {class: "stack"}, [
    gatePanel,
    el("div", {class: "panel"}, [el("h2", {}, ["Recorded runs"]), el("div", {class: "scroll"}, [table(["Run", "Simulation s", "Digest s", "Validation s", "Recorded result", "Threshold check", "File"], rows)])]),
    el("div", {class: "grid-2"}, [
      el("div", {class: "panel"}, [el("h2", {}, ["Seconds per year by bucket"]), chart]),
      el("div", {class: "panel"}, [el("h2", {}, ["Accepted-run subsystem seconds, last bucket"]), subsystem]),
    ]),
    el("div", {class: "panel"}, [el("h2", {}, ["This session"]), session]),
    tools,
  ]));
}

async function renderCheckpoints() {
  const payload = await api("/api/checkpoints");
  state.checkpoints = payload.checkpoints || [];
  const detail = el("div", {class: "panel"}, [el("p", {class: "empty"}, ["Select a checkpoint. Metadata is read when you ask; integrity is a separate verification."])]);
  const body = el("tbody");
  for (const row of state.checkpoints) {
    const header = row.header || {};
    body.append(el("tr", {class: "row-select", onclick: () => selectCheckpoint(row, detail)}, [
      el("td", {}, [row.name]),
      el("td", {class: "mono"}, [bytes(row.bytes)]),
      el("td", {class: "mono"}, [header.year ? num(val(header.year)) : "not read"]),
      el("td", {class: "mono"}, [header.seed ? num(val(header.seed)) : "—"]),
      el("td", {}, [header.integrity ? pill(header.integrity) : el("span", {class: "q unavailable"}, ["not verified"])]),
    ]));
  }
  const tableEl = el("table", {}, [
    el("thead", {}, [el("tr", {}, ["File", "Size", "Year", "Seed", "Integrity"].map((name) => el("th", {}, [name])))]),
    body,
  ]);
  const compare = el("div", {class: "actions"}, [
    el("select", {id: "cmp-a"}, state.checkpoints.map((row) => el("option", {value: row.path}, [row.name]))),
    el("select", {id: "cmp-b"}, state.checkpoints.map((row) => el("option", {value: row.path}, [row.name]))),
    el("button", {type: "button", onclick: async () => {
      try {
        state.compare = await api("/api/checkpoints/compare", {method: "POST", body: {left: document.querySelector("#cmp-a").value, right: document.querySelector("#cmp-b").value}});
        detail.replaceChildren(el("h2", {}, ["Comparison"]), el("p", {class: "note"}, [state.compare.note]), compareTable(state.compare.rows));
      } catch (error) { showError(error.message); }
    }}, ["Compare stored headers"]),
  ]);
  page("Checkpoint explorer", "Read-only. Verify uses the official loader and does not rewrite the file. Save, on the control page, can only create a new file in the laboratory folder.", el("div", {class: "stack"}, [
    el("div", {class: "panel"}, [el("div", {class: "scroll"}, [tableEl]), compare]),
    detail,
  ]));
  state.checkpointDetail = detail;
}

function compareTable(rows) {
  return table(["Field", "Left", "Right", "Equal"], (rows || []).map((row) => el("tr", {}, [
    el("td", {}, [row.field]),
    el("td", {class: "mono"}, [fmtMetric(row.left)]),
    el("td", {class: "mono"}, [fmtMetric(row.right)]),
    el("td", {}, [row.equal == null ? "—" : row.equal ? "yes" : "no"]),
  ])));
}

function fmtMetric(metricObj) {
  if (!metricObj) return "—";
  if (metricObj.quality === "unavailable") return "unavailable";
  const value = metricObj.value;
  if (typeof value === "number") return num(value);
  if (value == null) return "—";
  return String(value);
}

async function selectCheckpoint(row, detail) {
  let header = row.header;
  if (!header) {
    try { header = await api("/api/checkpoints/read", {method: "POST", body: {path: row.path}}); }
    catch (error) { showError(error.message); return; }
  }
  detail.replaceChildren(
    el("h2", {}, [row.name]),
    el("p", {class: "mono note"}, [row.path]),
    el("div", {class: "metrics"}, [
      metric("Year", header.year), metric("Seed", header.seed), metric("People", header.people), metric("Living", header.living),
      metric("File bytes", {quality: "measured", value: row.bytes, method: "stat size"}, bytes),
    ]),
    el("p", {class: "note"}, [`Stored digest ${fmtMetric(header.digest_stored)}`]),
    el("p", {class: "note"}, [header.integrity && header.integrity.method ? header.integrity.method : "Integrity has not been checked."]),
    pill(header.integrity),
    header.error ? el("p", {class: "note"}, [header.error]) : null,
    el("div", {class: "actions"}, [
      el("button", {type: "button", onclick: () => verifyCheckpoint(row.path, detail)}, ["Verify integrity"]),
      el("button", {class: "primary", type: "button", onclick: () => loadCheckpoint(row.path)}, ["Open in laboratory"]),
    ]),
  );
}

async function verifyCheckpoint(path, detail) {
  try {
    const result = await api("/api/checkpoints/verify", {method: "POST", body: {path}});
    detail.append(el("p", {}, [result.ok ? "Official load completed and the integrity check passed." : `Verification failed: ${result.error}`]));
    detail.append(el("p", {}, [pill(result.verify_seconds), " ", pill(result.mtime_unchanged), result.mtime_unchanged ? " mtime unchanged" : ""]));
  } catch (error) { showError(error.message); }
}

async function loadCheckpoint(path) {
  if (state.run && state.run.loaded && !confirm("Replace the world in memory? The checkpoint file stays untouched.")) return;
  try {
    await api("/api/checkpoints/load", {method: "POST", body: {path}});
    state.overview = null;
    state.run = await api("/api/run");
    location.hash = "observatory";
  } catch (error) { showError(error.message); }
}

async function renderSettings() {
  const payload = await api("/api/settings");
  const settings = payload.settings;
  const version = payload.version;
  const form = el("form", {class: "panel", onsubmit: async (event) => {
    event.preventDefault();
    const data = new FormData(event.target);
    try {
      await api("/api/settings", {method: "POST", body: {
        update_on_launch: data.get("update_on_launch") === "on",
        data_root: data.get("data_root") || "",
        year_cap: Number(data.get("year_cap")),
        default_years: Number(data.get("default_years")),
        default_seed: Number(data.get("default_seed")),
        default_timebox_seconds: Number(data.get("default_timebox_seconds")),
        extra_checkpoint_dirs: splitLines(data.get("extra_checkpoint_dirs")),
        extra_output_dirs: splitLines(data.get("extra_output_dirs")),
        extra_benchmark_dirs: splitLines(data.get("extra_benchmark_dirs")),
      }});
      state.status = await api("/api/status");
      state.benchmarks = null;
      banner.hidden = false;
      banner.textContent = "Settings saved on this computer, outside the git checkout.";
    } catch (error) { showError(error.message); }
  }}, [
    el("h2", {}, ["This install"]),
    el("div", {class: "kv"}, [
      el("div", {class: "k"}, ["Commit"]), el("div", {class: "mono"}, [fmtMetric(version.commit)]),
      el("div", {class: "k"}, ["Branch"]), el("div", {class: "mono"}, [fmtMetric(version.branch)]),
      el("div", {class: "k"}, ["Dirty"]), el("div", {}, [String(val(version.dirty))]),
      el("div", {class: "k"}, ["Engine"]), el("div", {class: "mono"}, [version.engine_root || ""]),
    ]),
    el("p", {class: "note"}, [version.engine_note || ""]),
    el("label", {style: "margin-top:10px;text-transform:none"}, [
      el("span", {}, [el("input", {name: "update_on_launch", type: "checkbox", checked: settings.update_on_launch, style: "width:auto"}), " Check this install's branch on launch and fast-forward when that is clean"]),
    ]),
    el("label", {}, ["Read-only data root", el("input", {name: "data_root", value: settings.data_root || "", placeholder: "C:\\Users\\Owner\\Projects\\all-that-endures"})]),
    el("p", {class: "note"}, ["The data root is only scanned for existing checkpoint, output, and benchmark folders. It is not imported and nothing is written there."]),
    el("div", {class: "form-row"}, [
      el("label", {}, ["Year cap", el("input", {name: "year_cap", type: "number", min: 1, max: 250, value: settings.year_cap})]),
      el("label", {}, ["Default years", el("input", {name: "default_years", type: "number", min: 1, value: settings.default_years})]),
    ]),
    el("div", {class: "form-row"}, [
      el("label", {}, ["Default seed", el("input", {name: "default_seed", type: "number", value: settings.default_seed})]),
      el("label", {}, ["Default timebox", el("input", {name: "default_timebox_seconds", type: "number", min: 0, value: settings.default_timebox_seconds})]),
    ]),
    el("label", {}, ["Extra checkpoint folders", el("textarea", {name: "extra_checkpoint_dirs"}, [(settings.extra_checkpoint_dirs || []).join("\n")])]),
    el("label", {}, ["Extra output folders", el("textarea", {name: "extra_output_dirs"}, [(settings.extra_output_dirs || []).join("\n")])]),
    el("label", {}, ["Extra benchmark folders", el("textarea", {name: "extra_benchmark_dirs"}, [(settings.extra_benchmark_dirs || []).join("\n")])]),
    el("div", {class: "actions"}, [
      el("button", {class: "primary", type: "submit"}, ["Save settings"]),
      el("button", {type: "button", onclick: checkUpdates}, ["Check for updates"]),
    ]),
    el("div", {id: "update-result", class: "note"}),
  ]);
  const future = el("div", {class: "panel"}, [el("h2", {}, ["Not built"])]);
  for (const item of (state.status && state.status.future) || payload.future || []) {
    future.append(el("p", {}, [el("strong", {}, [item.label]), " — not built. ", item.note]));
  }
  const folders = payload.folders || {};
  const watch = el("div", {class: "panel"}, [
    el("h2", {}, ["Watched folders"]),
    el("p", {class: "note"}, ["Directory watches are not recursive. A new file in one of these folders is indexed from that event."]),
    el("pre", {class: "note mono"}, [JSON.stringify({
      checkpoints: folders.checkpoints, outputs: folders.outputs, benchmarks: folders.benchmarks,
      write: folders.checkpoint_write_dir,
    }, null, 2)]),
  ]);
  page("Settings", "Launch checks the branch of this install only. A dirty tree, a failed fetch, or a history that is not a fast-forward skips the update and opens the current version.", el("div", {class: "stack"}, [form, watch, future]));
}

function splitLines(value) {
  return String(value || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
}

async function checkUpdates() {
  const host = document.querySelector("#update-result");
  try {
    const payload = await api("/api/update", {method: "POST", body: {apply: false}});
    const update = payload.update;
    host.textContent = `${update.action}: ${update.reason}` + (update.upstream ? ` Upstream ${String(update.upstream).slice(0, 12)}.` : "");
    if (update.action === "fast_forward" && confirm("Fast-forward this install and restart?")) {
      const applied = await api("/api/update", {method: "POST", body: {apply: true}});
      host.textContent = applied.update.reason || applied.update.action;
      if (applied.update.updated) location.reload();
    }
  } catch (error) { showError(error.message); }
}

function adoptRun(payload) {
  const previousRun = state.run || {};
  state.run = {...previousRun, ...payload};
  if (Array.isArray(payload.samples)) state.samples = payload.samples.slice();
  if (payload.sample) {
    const year = val(payload.sample.year);
    const previous = state.samples[state.samples.length - 1];
    if (previous && year != null && Number(val(previous.year)) > Number(year)) state.samples = [];
    if (!state.samples.length || val(state.samples[state.samples.length - 1].year) !== year) state.samples.push(payload.sample);
    else state.samples[state.samples.length - 1] = payload.sample;
  }
  paintTop();
  if (state.module === "control") paintLive(state.liveHost, state.chartHost);
}

let overviewTimer = null;
function scheduleOverview() {
  if (state.module !== "observatory" || overviewTimer) return;
  overviewTimer = setTimeout(async () => {
    overviewTimer = null;
    if (state.module === "observatory") await render();
  }, 400);
}

function connect() {
  const stream = new EventSource("/api/stream");
  stream.addEventListener("run", (event) => adoptRun(JSON.parse(event.data)));
  stream.addEventListener("world", () => scheduleOverview());
  stream.addEventListener("files", () => {
    if (state.module === "checkpoints") render();
    if (state.module === "performance") state.benchmarks = null;
  });
}

window.addEventListener("hashchange", () => {
  state.module = (location.hash || "#control").slice(1) || "control";
  render();
});

async function boot() {
  state.module = (location.hash || "#control").slice(1) || "control";
  state.status = await api("/api/status");
  state.run = state.status.run;
  state.samples = (state.run && state.run.samples) || [];
  if (state.status.last_update && state.status.last_update.action && state.status.last_update.action !== "up_to_date") {
    banner.hidden = false;
    banner.textContent = `Last update check: ${state.status.last_update.action}. ${state.status.last_update.reason || ""}`;
  }
  connect();
  await render();
}

boot().catch((error) => { showError(error.message); window.__ATE_READY = true; });
