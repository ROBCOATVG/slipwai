const test = require("node:test");
const assert = require("node:assert");
const { total } = require("../src/prices.js");
test("totals the lines", () => assert.equal(total([{ price: 2, quantity: 3 }]), 6));
