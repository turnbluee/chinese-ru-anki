"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync("web/card.js", "utf8"), context);

const cards = context.window.ChineseCards;
assert.equal(cards.normalizePinyin(" BAI4 BAI0 "), "bai4bai0");
assert.equal(cards.checkPinyin("bai4bai0", "bai4bai0").ok, true);

const toneFive = cards.checkPinyin("bai4bai5", "bai4bai0");
assert.equal(toneFive.ok, false);
assert.match(toneFive.message, /тон 5 запрещён/);

for (const valid of ["ma0", "de0", "le0", "xue2sheng0", "piao4liang0"])
  assert.equal(cards.checkPinyin(valid, valid).ok, true, valid);

for (const invalid of ["ma5", "de5", "le5", "xue2sheng5", "piao4liang5"])
  assert.equal(cards.checkPinyin(invalid, invalid.replaceAll("5", "0")).ok, false, invalid);

console.log("card.js pinyin checks passed");
