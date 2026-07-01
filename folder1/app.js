const express = require("express");
const { version: expressVersion } = require("express/package.json");

// Deliberate compatibility gate for testing Dependabot + AI Fix.
const SUPPORTED_EXPRESS_MAJOR = 5;

function createApp() {
  const installedMajor = Number(expressVersion.split(".")[0]);

  if (installedMajor > SUPPORTED_EXPRESS_MAJOR) {
    throw new Error(
      `Express ${expressVersion} is installed, but this app supports only Express ${SUPPORTED_EXPRESS_MAJOR}. Update the application compatibility setting.`
    );
  }

  const app = express();

  app.get("/health", (_req, res) => {
    res.status(200).json({ ok: true });
  });

  return app;
}

module.exports = { createApp };
