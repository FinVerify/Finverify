# FinVerify

Verification infrastructure for AI — starting with numerical/financial
claims, architected to extend to Healthcare, Legal, Aerospace, and Climate
verification without rewriting the engine each time.

## Structure

```
packages/
  core/            @finverify/core — the reusable, provider-agnostic,
                    event-driven, plugin-based verification engine.
                    Zero DOM, zero chrome.*, zero React. This is the
                    package every client below is meant to consume.
apps/
  extension/       @finverify/extension — the Chrome/browser extension.
                    A thin client: DOM adapters + a chrome.runtime
                    transport + UI wiring. All verification logic lives
                    in @finverify/core.
```

Future clients (VS Code extension, Desktop app, Enterprise Dashboard, AI
agent integrations) are meant to live alongside `apps/extension` as
siblings, each a thin client of the same `@finverify/core` package —
see `packages/core/README.md` for what "thin client" means concretely.

## Build

```bash
npm install          # installs and symlinks every workspace package
npm run build         # builds @finverify/core, then @finverify/extension
```

Or per-package:

```bash
npm run build -w @finverify/core
npm run build -w @finverify/extension
```

`apps/extension`'s build depends on `@finverify/core`'s `dist/` existing
first (its `package.json` points `main`/`types` at compiled output, not
raw TS) — the root `build` script above handles ordering; if building
manually, always build core first.

## Where to look for what

| I want to... | Look in |
|---|---|
| Understand or extend claim detection, trust scoring, retry/dedup/batching/cancellation | `packages/core/` |
| Add a new domain verifier (healthcare, legal, aerospace, climate) | `packages/core/README.md` → "Adding a domain plugin" |
| Add support for a new AI chat product (Claude, Gemini, Copilot, ...) | `apps/extension/docs/adding-a-provider.md` |
| Understand the extension's own architecture (adapters/messaging/UI wiring) | `apps/extension/docs/architecture.md` |
| Build a new client (VS Code, Desktop, Dashboard, agent) | Read `packages/core/README.md` first — a new client needs a `VerificationTransport` implementation and a UI shell; it does not need to reimplement anything else |
