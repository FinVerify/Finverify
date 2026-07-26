# Examples

Runnable, dependency-minimal demonstrations of `@finverify/core`. Build
core first (`npm run build:core` from the repo root), then run any
example directly with `node`.

| Example | Demonstrates |
|---|---|
| `node-basic-usage/` | The minimum code for a new Node-based client: engine + the built-in HTTP transport (real network) + finance plugin + event subscription. |
| `custom-transport/` | Implementing `VerificationTransport` yourself — the pattern a browser extension, VS Code extension, or sandboxed agent runtime follows when it can't use `createHttpTransport()` as-is. Fully offline, safe to run. Also demonstrates cancellation. |
| `custom-plugin/` | A complete worked "add a new domain verifier" tutorial — builds a small legal-citation plugin from scratch, registers it alongside `financePlugin`, and verifies a mixed-domain claim set through one engine with zero changes to `@finverify/core` itself. Fully offline, safe to run. |

`custom-transport` and `custom-plugin` make no external network calls and
are safe to run anywhere. `node-basic-usage` calls the real FinVerify
backend (`createHttpTransport()`'s default) — expect it to make one real
`/v1/verify` request per detected claim.
