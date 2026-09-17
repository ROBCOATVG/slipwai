const test = require("node:test");
const assert = require("node:assert");
const { total } = require("../src/adapters/http");

test("a basket costs the sum of its items", () => {
  assert.strictEqual(total([{ price: 2 }, { price: 3 }]), 5);
});
