"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {estimateCoverage, parseCsv, readCsv, resultCsv} = require("../web/app.js");

test("Wilson reference and dropout", () => {
  const r = estimateCoverage(100, 80, 90, 72);
  assert.equal(r.coverage_percent, 80);
  assert.equal(r.ci_lower_percent, 71.12);
  assert.equal(r.ci_upper_percent, 86.66);
  assert.equal(r.dropout_percent, 20);
});
test("Boundary values", () => {
  assert.equal(estimateCoverage(100, 0).ci_lower_percent, 0);
  assert.equal(estimateCoverage(100, 100).ci_upper_percent, 100);
  assert.equal(estimateCoverage(100, 0, 0, 0).dropout_percent, null);
});
test("Reject invalid counts and dose series", () => {
  for (const params of [[0,0], [100,101], [100,-1], [100,50,20,null],
      [100,50,20,21], [100.5,10], [true,10]]) {
    assert.throws(() => estimateCoverage(...params));
  }
});
test("Read quoted CSV and reject incorrect rows", () => {
  assert.deepEqual(parseCsv('group,population,vaccinated\n"West, Area",100,80\n')[1], ["West, Area", "100", "80"]);
  const d = readCsv('group,population,vaccinated\nA,100,80\nB,100,110\n');
  assert.equal(d.results.length, 1);
  assert.equal(d.errors.length, 1);
});
test("CSV export prevents spreadsheet formula injection", () => {
  const row = {...estimateCoverage(100,80), group: "=cmd"};
  assert.match(resultCsv([row]), /"'=cmd"/);
});
