// react-dom/test-utils's `act` warns unless the environment declares itself
// React-act-aware; this repo renders directly via `act` (no
// @testing-library, which normally sets this) so it must be set here.
globalThis.IS_REACT_ACT_ENVIRONMENT = true
