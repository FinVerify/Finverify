# FinVerify Extension — Forensic Architecture & Reliability Audit

Repository audited: `github.com/FinVerify/Finverify` (monorepo), specifically:
- `finverify-extension/` — the browser extension (apps/extension, packages/core)
- `finverify-terminal/backend/` — the DVL backend the extension calls (`/v1/verify`)

Method: this audit was produced by cloning the repository and reading source
directly (not inferred from the screenshot alone). Every claim below is
labeled **VERIFIED** (traced in code, file/line referenced), **INFERRED**
(strong architectural reasoning from verified code, not independently
executed), or **UNVERIFIED / RECOMMENDATION** (could not be confirmed from
static reading alone — needs a live run to close out). Per the brief, no
code was changed.

---

## A. Executive Summary

**What's good:**
- `packages/core` (the shared TS engine) is genuinely well-architected: a
  domain-agnostic plugin system (`VerifierPlugin`), a transport seam that
  cleanly separates "how do I reach the network" from "what do I verify"
  (`VerificationTransport`), real cancellation via `AbortController`,
  engine-wide request dedup with TTL, and exponential backoff with jitter.
  This is not a prototype-quality core.
- Provider-adapter *gating* is already correct: `resolveAdapter()` refuses
  to activate any adapter whose `verified` flag is `false`, and
  Gemini/Copilot/Perplexity are already clean `createUnverifiedStub()`s.
  Nothing currently reaches real users half-built.
- `packages/core` has real unit tests for the engine, session, retry,
  finance-claim detection, http-transport, and trust palette.
- The Claude adapter's own source comments are unusually honest about their
  sourcing confidence (two independent third-party DOM references, not a
  live authenticated session) — this is good practice, not a red flag.

**What's broken (P0):**
- The headline "confidence %" the user sees is **not a confidence score in
  any meaningful sense**. It's an average of a flat per-tier weight
  (`LOW→20`) applied to a backend trust label that silently defaults to
  `LOW` whenever no external evidence is found — which, given how the
  extension calls the API today (no ticker/entity/period context), is most
  of the time. "17/17 matched exactly, 20% confidence" is not a rare edge
  case; it is close to the *expected* output shape for the current
  integration pattern. Full trace in Section C.
- The verification-state model conflates "we have no evidence either way"
  with "this looks wrong" at **three separate layers** (backend rule
  fallback, API response schema, frontend weighting). There is no
  `UNVERIFIED` state anywhere in the type system.
- `GET/POST/DELETE /v1/history/{user_id}` on the backend has no
  authorization check binding the caller to `user_id` — a straightforward
  IDOR (Section P).

**What's risky (P1):**
- On claude.ai specifically, the extension's own badge is mounted as a DOM
  *descendant* of the tracked message element (confirmed in the adapter's
  own source comments), unlike ChatGPT where it's a sibling. The
  numbers-heavy panel is safely portaled to `document.body`, so this isn't
  firing today, but there is no structural guard (e.g. excluding
  `[data-finverify-badge]` before reading `innerText`) preventing a future
  change from creating a real self-observation feedback loop.
- `engineInstance.ts` hardcodes `model_source: "chatgpt.com"` regardless of
  which site is active — a real provenance/observability bug, live today.
- Claim-pattern overlap can produce duplicate claims for the same text span
  under two different `claim_type`s (Section G).
- Zero test coverage on the exact function that produces the buggy
  confidence number (`trustWeight`/`deriveAnalystSummary` in
  `VerificationCard.tsx`).

---

## B. Current Architecture (as verified)

```
LLM webpage (chatgpt.com | claude.ai)
  → content script (apps/extension/src/content/orchestrator.tsx)
      MutationObserver(document.body) + rAF-coalesced scan()
  → adapter.findMessages() / adapter.extractText()   [per-provider, apps/extension/src/adapters/*]
  → InlineBadge (apps/extension/src/ui/InlineBadge.tsx)
      engine.detectClaims(text)   [packages/core → finance plugin regex]
      session.verify(claims)     [packages/core/src/session.ts]
  → VerificationTransport.verify()
      chromeTransport → chrome.runtime.sendMessage → background service worker
      → createHttpTransport() (packages/core/src/http-transport.ts)
      → POST https://aadi2026-finverify-api.hf.space/v1/verify
  → FastAPI backend (finverify-terminal/backend/app/main.py::v1_verify_endpoint)
      → core.engine.verify() → DVL math + evidence retrieval + trust_engine.compute_trust()
  → V1VerifyResponse {verified_value, correction_applied, trust_score, trust_color, delta_pct}
  → back through background worker → chromeTransport → session → EventBus
  → InlineBadge / VerificationCard render (deriveOverallStatus, deriveAnalystSummary)
```

Key structural facts (all **VERIFIED**):
- One `VerificationEngine` instance per content-script context
  (`engineInstance.ts`), one `financePlugin` registered.
- One `VerificationSession` per tracked message (`orchestrator.tsx`'s
  `tracked: Map<HTMLElement, TrackedEntry>`), created inside `InlineBadge`,
  cancelled on unmount (message pruned from DOM).
- Request dedup is **engine-wide**, keyed on `${question}|${rawValue}`, not
  session-scoped — intentional (`session.ts` doc comment), so identical
  claims across two different messages share one network call.
- The background service worker is the *only* place with real `fetch`
  access (content scripts hit host-page CSP); it owns `requestId →
  AbortController` bookkeeping for cancellation.
- Content script → background → backend is three hops for every single
  claim; there is no batch endpoint used despite one existing
  (`/v1/verify/batch`, `backend/app/main.py:421` — **VERIFIED present,
  unused by the extension**).

---

## C. Root Cause Analysis — the 20% confidence bug

This is the most load-bearing finding in the audit, so it's given in full
with exact file/line evidence, answering the audit's 13 sub-questions
directly.

### C.1 — Where does `20` come from? (frontend)

`apps/extension/src/ui/VerificationCard.tsx`:

```ts
function trustWeight(t: TrustScore): number {
  if (t === "HIGH") return 100;
  if (t === "MEDIUM") return 60;
  return 20; // LOW
}
...
const confidencePercent = verified.length
  ? Math.round(verified.reduce((sum, c) => sum + trustWeight(c.result!.trust_score), 0) / verified.length)
  : 0;
```

This is a **flat, hardcoded, frontend-only weighting scale**. It has no
relationship to any numeric score the backend computes (see C.3 — the
backend *does* compute a float score, and the API never sends it). If every
verified claim in a message comes back `LOW`, the average is mechanically
`20`, regardless of how many claims there are. **This is exactly why
17/17 claims produces 20%**: 17 values of 20, averaged, is 20.

Answering the audit's specific questions:
- *"Is it a fallback/default score?"* — Yes, but the fallback lives one
  layer down, in the backend (C.2), and gets **re-encoded** into a second,
  unrelated fallback number on the frontend.
- *"Is 'unverified' being incorrectly represented as a numerical confidence
  score?"* — Yes. `LOW` here does not mean "verified and found to be
  wrong" — see C.2. There is no code path that ever produces a value
  between the three fixed points (20/60/100); "confidence" is a lie of
  precision layered on top of a 3-value categorical label.
- *"Is the client-side DVL fallback overriding backend results?"* — No.
  `financeOfflineFallback()` (packages/core) only runs when the transport
  throws, and it's clearly marked `OFFLINE` in the UI when it does
  (`isOffline` badge, `claim.error` set). The 20% in the reported
  screenshot is not this path (that path never labels itself "verified
  matched exactly").
- *"Are multiple verification results being incorrectly aggregated?"* —
  Aggregation itself (`deriveAnalystSummary`, `deriveOverallStatus`) is
  arithmetically correct given its inputs; the *inputs* are the problem.
- *"Is the UI displaying a derived score rather than the actual per-claim
  verification state?"* — Yes, precisely. The per-claim state is a
  3-value label; the UI presents a 2-decimal-free but still falsely
  precise-looking percentage built by averaging a made-up integer scale.

### C.2 — Where does `trust_score = LOW` come from for a claim that
"matched exactly"? (backend — the real root cause)

`finverify-terminal/backend/core/trust_engine.py`:

```python
TRUST_RULES: list[dict[str, Any]] = [
    {"match": (EvidenceTier.PRIMARY,   CorrectionSeverity.NONE,       Ambiguity.LOW, Consistency.PASS), "label": "HIGH", "score": 0.90, ...},
    {"match": (EvidenceTier.PRIMARY,   CorrectionSeverity.SCALE_ONLY, Ambiguity.LOW, Consistency.PASS), "label": "HIGH", "score": 0.90, ...},
    {"match": (EvidenceTier.SECONDARY, CorrectionSeverity.NONE,       Ambiguity.LOW, Consistency.PASS), "label": "HIGH", "score": 0.85, ...},
    {"match": (EvidenceTier.SECONDARY, CorrectionSeverity.SCALE_ONLY, Ambiguity.LOW, Consistency.PASS), "label": "MEDIUM", "score": 0.65, ...},
    {"match": (EvidenceTier.PRIMARY,   CorrectionSeverity.MULTIPLE,   Ambiguity.MEDIUM, Consistency.PASS), "label": "MEDIUM", "score": 0.60, ...},
    {"match": (EvidenceTier.PRIMARY,   CorrectionSeverity.NONE,       None, Consistency.PASS), "label": "HIGH", "score": 0.88, ...},
]
DEFAULT_LABEL = "LOW"
DEFAULT_SCORE = 0.25
DEFAULT_REASON = "Default fallback"

def derive_label(findings: TrustFindings) -> tuple[str, float, str, str]:
    for rule in TRUST_RULES:
        ...  # first match wins
    return DEFAULT_LABEL, DEFAULT_SCORE, DEFAULT_COLOUR, DEFAULT_REASON
```

Every single rule in `TRUST_RULES` requires `evidence_tier` to be `PRIMARY`
or `SECONDARY`. `evidence_tier` is resolved in `backend/providers/base.py`:

```python
def resolve_provider_tier(provider_name, provider_metadata=None) -> EvidenceTier:
    metadata = provider_metadata or {}
    tier = metadata.get("tier")
    if isinstance(tier, str): ...  # not set by the extension's request
    normalized_name = (provider_name or "").strip().lower()
    if "sec" in normalized_name: return EvidenceTier.PRIMARY
    if any(t in normalized_name for t in ("fred", "dbnomics")): return EvidenceTier.SECONDARY
    if "model" in normalized_name: return EvidenceTier.MODEL
    return EvidenceTier.USER   # ← falls through here
```

The extension's `/v1/verify` request body is only `{question, raw_value,
model_source}` (`packages/core/src/types.ts::V1VerifyRequest`). There is no
ticker, entity, or ground-truth reference passed. `compute_findings()` in
`trust_engine.py` only sets `context.provider` from `evidence[0].source.name`
*if evidence was actually retrieved* — and when the evidence retriever
finds nothing (which is the common case for a standalone `question +
raw_value` call with no entity context), `provider_name` stays `None`,
`resolve_provider_tier(None, {})` returns `EvidenceTier.USER`, and **no
rule in `TRUST_RULES` has a `USER`-tier entry** → `derive_label()` falls
through to the hardcoded default: `label="LOW", score=0.25, reason="Default
fallback"`.

Critically, this happens **independent of whether any correction was
applied**. A claim whose raw value needed zero correction (i.e. "matched
verification exactly," per the extension's own analyst-summary copy) still
gets `LOW` if no evidence was found. This is confirmed independently in the
older, still-present `dvl.py::compute_trust()`:

```python
def compute_trust(raw, verified, logs, ambiguous=False):
    if len(logs) == 0:
        return "HIGH", "#00ff88"
    if ambiguous:
        return "LOW", "#f87171"          # ← "matched, but ambiguous" → LOW
    ...
```

and in `verify_canonical()` (`dvl.py:218-222`), `ambiguous=True` is set
specifically for ratio-typed claims (margin/return/growth/rate/percent)
with a value in `[1, 100]` and **no ground truth available** — i.e. exactly
"we can't tell if this needs scaling because we have nothing to check it
against," which is a statement about *evidence availability*, not about
correctness. (Both `dvl.py::compute_trust` and `trust_engine.py::compute_trust`
exist in the codebase and are called from different code paths —
`verify_canonical` vs. `core.engine.verify` — see Section E for the
duplication risk this represents.)

**Direct answer to the audit's question "why does lack of corroborating
evidence map to 20%?":** because the backend encodes "no evidence" as the
*same label* (`LOW`) used for "evidence found and it disagrees," and the
frontend then encodes that label as a flat, low, made-up number (20) with
no distinction from a genuinely contradicted claim. Two independent lossy
compressions of the same underlying "we don't know" signal, stacked.

### C.3 — The richer backend signal that gets thrown away

`trust_engine.py::compute_trust()` actually returns a `TrustScore` object
with `score: float` (0.25–0.90, not just three buckets) and a `reasons:
list[str]` explaining evidence tier / correction severity / ambiguity /
consistency / rule evidence. **None of this reaches the extension.**
`V1VerifyResponse` (`backend/app/models.py`, mirrored in
`packages/core/src/types.ts`) only exposes:

```ts
trust_score: "HIGH" | "MEDIUM" | "LOW" | "N/A";
trust_color: string;
```

The float `score` and the `reasons` array are computed and then discarded
before the response is built (need to confirm `V1VerifyResponse`'s Pydantic
model doesn't serialize them — **VERIFIED** by reading `main.py:408-418`,
which manually constructs the response from `trust_label`/`trust_color`
only). This is a second, independent instance of the same root problem:
useful graduated signal exists and is being collapsed to a 3-value label
before it ever reaches a UI that then re-expands it into a fake-precise
percentage.

### C.4 — Duplicate "20% / 20% / 20% / 20% / $383 / $383.3B" metric rows

**UNVERIFIED as a single mechanism** — I could not fully reproduce this
from static reading alone, and want to be honest about that rather than
invent a plausible-sounding story. What is and isn't supported by code:

- `MetricRow` (`VerificationCard.tsx`) renders `formatValue(raw_value)` and
  `formatValue(verified_value)` per claim — **not** the confidence
  percentage — so four literal "20%" rows would most plausibly mean four
  *separate claims* whose own `raw_value`/`verified_value` happened to be
  ≈20 (e.g. several distinct margin/return figures near 20% in one
  earnings-call-style response), which is a real and unremarkable
  transcript pattern, not obviously a bug.
- I traced a genuine, code-confirmed *structural* risk that could produce
  exactly this pattern under different conditions (self-observation via
  DOM nesting on claude.ai — see Section E.3) but the current rendering
  path (badge portaled to `document.body`) does not, on its own, put
  "20%"/"$383.3B" text inside the tracked message element's `innerText`.
- The `$383` / `$383.3B` pairing is consistent with `formatValue`'s own
  branching (`>=100` → `$value.toFixed(2)` i.e. `"$383.30"`-ish vs.
  `>=1e9` → `"$383.3B"`) being applied to the *same underlying claim's*
  raw vs. verified value in one `MetricRow` — which is expected, working
  behavior, not a bug, if that's what's being seen in the screenshot.

**Recommendation:** reproduce with the exact transcript that produced the
screenshot and capture the raw `VerifiedClaim[]` array (e.g. via a
temporary `console.table` or the existing `[FV-DEBUG]` logging already
wired into the orchestrator) before assuming a second bug exists here. This
is exactly the kind of claim the brief says not to guess at — flagged
`UNVERIFIED / EXPERIMENTAL` rather than asserted.

---

## D. Verification State Model — what it should be

**Current state** (`packages/core/src/types.ts`):
```ts
export type TrustScore = "HIGH" | "MEDIUM" | "LOW" | "N/A";
export interface VerifiedClaim extends ExtractedClaim {
  status: "pending" | "verified" | "error" | "cancelled";
  result?: V1VerifyResponse;
  error?: string;
}
```

`status` only tracks *pipeline* state (did we get an HTTP response), not
*evidentiary* state (did we actually corroborate the value). `trust_score`
is being asked to carry both "how much did we have to correct this" and
"how much evidence do we have," which is the structural cause of Section C.

**Recommended schema** (additive — does not require dropping
`trust_score`, which the UI still needs for its existing color logic):

```ts
export type VerificationStatus =
  | "verified"       // evidence found, value confirmed (with or without correction)
  | "contradicted"   // evidence found, value conflicts and could not be reconciled
  | "unverified"      // extracted fine, but no independent evidence was available — NOT a claim about correctness
  | "pending"
  | "error";          // infrastructure/network/API failure, not an evidentiary judgment

export interface V1VerifyResponse {
  question: string;
  raw_value: number;
  verified_value: number;
  correction_applied: string | null;
  verification_status: VerificationStatus;   // NEW — primary signal
  trust_score: TrustScore;                    // KEPT for color/legacy, now a display hint, not the primary signal
  confidence: number | null;                  // NEW — the backend's real float score (0–1), null when unverified
  trust_color: string;
  delta_pct: number;
  reasons: string[];                          // NEW — surfaces trust_engine.py's existing reasons array
  dvl_version: string;
  timestamp: string;
}
```

Backend changes required to support this (Section T has the Codex-ready
version): stop collapsing `EvidenceTier.USER` (no evidence) into the same
`DEFAULT_LABEL = "LOW"` used for genuine contradictions. A `USER`-tier /
no-evidence finding should route to `verification_status = "unverified"`
with `trust_score = "N/A"`, distinct from a rule match that actively found
conflicting evidence (`verification_status = "contradicted"`, `trust_score
= "LOW"`).

**Frontend consequence:** `trustWeight()`'s LOW=20 average must not include
`unverified` claims in the confidence average at all — an average is not a
meaningful summary of "here's a number, and separately, here's how many
things we simply couldn't check." The two need to be reported as separate
counts (which `deriveAnalystSummary` already half-does via
`lowConfidenceUncorrected`/`unavailable` — it just also *also* folds the
same claims into the numeric average, which is the contradiction).

---

## E. Claim Extraction Audit

`packages/core/src/plugins/finance/detect.ts`, ported 1:1 (per its own doc
comment) from `finverify-terminal/backend/ingestion/transcripts.py`.

**Verified-safe (no evidence of the audit's feared failure modes):**
- Years/dates are not mistakenly captured: every `CLAIM_PATTERNS` entry
  requires a `$`, `%`, `bps`/`basis points`, or an explicit financial
  keyword (`EPS`, `margin`, `revenue`, `CET1`/`tier 1`, `return`/`ROTCE`
  etc.) adjacent to the number. A bare "In 2024, the company..." cannot
  match any pattern.
- Negative numbers / parentheses / commas: `numStr.replace(/,/g, "")` +
  `parseFloat` handles commas and standard negatives (`-94.9`); **not
  verified**: whether accounting-style parenthesized negatives (`(94.9)`)
  are handled — no test covers this and no pattern strips parens. Likely
  gap, not confirmed exploitable.
- Millions/billions/trillions: `SCALE_MAP` covers billion/million/thousand
  and B/M/K/bn/mn abbreviations, tested (`finance-detect.test.ts`).
  **Note**: no `trillion`/`T` entry exists in `SCALE_MAP` despite `T` being
  common in large-cap market-cap reporting — real gap, easy fix.

**Confirmed real gaps:**
1. **Overlapping-pattern duplication.** All 12 `CLAIM_PATTERNS` run over
   every sentence unconditionally; dedup is keyed on
   `` `${sentence.slice(0,50)}:${m[0]}` `` — i.e. deduped only when the
   *exact matched substring* is identical. `"return on equity of 15.2%"`
   matches both the generic `percentage` pattern (`m[0] = "15.2%"`) and the
   `return_metric` pattern (`m[0] = "return on equity of 15.2%"`). Because
   `m[0]` differs, both survive dedup as two separate claims for the same
   number, with different `claim_type`s and therefore potentially
   different DVL questions/trust outcomes for what a user would see as one
   fact. This directly inflates claim counts (part of why "17 claims" can
   overstate distinct facts) and can produce visibly redundant metric rows.
2. **No `trillion`/`T` scale support** (above).
3. **Currency-raw vs currency ordering risk**: `currency_raw`'s regex uses
   a negative lookahead against scale words, which is correct, but it's a
   *second, independent* pass over the same sentence — a value like
   `$94.9 billion` is correctly claimed once as `currency`, but nothing
   stops a *different* dollar figure in the same sentence like `$1.2` (a
   per-share stub, a footnote) from separately matching `currency_raw` —
   working as designed, but worth flagging that "financial claim" here
   really means "any dollar/percent-shaped token," with no sentence-level
   cap or plausibility filtering (e.g. a page number, a footnote marker
   rendered as `$3`).
4. **No self-exclusion of FinVerify's own DOM.** Neither `extractText()`
   implementation (ChatGPT or Claude adapter) excludes elements carrying
   `data-finverify-badge` or `data-finverify-fallback-mount` before reading
   `innerText`/`textContent`. On ChatGPT this is currently safe only
   because the toolbar happens to be a DOM sibling, not because of an
   explicit guard. This is exactly the kind of implicit invariant that
   breaks silently on a provider markup change — recommend an explicit
   exclusion regardless of current adapter geometry (cheap, high
   defense-in-depth value; see Codex spec Phase 1).

---

## F. ChatGPT & Claude Adapter Audit

Both adapters share `apps/extension/src/adapters/shared/domUtils.ts`
(good — this is exactly the "shared scaffolding, provider-specific
selectors" split the brief asks for future providers to follow).

**ChatGPT** (`adapters/chatgpt/index.ts`) — `verified: true`:
- 3-tier selector fallback (`MESSAGE_SELECTORS` → semantic candidates),
  each wrapped in `safeQueryAll` so a malformed/changed selector degrades
  to empty rather than throwing.
- Toolbar located via `messageEl.closest("article") ?? messageEl.parentElement
  ?? messageEl`, then label-hint button matching — this resolves to a
  container that is an *ancestor or sibling scope* of `messageEl`, not a
  descendant, which is why the self-observation risk (E.4) doesn't fire on
  this adapter today.
- `isStreaming()` is explicitly documented as "best-effort... can
  false-positive"; no cap is visible in this file on how long the
  orchestrator will treat a message as "still streaming" — **UNVERIFIED**
  whether `orchestrator.tsx` enforces a timeout here (not found in the
  files reviewed); worth confirming, since a stuck `isStreaming()===true`
  forever would silently prevent a message from ever mounting a badge.

**Claude** (`adapters/claude/index.ts`) — `verified: true`, but the file's
own header comment says selectors were reconstructed from two third-party
sources, **not** a live authenticated DevTools session, and that `verified`
should stay `false` until that happens — **yet the flag is set to `true`**
(line 104) while the comment immediately above it says the opposite. This
is either a stale comment or a flag flipped before the documented
checklist was actually completed — worth resolving one way or the other
before shipping wider (this is a process/documentation defect, not
necessarily a functional one, but it's exactly the kind of drift the brief
asked to catch).
- No positive "this is Claude's message" DOM marker exists (both sourcing
  references agree); detection instead works backward from the action
  bar's feedback button, walking up to 20 ancestor levels
  (`findTurnContainer`) to find "the container that doesn't also contain
  the human's turn." This is inherently more fragile than a positive
  marker and is explicitly flagged by the code's own comments as such.
- **Toolbar/action-bar is a DOM descendant of the returned message
  container** (confirmed by the `extractText()` comment: "that toolbar is
  necessarily a descendant of what we return here, unlike ChatGPT"). This
  is the structural fact behind Section E.4/Section C.4's risk.
- `isStreaming()`'s heuristic ("no settled action bar yet = still
  streaming") is explicitly noted in-code as *not confirmed* by either
  sourcing reference for Claude specifically — a documented, open
  assumption, not a silent one.

**Both adapters** are currently saturated with `adapterDebugLog`/`[FV-DEBUG]`
instrumentation explicitly marked `// TEMP DEBUG — remove after diagnosis`
throughout `orchestrator.tsx` and both adapter files. This reads as an
active, unfinished debugging pass (likely for the badge-mounting issue) —
**recommend resolving and stripping this before any provider-expansion
work**, both for bundle size and because verbose per-mutation logging
in a `MutationObserver` callback is itself a real perf cost on long
conversations (Section N).

---

## G. Provider-Adapter Architecture for Expansion

Already largely correct — no rewrite needed, and the brief explicitly says
not to reinvent this. What's already in place, verified:

```
ProviderAdapter (apps/extension/src/adapters/types.ts)
  .matches(hostname): boolean
  .findMessages(root): HTMLElement[]
  .extractText(messageEl): string
  .isStreaming(messageEl): boolean
  .findToolbar(messageEl): HTMLElement | null
  .mountPoint(messageEl): HTMLElement
  .verified: boolean
```

`resolveAdapter()` in `registry.ts` already refuses unverified adapters
outside an explicit dev-only `allowUnverified` flag. `manifest.json`
already scopes `content_scripts.matches` to only the two live providers.
Gemini/Copilot/Perplexity are already `createUnverifiedStub()` shells.

**Recommended additions, not replacements:**
1. Add the DOM-exclusion guard from Section E.4 to the *shared* layer
   (`domUtils.ts`) so every future adapter gets it for free, rather than
   relying on each adapter's toolbar geometry happening to be safe.
2. Add a per-adapter streaming-timeout cap in the orchestrator (shared,
   not per-adapter) so a permanently-false-positive `isStreaming()` can't
   silently starve a message of verification forever.
3. Fix the hardcoded `model_source` (Section H) by threading the resolved
   adapter's `id` into `engineInstance.ts` instead of a literal string.
4. For each new provider (Gemini/DeepSeek/Perplexity), the *process* the
   Claude adapter's header comment documents (cite sourcing, don't flip
   `verified` without a live pass) is exactly right and should be
   followed — but per the brief's constraint, this audit does not invent
   selectors for markup it hasn't inspected live. All three remain
   correctly marked `UNVERIFIED / EXPERIMENTAL` (i.e., left as
   `createUnverifiedStub()`) until that pass happens.

---

## H. Reliability & Concurrency Audit

**Verified working correctly:**
- Cancellation: `VerificationSession.cancel()` aborts only
  *self-owned* controllers (`ownedControllers`), explicitly documented as
  necessary because dedup is engine-wide — cancelling session A must not
  break session B's await on the same in-flight deduped request. This is
  correct and non-obvious; whoever wrote `session.ts`'s
  `getOrCreateDeduped` understood the sharp edge here.
- Debouncing: `scheduleScan()` coalesces mutation floods into one scan per
  animation frame via a `scheduled` boolean guard.
- Redundant re-render guard: `updateEntry()` bails if `text ===
  entry.lastText`.
- Stale-result handling: `verifyOne()` checks `this.cancelled` both before
  emitting a result and inside the fallback path, so a session that moved
  on can't clobber newer state.
- Retry: `withRetry()` only retries `TransportError`s marked `retryable`
  (429/5xx), with exponential backoff + jitter, and immediately aborts on
  `cancelled`. Non-`TransportError` throws are *not* retried — reasonable
  default (unknown errors could be non-idempotent bugs, not transient
  network issues) but worth a one-line comment since it's a slightly
  surprising choice (`retry.ts` currently treats unknown errors as
  "assume transient" in the comment, which actually contradicts "isn't
  retried" — re-reading: `retryable = isTransportError ? err.retryable :
  true` — **correction**: unknown errors ARE retried (`true` by default).
  Documented in-code, consistent, not a bug — flagged only because the
  first read is easy to get wrong).

**Real gaps:**
1. **Hardcoded `model_source`** (`engineInstance.ts:
   createChromeTransport("chatgpt.com")`) — confirmed live bug, not
   provider-specific despite the engine/adapter system otherwise being
   fully provider-agnostic. Every claim verified on claude.ai is currently
   tagged as having come from `chatgpt.com` in the backend's
   `model_source` logging (`main.py:386-387`), which will corrupt any
   future per-provider analytics and (per Section C.2) has a plausible
   path to affecting `resolve_provider_tier`'s name-substring matching if
   that function is ever extended to special-case model sources.
2. **No batch endpoint usage.** `/v1/verify/batch` exists on the backend
   (`main.py:421`, `core/engine.py::verify_batch`) and is unused by the
   extension, which instead fires one HTTP round-trip per claim (bounded
   by `concurrency` — default 3, `VerificationEngine`'s
   `DEFAULT_CONCURRENCY`). For a 17-claim message this is up to 17
   separate request/response cycles through content script → background →
   network → background → content script, each independently subject to
   the messaging round-trip cost. Batching would reduce backend load and
   perceived latency, especially relevant given the audit's own concern
   about "the system should never accidentally verify the same claim
   dozens of times because an LLM streamed its response character by
   character" — dedup handles *identical* claims, but doesn't reduce the
   request *count* for 17 genuinely distinct claims in one message.
3. **Streaming-timeout cap**: not found in the files reviewed (Section F).
4. **Verbose debug logging in the hot path**: `adapterDebugLog` is called
   on essentially every step of every scan, inside a `MutationObserver`
   callback that fires on `childList + subtree + characterData` across
   `document.body`. Confirm whether `adapterDebugLog` is a no-op in
   production builds (**UNVERIFIED** — did not locate a build-time strip
   or `DEBUG` env gate in `adapters/shared/log.ts` at the depth reviewed;
   worth confirming before shipping, since this is a real perf cost if it
   isn't gated).

---

## I. Backend/API Integration Audit

Actual current contract for `/v1/verify` (**VERIFIED**, `main.py:368-418`):

Request: `{question: str, raw_value: float, model_source?: str}` (+ optional
`X-FinVerify-Key` header, logged but **explicitly not enforced** — the
endpoint's own docstring says so).

Response: `{question, raw_value, verified_value, correction_applied,
trust_score, trust_color, delta_pct, dvl_version, timestamp}` — matches
`packages/core/src/types.ts::V1VerifyResponse` field-for-field; no schema
mismatch found between the two.

Findings:
- **No authentication is enforced** on `/v1/verify` beyond an optional,
  unchecked header — anyone can call this endpoint directly (it's a public
  HF Space URL, hardcoded in `http-transport.ts`), independent of the
  extension.
- **Rate limiting exists** (`SlowAPIMiddleware`, 100 req/min per IP per the
  endpoint docstring) but is conditionally attached only
  `if RATE_LIMITING_AVAILABLE and _limiter is not None` — **UNVERIFIED**
  whether that condition reliably holds in the deployed environment;
  worth an explicit health-check assertion rather than a silent optional.
- **CORS**: `allow_origins` is read from `CORS_ORIGINS` env var, split on
  commas, with `allow_credentials=True` and `allow_headers=["*", ...]`.
  If `CORS_ORIGINS` is unset or misconfigured to include a wildcard
  alongside `allow_credentials=True`, that's a real CORS
  misconfiguration risk (browsers reject `*` + credentials, but a
  misconfigured explicit-origin list that's too broad, e.g. including a
  dev URL in production, would not be caught by that browser-level
  safeguard) — **UNVERIFIED without reading the deployed env config**,
  flagged as needing a live check, not asserted as broken.
- **No API client abstraction is needed beyond what exists.**
  `VerificationTransport` (packages/core) already *is* that abstraction,
  cleanly separating transport from verification logic — recommend against
  adding another layer here.
- **`/v1/verify/batch` exists and is unused** (Section H.2).

---

## J. UI/UX Audit & Redesign Direction

The current `VerificationCard.tsx` (apps/extension) is already a
substantial, thoughtful redesign (per its own doc comments, a recent
`feat/finverify-ui` merge) — terminal-dark aesthetic, segmented confidence
meter, collapsible sections, offline-estimate visual distinction
(dashed border + "OFFLINE" chip), accessible live regions, keyboard
support (Escape), portal-based floating panel clamped to viewport. This is
not what needs rebuilding; the *data* it's fed needs fixing (Section C/D).

Concrete, implementable recommendations once Section D's schema lands:

1. **Split the hero stat.** Replace the single `ConfidenceMeter` with two
   numbers when `unverified` claims exist: "N confirmed" (from real
   evidence) and "M unverified" (no evidence available), never averaged
   into one percentage. Only show a percentage meter when *all* verified
   claims actually have `verification_status !== "unverified"`.
2. **Rename "confidence" to something that can't imply false precision**
   when the underlying signal is categorical — e.g. "Evidence coverage" or
   simply drop the meter to a coverage bar (`X/Y corroborated`) rather
   than a percentage, for exactly the cases the brief warns about
   ("if there is insufficient evidence for a numerical score, recommend
   showing an appropriate state instead of manufacturing precision").
3. **Analyst summary copy already does most of this well** —
   `deriveAnalystSummary`'s branching text ("N matched the reported figure
   exactly but couldn't be corroborated...") is honest and specific. The
   bug isn't the copy, it's that the copy sits next to a misleading number.
   Once `unverified` is a first-class status, the copy and the number will
   finally agree.
4. **"Key Financial Metrics" section** should visually separate
   `verified`/`contradicted` rows from `unverified` rows (distinct section
   or a clear inline marker), rather than the current single
   `visibleMetrics` list where a corroborated $4.2B revenue figure and an
   uncorroborated 20%-ambiguous margin figure render identically.
5. Everything else (loading/pending states, error states, empty state,
   expandable raw-claims list, responsiveness via `92vw` max-width,
   `68vh` max-height scroll) is already reasonable and doesn't need
   redesign.

---

## K. Security/Privacy Audit

**Confirmed (P0):**
- `GET /v1/history/{user_id}`, `POST /v1/history`, `DELETE
  /v1/history/{user_id}` (`main.py:693-751`) take `user_id` as a bare
  path/body parameter with **no check that the requester is authorized for
  that `user_id`**. Any caller who knows or guesses a `user_id` can read,
  overwrite, or delete another user's verification history. This is not
  used by the extension's current code paths reviewed, but it's live on
  the same backend the extension talks to and is reachable by anyone.
- `/v1/verify`'s `X-FinVerify-Key` is accepted, logged, and **explicitly
  documented as not enforced** — there is effectively no authentication on
  the verification endpoint itself.

**Extension-side, reviewed:**
- `manifest.json` permissions are minimal and appropriate: `["storage"]`
  only, `host_permissions` scoped to exactly the one backend origin. No
  `<all_urls>`, no `tabs`, no `webRequest`. This is good practice.
- No API keys or secrets found hardcoded in the extension source reviewed.
- Content sent to the backend is the *extracted claim* (a short sentence +
  matched number), not the full conversation — reduces, but does not
  eliminate, exposure of potentially sensitive user-typed financial
  figures to a third-party (Anthropic/OpenAI-external) backend; worth a
  privacy-policy-level acknowledgment if not already present (not
  reviewed — outside repo scope).
- No unsafe `dangerouslySetInnerHTML`/`innerHTML` assignment found in the
  UI files reviewed (`VerificationCard.tsx`, `InlineBadge.tsx`) — all
  dynamic content goes through JSX text interpolation, which is
  XSS-safe by default.
- **CORS `allow_credentials=True` + externally-configured `allow_origins`**
  is a live pattern worth a deployment-config check (Section I).

---

## L. Testing Strategy

**Exists (VERIFIED, `packages/core/test/`):** `engine.test.ts`,
`session.test.ts`, `retry.test.ts`, `finance-detect.test.ts`,
`finance-plugin.test.ts`, `registry.test.ts`, `http-transport.test.ts`,
`trust.test.ts`, `events.test.ts`. Plus `apps/extension/e2e/
verification.spec.ts` and `performance.spec.ts` (Playwright).

**Missing (confirmed by absence, not by exhaustively reading every test
file's assertions):**
1. **No test anywhere covers `VerificationCard.tsx`'s `trustWeight` /
   `deriveAnalystSummary` / `deriveOverallStatus`.** This is the exact
   function that produces the reported bug, and it currently has zero
   coverage. This should be the first test written, before any fix lands,
   specifically as a regression fixture:
   ```ts
   // 17 claims, all status="verified", all result.trust_score="LOW",
   // all result.correction_applied=null (i.e. "matched exactly")
   // → today: confidencePercent === 20
   // → after fix: should not render a misleading single percentage at all
   ```
2. No adapter-level DOM fixture tests (ChatGPT/Claude realistic markup
   snapshots) — the audit's requested regression coverage for "brittle
   selectors" doesn't exist yet; `e2e/fixtures` exists but wasn't
   confirmed to contain provider DOM snapshots specifically (only
   partially reviewed).
3. No test asserting the DOM-exclusion behavior from Section E.4, because
   the behavior doesn't exist yet.
4. No test for the overlapping-claim-pattern duplication in Section G.1.

---

## M. Performance

Not deeply profiled (out of scope for a static read), but structurally:
- `MutationObserver` on `document.body` with `{childList: true, subtree:
  true, characterData: true}` plus a `setInterval(4000ms)` belt-and-braces
  fallback is a reasonable pattern; `characterData: true` is specifically
  justified in-code for streaming renderers that mutate text nodes
  directly, which is a real and correct concern, not over-engineering.
- The verbose per-mutation `[FV-DEBUG]` logging (Section H.4) is the most
  concrete, easily-fixed performance risk found — confirm it's stripped
  or gated in production builds.
- One HTTP round-trip per distinct claim (Section H.2) scales linearly
  with claim count and is the main lever for reducing both backend load
  and perceived latency on long, number-dense responses.

---

## N. File-by-File Change Plan (Phase 1–2 scope only; full list in Section P)

| File | Current responsibility | Problem | Recommended change | Why | Risk |
|---|---|---|---|---|---|
| `finverify-terminal/backend/core/trust_engine.py` | Rule-based trust label derivation | `EvidenceTier.USER` (no evidence) silently falls through to the same `LOW` default used for contradicted evidence | Add an explicit "no evidence" branch producing `verification_status="unverified"`, `trust_score="N/A"`, distinct from a rule-matched contradiction | Root cause of the 20% bug; the label conflation happens here first | Low — additive, existing rules unaffected |
| `finverify-terminal/backend/app/main.py` (`v1_verify_endpoint`) | Builds `V1VerifyResponse` | Drops `TrustScore.score` (float) and `.reasons` before responding | Add `confidence: float`, `verification_status`, `reasons: list[str]` to the response model | Frontend has nothing but a 3-value label today | Low — additive fields, backward compatible if old fields kept |
| `packages/core/src/types.ts` | Mirrors backend contract | Missing `verification_status`/`confidence`/`reasons` | Extend `V1VerifyResponse`, add `VerificationStatus` type (Section D) | Type-level fix required before UI can consume the new fields | Low |
| `apps/extension/src/ui/VerificationCard.tsx` | Aggregation + rendering | `trustWeight()`/`confidencePercent` averages a flat scale that includes `unverified` claims as if they were low-scoring verified ones | Exclude `unverified` claims from the numeric average; render a separate "N unverified" count; only show a percentage meter when all claims have real evidence | Directly fixes the reported symptom | Medium — touches the most user-visible component; needs the regression test in Section L.1 written first |
| `apps/extension/src/engineInstance.ts` | Wires transport into the engine | `createChromeTransport("chatgpt.com")` hardcoded | Pass the resolved adapter's `id` (from `resolveAdapter()`) instead of a literal | Live provenance bug on claude.ai | Low |
| `apps/extension/src/adapters/shared/domUtils.ts` | Shared DOM helpers | No exclusion of FinVerify's own injected DOM before text extraction | Add a shared `stripFinVerifyDom(el)` helper; call it from both adapters' `extractText()` | Closes the self-observation risk (Section E.4) before it's ever triggered by a markup change | Low |
| `packages/core/src/plugins/finance/detect.ts` | Claim regex + normalization | Cross-pattern duplicate matches on overlapping substrings; no `trillion`/`T` scale | Dedup by normalized numeric value + sentence + offset range overlap, not exact substring; add `trillion`/`T` to `SCALE_MAP` | Reduces inflated claim counts and redundant metric rows | Medium — touches a well-tested file; needs new tests for overlap cases before changing dedup logic |
| `apps/extension/src/content/orchestrator.tsx` | Scan/mount/lifecycle | `[FV-DEBUG]` logging on every mutation; no confirmed streaming-timeout cap | Strip or env-gate debug logging; add a max-wait cap before treating `isStreaming()===true` as stuck | Perf + reliability | Low–Medium |
| `finverify-terminal/backend/app/main.py` (`/v1/history/*`) | User history CRUD | No authorization binding caller to `user_id` | Require and verify a session/auth token matching `user_id` before serving/mutating history | Confirmed IDOR | Medium — needs an actual auth mechanism, likely larger than this audit's scope to fully design; flag for a dedicated security fix, not bundled into the trust-score fix |

Section T below expands Phase 1 (the trust/status model — the highest-value,
most self-contained fix) into a full Codex-ready spec. Phases for claim
extraction, provider expansion, and the history-endpoint auth fix are
scoped but intentionally left less detailed here, since the brief asks for
the *first* implementation batch to be the most actionable one.

---

## O. Implementation Order

```
Phase 0 — Regression fixture for the 20% bug (Section L.1), written against
           current behavior, currently failing/red for the "should not
           show a misleading single percentage" assertion.
Phase 1 — Backend trust/status model: trust_engine.py + main.py response
           schema (Section N rows 1–2).
Phase 2 — Frontend types + VerificationCard consumption of the new schema
           (Section N rows 3–4).
Phase 3 — engineInstance.ts model_source fix (independent, can land any time).
Phase 4 — Shared DOM-exclusion guard in domUtils.ts (independent, can land
           any time, high value/low risk).
Phase 5 — Claim-extraction dedup + trillion scale fix, with new tests first.
Phase 6 — Strip/gate [FV-DEBUG] logging; add streaming-timeout cap.
Phase 7 — /v1/history authorization fix (separate security-focused change,
           likely needs its own review — do not bundle with Phase 1–2).
Phase 8 — UI polish per Section J once Phase 2 data is available.
Phase 9 — Provider expansion (Gemini/DeepSeek/Perplexity), only after a
           live-DOM verification pass per docs/adding-a-provider.md —
           out of scope for this audit to pre-write selectors for.
```

This differs from the brief's example ordering mainly in putting the
trust/status model (Phase 1–2) before the reliability layer and provider
work, since it's both the most concretely-reported bug and the smallest,
most self-contained change — everything else in this codebase is in
reasonable shape and doesn't block on it.

---

## P. Codex Implementation Specification — Phase 0–2 (first batch)

This is the batch that should be implemented first; it's scoped tightly
enough to execute without further architectural questions.

### Phase 0 — Regression fixture

**Objective:** lock in current (buggy) behavior with a failing test that
defines the fix.

**Files to create:**
- `apps/extension/src/ui/__tests__/VerificationCard.test.tsx` (new —
  no test file currently exists for this component)

**Behavior requirements:**
- Construct a `VerifiedClaim[]` of 17 items, `status: "verified"`, each
  `result.trust_score: "LOW"`, `result.correction_applied: null`,
  `result.raw_value === result.verified_value` (i.e. "matched exactly").
- Assert `deriveAnalystSummary(claims).confidencePercent === 20` (documents
  current behavior — this assertion should be **deleted**, not weakened,
  once Phase 2 lands, and replaced with the Phase 2 acceptance criteria
  below).

**Acceptance criteria:** test exists, passes against current code,
demonstrates the exact reported numbers (17 claims, 20%).

**Dependencies:** none. **Must NOT change:** any non-test file.

### Phase 1 — Backend trust/status model

**Objective:** stop encoding "no evidence" and "evidence contradicts" as
the same label.

**Files to modify:**
- `finverify-terminal/backend/core/models.py` — add `class
  VerificationStatus(str, Enum): VERIFIED = "verified"; CONTRADICTED =
  "contradicted"; UNVERIFIED = "unverified"`. Add `status:
  VerificationStatus` and `score: float | None` and `reasons: list[str]`
  fields to whatever model currently carries `TrustScore` through to the
  API boundary (confirm exact model name by reading `build_result()` in
  `backend/core/output.py`, not yet reviewed in this pass — **Codex should
  read this file before implementing**, as it's the function that shapes
  `VerificationResult` from `TrustScore`).
- `finverify-terminal/backend/core/trust_engine.py` — in `derive_label()`,
  before falling through to `DEFAULT_LABEL`, add an explicit check: if
  `findings.evidence_tier == EvidenceTier.USER` (no evidence resolved),
  return a distinct outcome — `label="N/A"`, `score=None`,
  `status=VerificationStatus.UNVERIFIED`, `reason="No independent evidence
  available"` — rather than falling into the same tuple used for a rule
  match. Existing rule matches for PRIMARY/SECONDARY tiers are unaffected;
  this only changes the *default fallback* path.
- `finverify-terminal/backend/app/main.py` (`v1_verify_endpoint`) — thread
  the new `status`/`score`/`reasons` fields into `V1VerifyResponse`.
- `finverify-terminal/backend/app/models.py` — extend the
  `V1VerifyResponse` Pydantic model with the three new fields (all
  additive; keep `trust_score`/`trust_color` as-is for backward
  compatibility with any other client of this public API).

**Edge cases:**
- A claim that has `EvidenceTier.USER` **and** a correction was applied
  (e.g. an obvious scale fix with no ground truth) should still be
  `UNVERIFIED`, not `VERIFIED` — a correction based on a heuristic, not
  evidence, is not corroboration. Do not conflate "we fixed the scale"
  with "we confirmed the value."
- `ambiguous=True` cases in the legacy `dvl.py::verify_canonical` path
  (still called from somewhere — confirm callers before this phase, since
  it appears to be a parallel/older code path to `core/engine.py::verify`;
  **Codex should grep for all callers of both `compute_trust` functions
  and `verify_canonical` before changing either**, to avoid fixing one
  path and leaving a second, still-live path with the old conflation).

**Tests required:** unit test in the backend test suite (`backend/core`
or equivalent) asserting: no-evidence input → `status="unverified"`,
`score is None`, `trust_score in ("N/A",)`; PRIMARY-tier no-correction
input → unaffected, still `status="verified"`, `trust_score="HIGH"`.

**Acceptance criteria:** existing backend tests still pass; new test
covers the no-evidence path; `V1VerifyResponse` includes the three new
fields without removing any existing field.

**Must NOT change:** the shape or values of `trust_score`/`trust_color`
for any input that currently resolves through an explicit `TRUST_RULES`
match (PRIMARY/SECONDARY-tier cases) — only the default-fallback path
changes.

### Phase 2 — Frontend consumption

**Objective:** stop averaging unverified claims into a fake percentage.

**Files to modify:**
- `packages/core/src/types.ts` — add `VerificationStatus` type and the
  three new fields to `V1VerifyResponse` (mirroring Phase 1 exactly, per
  this file's own "do not drift from backend" doc comment).
- `apps/extension/src/ui/VerificationCard.tsx`:
  - `deriveAnalystSummary()`: partition `verified` claims into those with
    `result.verification_status !== "unverified"` (call these
    `corroborated`) and those with `=== "unverified"`. Compute
    `confidencePercent` **only** over `corroborated` (existing
    `trustWeight` logic is fine to keep for HIGH/MEDIUM/LOW *within* that
    set — those distinctions remain meaningful once "no evidence" is no
    longer forced into `LOW`). Add `uncorroboratedCount` to
    `AnalystSummary`.
  - `VerificationCard`'s hero section: if `corroborated.length === 0` and
    `uncorroboratedCount > 0`, render a coverage statement ("0 of 17
    claims could be independently corroborated") instead of
    `ConfidenceMeter` — do not show a percentage with no real information
    behind it (this is the direct fix for "manufactured precision," per
    the brief's explicit constraint).
  - `flaggedForReview` filter (`c.result?.trust_score === "LOW"`) should
    become `c.result?.verification_status === "contradicted"` — LOW no
    longer means "flag this," since LOW will now only occur for
    rule-matched contradictions/low-confidence corrections, not
    no-evidence cases (which get their own `unverified` bucket, shown
    separately, not as an "issue").

**Edge cases:**
- Mixed messages (some corroborated, some not) must show both numbers,
  not just the corroborated percentage with unverified claims silently
  dropped from the count entirely — the existing `summary.total` /
  `summary.unavailable` pattern in the analyst-summary paragraph already
  has the right shape for this; extend it, don't replace it.
- Offline-fallback claims (`claim.error` set, `financeOfflineFallback()`
  result) should remain visually distinct as `OFFLINE` and should **not**
  count as `corroborated` regardless of their fallback `trust_score`,
  since they were never sent to the backend at all.

**Tests required:** update `VerificationCard.test.tsx` from Phase 0 —
change the assertion from `confidencePercent === 20` to: `corroborated
.length === 0`, `uncorroboratedCount === 17`, and (component-level) assert
the rendered output does **not** contain a `%`-suffixed confidence number
for this fixture. Add a second fixture mixing corroborated + uncorroborated
claims and assert both counts render correctly.

**Acceptance criteria:** Phase 0's fixture no longer shows a misleading
20% figure; a corresponding "real evidence found" fixture (PRIMARY tier,
no correction) still shows a 100%-equivalent HIGH confidence meter,
unchanged from current behavior.

**Dependencies:** Phase 1 must land first (or be mocked in frontend tests
against the new schema shape).

**Must NOT change:** `trustPalette`/`trustIcon`/`trustLabel` in
`packages/core/src/trust.ts` — these are pure presentation helpers, still
correct for whatever `trust_score` a corroborated claim carries, and are
shared with `finverify-terminal/frontend/public/widget.js` per that file's
own doc comment (changing them here would need a parallel change there,
out of scope).

---

## What Codex Should Implement First

**Phase 0 + Phase 1**, in that order, as one PR-sized unit.

**Reasoning:** Phase 0 is a five-minute, zero-risk test that pins down
exactly what "the bug" means in code, not just in a screenshot — this
matters because the audit found the bug is a *systemic default*, not a
rare edge case, and a regression test is the cheapest way to make sure the
eventual fix actually changes the number instead of just changing how it's
displayed. Phase 1 is the actual root-cause fix, entirely backend-side,
additive to the API contract (no breaking change to any other consumer of
`/v1/verify`), and self-contained enough to land, test, and deploy
independently of any frontend change — the frontend will simply keep
computing `confidencePercent` from `trust_score` exactly as it does today
until Phase 2 lands, so Phase 1 alone is safe to ship first and observe.

**Acceptance criteria for this first batch:**
1. Phase 0's test file exists and documents current behavior.
2. A no-evidence `/v1/verify` call (the extension's actual current usage
   pattern — no ticker/entity) returns `verification_status="unverified"`,
   `score=None`, distinct from a call where evidence was found and
   genuinely contradicted the claim.
3. All existing backend tests still pass unmodified.
4. No frontend file is touched in this batch — Phase 2 is a separate,
   reviewable unit.

Phase 2 (frontend) should follow immediately after in a second PR, using
the exact plan above — at which point the reported "17 claims / 17
matched / 20% LOW CONFIDENCE" screenshot should no longer be reproducible,
and Section C.4's open question (the duplicate 20%/$383.3B metric rows)
should be re-examined against real data before deciding whether it needs
its own fix or was a coincidental transcript pattern.
