const test = require("node:test");
const assert = require("node:assert");
const { total } = require("../src/server.js");
test("totals the lines", () => assert.equal(total([{ price: 2, quantity: 3 }]), 6));
// Red on day one on purpose: the suite that arrives with the code is not always green, and the gate has to
// quarantine it and say so rather than be red on day one itself.
test("applies a discount nobody has written", () => assert.equal(total([{ price: 10, quantity: 1 }]), 9));
