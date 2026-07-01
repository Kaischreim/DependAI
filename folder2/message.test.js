const test = require("node:test");
const assert = require("node:assert/strict");

const { makeGreeting } = require("./message");

test("makeGreeting creates a greeting", () => {
  assert.equal(makeGreeting("Kai"), "Hello, Kai!");
});
