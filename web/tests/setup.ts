// react-dom/test-utils's `act` warns unless the environment declares itself
// React-act-aware; this repo renders directly via `act` (no
// @testing-library, which normally sets this) so it must be set here.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

// jsdom's requestAnimationFrame is a real ~16ms wall-clock timer. zrender
// (echarts' renderer) captures a reference to it once at module load time
// and drives its whole render/animation loop -- including the initial
// paint -- through it, so a chart's first <canvas> only appears after real
// time passes. That makes canvas-presence assertions genuinely racy against
// a test's own `act()` calls, not just against the missing 2D context below
// -- confirmed by direct experiment: patching rAF to resolve on a microtask
// instead removes the raciness. This must be set here, in a setup file that
// runs before any test file's imports, not inside a test -- zrender reads
// `window.requestAnimationFrame` once when its module first loads (via the
// chain ChartView -> echarts-for-react -> echarts -> zrender), so a patch
// applied later has no effect on the reference it already captured.
globalThis.requestAnimationFrame = ((fn: FrameRequestCallback) => {
  queueMicrotask(() => fn(0))
  return 0
}) as typeof requestAnimationFrame

// jsdom implements HTMLCanvasElement but not a real 2D rendering context
// (that requires the native `canvas` package, deliberately not added --
// see HANDOFF.md). Without a stub, `getContext('2d')` returns null and
// echarts' own Layer/CanvasPainter dispose+redraw code crashes calling
// methods like `clearRect` on it. This list was seeded by grepping
// node_modules/{zrender,echarts}/lib for every `ctx.<method>(` call site,
// then extended with `arcTo` and `scale` -- reachable via differently-named
// context variables (PathProxy's `_ctx`, Layer's double-buffer `ctxBack`)
// that the literal `ctx.` grep pattern doesn't match -- and `draw`, which
// callers only invoke behind an `if (ctx.draw)` existence check, so it must
// exist as a no-op rather than be left undefined. Not claimed exhaustive
// beyond that: a context variable under some other name could still exist
// uncovered.
const CANVAS_2D_METHODS = [
  'arc',
  'arcTo',
  'beginPath',
  'bezierCurveTo',
  'clearRect',
  'clip',
  'closePath',
  'createLinearGradient',
  'createPattern',
  'createRadialGradient',
  'draw',
  'drawImage',
  'ellipse',
  'fill',
  'fillRect',
  'fillText',
  'getImageData',
  'lineTo',
  'measureText',
  'moveTo',
  'putImageData',
  'quadraticCurveTo',
  'rect',
  'restore',
  'save',
  'scale',
  'setLineDash',
  'setTransform',
  'stroke',
  'strokeText',
] as const

function createCanvas2DContextStub(canvas: HTMLCanvasElement) {
  const gradientStub = { addColorStop: () => {} }
  const stub: Record<string, unknown> = { canvas }
  for (const method of CANVAS_2D_METHODS) stub[method] = () => {}
  // zrender's own text-measurement fallback (for when getContext returns
  // falsy) only triggers if measureText is absent -- since our stub is
  // truthy, `.width` must come back real-shaped or it throws instead.
  stub.measureText = () => ({ width: 0 })
  // Callers chain `.addColorStop(...)` off the gradient object returned
  // by these two.
  stub.createLinearGradient = () => gradientStub
  stub.createRadialGradient = () => gradientStub
  return stub as unknown as CanvasRenderingContext2D
}

// Cached per canvas so repeated getContext('2d') calls on the same
// element return the same object, matching real browsers' per-canvas
// context singleton behavior.
const canvas2DContextStubs = new WeakMap<HTMLCanvasElement, CanvasRenderingContext2D>()

const originalGetContext = HTMLCanvasElement.prototype.getContext
HTMLCanvasElement.prototype.getContext = function (
  this: HTMLCanvasElement,
  contextId: string,
  ...args: unknown[]
) {
  if (contextId === '2d') {
    let stub = canvas2DContextStubs.get(this)
    if (!stub) {
      stub = createCanvas2DContextStub(this)
      canvas2DContextStubs.set(this, stub)
    }
    return stub
  }
  return (originalGetContext as (...a: unknown[]) => unknown).apply(this, [contextId, ...args])
} as typeof HTMLCanvasElement.prototype.getContext
