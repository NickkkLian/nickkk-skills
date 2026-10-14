#!/usr/bin/env node
/* Offline chart regression checks. Execute the template's real formula and drawing functions
   in Node with a minimal SVG document; this does not check browser layout or interaction.
   node scripts/chart_check.js --selftest [path/to/old/starter.html]
   node scripts/chart_check.js output/loan.html
   No packages, network, or files written. */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assets = path.join(__dirname, "../assets");
const args = process.argv.slice(2);
const selftest = args[0] === "--selftest";
if (!args.length) {
  console.error("usage: node scripts/chart_check.js --selftest [template] | page.html");
  process.exit(2);
}
const source = fs.readFileSync(selftest ? args[1] || path.join(assets, "starter.html") : args[0], "utf8");
const loan = JSON.parse(fs.readFileSync(path.join(assets, "concepts/loan-payment.json"), "utf8"));
function section(a, b) {
  const start = source.indexOf(a), end = source.indexOf(b, start);
  if (start < 0 || end < 0) throw new Error("missing template section: " + a);
  return source.slice(start, end);
}
class Element {
  constructor(name) { this.name = name; this.attrs = {}; this.children = []; this.textContent = ""; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  appendChild(n) { this.children.push(n); }
  get firstChild() { return this.children[0]; }
  removeChild(n) { this.children.splice(this.children.indexOf(n), 1); }
  getBoundingClientRect() { return {width: 640}; }
}
function draw(concept, changes = {}) {
  const nodes = {chart: new Element("svg"), "chart-how": new Element("p")};
  const context = {window: {}, document: {createElementNS: (_, n) => new Element(n)},
    C: concept, SVGNS: "http://www.w3.org/2000/svg", $: id => nodes[id],
    copy: o => ({...o}), has: (o, k) => Object.hasOwn(o, k),
    chartDescription: "The full slider range is sampled.", stepped: /\b(floor|ceil|round)\(/.test(concept.formula)};
  vm.createContext(context);
  vm.runInContext(section("/* formula:start */", "/* formula:end */"), context);
  vm.runInContext("var fmt = Formula.fmt;", context);
  context.xc = concept.controls.find(c => c.name === concept.chart.x);
  context.values = Object.fromEntries(concept.controls.map(c => [c.name, c.value]));
  Object.assign(context.values, changes);
  vm.runInContext("var tree = Formula.parse(C.formula); function tryResult(v) { try { return Formula.evaluate(tree, v); } catch (e) { if (e instanceof Formula.FormulaError) return null; throw e; } } var lastResult = tryResult(values);", context);
  vm.runInContext(section("  function withUnit(", "  function errorText("), context);
  vm.runInContext(section("  function el(", '  window.addEventListener("resize", drawChart);') + "\ndrawChart();", context);
  return {nodes, result: context.lastResult,
    labels: nodes.chart.children.filter(n => n.name === "text" && n.attrs["text-anchor"] === "end" && !n.attrs.class && Number(n.attrs.y) < 225).map(n => n.textContent),
    ticks: nodes.chart.children.filter(n => n.name === "text" && !n.attrs.class).map(n => n.textContent),
    dot: nodes.chart.children.find(n => n.name === "circle"),
    curve: nodes.chart.children.find(n => n.name === "path")};
}
const clone = o => JSON.parse(JSON.stringify(o));
function linear(unit, locale, min = 0, max = 20000) {
  const c = clone(loan);
  c.formula = "x";
  c.controls = [{name: "x", label: "Input", min, max, step: (max - min) / 100, value: (min + max) / 2}];
  c.result = {name: "A", label: "Answer", unit};
  c.chart = {x: "x", title: "Answer by input"};
  if (locale) c.chart.locale = locale;
  return c;
}
let passed = 0, total = 0;
function check(label, action) {
  total++;
  try { if (!action()) throw new Error("assertion failed"); passed++; console.log("  PASS  " + label); }
  catch (e) { console.log("  FAIL  " + label + ": " + e.message); }
}
if (selftest) {
  check("sterling ticks include £15,000 with grouping and no pence", () => {
    const labels = draw(linear("£")).labels;
    if (!labels.includes("£15,000")) throw new Error("got " + labels.join(" · "));
    return true;
  });
  check("US dollar ticks follow en-US", () => draw(linear("$", "en-US")).labels.includes("$15,000"));
  check("German euro ticks follow de-DE", () => draw(linear("€", "de-DE")).labels.includes("15.000\u00a0€"));
  check("French euro ticks follow fr-FR", () => draw(linear("€", "fr-FR")).labels.includes("15\u202f000\u00a0€"));
  check("negative money keeps its sign and grouping", () => draw(linear("£", "en-GB", -20000, 0)).labels.includes("-£15,000"));
  check("fractional ticks stay distinct even with a whole-number headline", () => {
    const c = linear("£", "en-GB", 0, 0.004); c.result.decimals = 0;
    const labels = draw(c).labels;
    return labels.includes("£0.001") && new Set(labels).size === labels.length;
  });
  check("physical units and singular forms remain on the axis", () => {
    const c = linear("metres", "en-GB", 0, 4); c.result.unit_one = "metre";
    return draw(c).labels.includes("1 metre") && draw(c).labels.includes("2 metres");
  });
  check("horizontal ticks use the concept's locale", () => draw(linear("%", "de-DE")).ticks.includes("15.000"));
  check("loan scale shows ordinary payments below £6,000 and keeps the current dot", () => {
    const r = draw(loan);
    return Number(r.nodes.chart.attrs["data-y-max"]) <= 6000 && r.dot && /extreme sampled/.test(r.nodes["chart-how"].textContent);
  });
  check("one-year loan answer stays correct and discloses its omitted dot", () => {
    const r = draw(loan, {y: 1});
    return Math.abs(r.result - 17121.49635769) < 1e-6 && !r.dot && /Current answer:.*dot is omitted/.test(r.nodes["chart-how"].textContent);
  });
  check("bounded low plateaus remain visible", () => {
    const c = linear("", "en-GB", 0, 100); c.formula = "1 - exp(-x)";
    const r = draw(c, {x: 0});
    return r.dot && Number(r.nodes.chart.attrs["data-y-min"]) <= 0;
  });
  check("negative extreme tails are clipped symmetrically", () => {
    const c = clone(loan); c.formula = "-(" + c.formula + ")";
    const r = draw(c);
    return Number(r.nodes.chart.attrs["data-y-min"]) >= -6000 && r.dot;
  });
  check("undefined samples break the path and are disclosed", () => {
    const c = linear("", "en-GB", -1, 1); c.formula = "1/x";
    const r = draw(c);
    return /undefined/.test(r.nodes["chart-how"].textContent) && (r.curve.attrs.d.match(/M/g) || []).length >= 2;
  });
  check("constant curves still have a finite nonzero scale", () => {
    const c = linear("£", "en-GB"); c.formula = "7";
    const r = draw(c), a = Number(r.nodes.chart.attrs["data-y-min"]), b = Number(r.nodes.chart.attrs["data-y-max"]);
    return Number.isFinite(a) && Number.isFinite(b) && b > a && r.dot;
  });
} else {
  const concept = JSON.parse(source.match(/<script type="application\/json" id="concept">([\s\S]*?)<\/script>/)[1]);
  const r = draw(concept);
  check("generated loan page has grouped sterling axis ticks without pence", () => r.labels.length > 1 && r.labels.every(s => /^-?£[\d,]+$/.test(s)) && r.labels.some(s => s.includes(",")));
  check("generated loan page shows the ordinary curve and current dot", () => Number(r.nodes.chart.attrs["data-y-max"]) <= 6000 && r.dot);
  console.log("  axis: " + r.labels.join(" · "));
  console.log("  note: " + r.nodes["chart-how"].textContent);
}
console.log(`chart_check ${selftest ? "selftest" : "page"}: ${passed}/${total} passed`);
process.exit(passed === total ? 0 : 1);
