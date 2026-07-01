const test = require("node:test");
const assert = require("node:assert/strict");

const { assertReactCompatibility } = require("./reactCompat");

test("app supports the installed React stack", () => {
  assert.doesNotThrow(() => assertReactCompatibility());
});
