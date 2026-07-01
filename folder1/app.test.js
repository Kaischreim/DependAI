const test = require("node:test");
const assert = require("node:assert/strict");

const { createApp } = require("./app");

test("creates an Express app", () => {
  const app = createApp();

  assert.equal(typeof app.get, "function");
});
