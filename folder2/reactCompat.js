const { version: reactVersion } = require("react/package.json");
const { version: reactDomVersion } = require("react-dom/package.json");

const SUPPORTED_REACT_MAJOR = 19;

function assertReactCompatibility() {
  const reactMajor = Number(reactVersion.split(".")[0]);
  const reactDomMajor = Number(reactDomVersion.split(".")[0]);

  if (reactMajor !== reactDomMajor) {
    throw new Error(
      `React ${reactVersion} and React-DOM ${reactDomVersion} must use the same major version.`
    );
  }

  if (reactMajor > SUPPORTED_REACT_MAJOR) {
    throw new Error(
      `React ${reactVersion} is installed, but this app supports only React ${SUPPORTED_REACT_MAJOR}.`
    );
  }
}

module.exports = { assertReactCompatibility };
