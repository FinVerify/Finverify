# FINVERIFY — UNIVERSAL VERIFICATION ENGINE AUDIT

Repository audited: `aadityat23/finverify-llm` (default branch, cloned fresh for this audit).
Scope: `finverify-extension/` (browser extension + `@finverify/core`) and `finverify-terminal/backend/` (FastAPI service).
No files were modified. Every finding below is either **FACT** (verified by reading the file/function named), **INFERENCE** (a conclusion drawn from facts, clearly derived), or **RECOMMENDATION** (a proposed change, not yet in the code). Where the codebase's own comments/docstrings already state a fact, that is quoted/cited as FACT, not treated as opinion.

---

## 1. EXECUTIVE SUMMARY

FinVerify's Phase 0–2 fix was correct: it stopped fabricating 20% confidence for claims with no evidence. But it also exposed the real problem, and this audit's central finding is sharper than the brief anticipated:

> **Even where the extension successfully reached the backend's strongest evidence provider, the current `/v1/verify` code path has no step that compares the claimed number to the evidence's number.**

This is not a hypothetical gap. It is directly confessed in the codebase itself:

```
scripts/verify_transcript.py (module docstring):
"core.engine.verify()'s own `verified` field is true whenever a numeric
value survived DVL formatting -- it does NOT mean the number was checked
against real evidence (the math engine never compares evidence.value to
the claim's value; only ConstraintVerifier cross-checks metrics against
each other, and evidence-tier only reflects "did SOME primary source
respond for this ticker", not "does it match THIS claim")."
```

That comment describes `core/engine.py::verify()` exactly as it exists today, and `/v1/verify` (`app/main.py::v1_verify_endpoint`) calls that exact function. The module that *does* perform value+concept+period identity matching — `core/identity_verification.py` — exists, is well-designed, is unit-tested (`tests/test_period_compatibility.py`), and is used by exactly one caller in the whole repository: `scripts/verify_transcript.py`, an offline CLI script. It is never imported by `app/main.py`, `core/engine.py`, or `core/trust_engine.py`.

Layered on top of that gap is the context-loss problem the brief described: the extension's `V1VerifyRequest` (`{question, raw_value, model_source?}`) never carries entity, ticker, metric, or period, so even if `verify()` did call `identity_verification.py`, it would have nothing to resolve against. The backend does have real entity/metric/period resolution (`core/financial/company.py::resolve_company`, `core/financial/concepts.py::ConceptRegistry`, `core/financial/period.py`) — but `core/engine.py::verify()` uses a much weaker, uppercase-regex resolver (`core/resolvers.py`) instead of any of them.

So there are two separable, both-necessary fixes, and they are independent of each other:

1. **Get identity fields to the backend at all** (extension: extract entity/metric/period from context; transport: carry them in the request; backend contract: accept them in `V1VerifyRequest`/route them into a `Claim`).
2. **Get the backend to actually check the number** (`core/engine.py::verify()` must call `core/identity_verification.py`'s concept+period+value comparison — today it doesn't, for *any* caller, batch or single).

Fix #2 is more urgent and more self-contained: it requires no extension changes and is a pure backend wiring change, reusing code that already exists and is tested. Fix #1 is what makes fix #2 actually fire for real chat claims instead of falling back to `EvidenceTier.MODEL`/`UNVERIFIED` every time (because `providers/sec.py::SECProvider.can_handle()` requires `claim.entity.ticker`, which nothing currently populates for extension traffic).

This report traces both gaps file-by-file, inventories what already exists and can be reused, and lays out the recommended order of work. **Nothing here should be read as "add more green checks."** The goal stated in the brief — VERIFIED must mean entity+metric+period+scale+value were positively matched to independent evidence — is not met today even in the best case (a fully-formed, correctly-resolved SEC-backed claim), because the comparison step that would make VERIFIED mean that is not wired in. Fixing the wiring will, correctly, turn some claims that are *currently silently mislabeled* (see §4) into CONTRADICTED, and will keep most currently-UNVERIFIED claims UNVERIFIED until context flows through. That is the intended, correct outcome.

---

## 2. CURRENT RUNTIME ARCHITECTURE (CODE-TRACED)

Trace of a claim from ChatGPT/Claude DOM to `VerificationCard`, file by file.

### 2.1 Provider adapters — `apps/extension/src/adapters/{chatgpt,claude}/index.ts`

- **FILE/FUNCTION:** `chatgptAdapter.extractText(messageEl)` (and the structurally identical `claudeAdapter.extractText`).
- **INPUT:** an assistant message DOM node, found via `MESSAGE_SELECTORS` (`[data-message-author-role="assistant"]`, etc.) with a semantic-DOM fallback (`findSemanticTurnCandidates`).
- **OUTPUT:** `(messageEl.innerText || messageEl.textContent || "").trim()` — a plain string, the assistant's answer text only.
- **FIELDS PRESERVED:** raw text of the assistant turn.
- **FIELDS LOST:** everything else. The adapter interface (`ProviderAdapter` in `adapters/types.ts`) has no method that extracts the *user's* preceding question, the conversation title, the model name/version actually rendering (e.g. "GPT-4o" vs "GPT-4o mini" — ChatGPT exposes this in its UI), the page URL, or any surrounding table/citation DOM. `SEMANTIC_USER_TURN_SELECTOR` exists in `chatgpt/index.ts` but is used only to help *locate* the assistant-turn container structurally (`findSemanticTurnCandidates`) — its matched user-turn text is never read into a string and never passed downstream.
- **FIELDS FABRICATED:** none.
- **FIELDS AVAILABLE BUT UNUSED:** the user's question (adjacent DOM node, matchable via `SEMANTIC_USER_TURN_SELECTOR`), page `location.hostname` (used only for `adapter.matches()`, not forwarded), and, on ChatGPT specifically, the model-name label visible in the UI.

### 2.2 Claim detection — `packages/core/src/plugins/finance/detect.ts::detectFinanceClaims()`

- **INPUT:** the plain assistant-text string from §2.1.
- **OUTPUT:** `ExtractedClaim[]`, each `{ id, domain, sentence, raw_value, claim_type, match, offset, bps_original?, scale_label? }` (`packages/core/src/types.ts:43-64`).
- **HOW:** splits text into sentences (`splitSentences`, a `.`/`!`/`?`+uppercase or newline heuristic), then runs 12 ordered regexes (`CLAIM_PATTERNS`, lines 26-39) per sentence — currency, currency_raw, percentage, bps, growth_pct, decline_pct, shares, eps, margin, revenue, ratio, return_metric.
- **FIELDS PRESERVED:** the matched sentence (truncated to 200 chars), the raw numeric value (scale-multiplied for `billion`/`million`/`thousand`/`B`/`M`/`K`/`bn`/`mn`; bps divided by 100), the matched substring, its character offset in the full text, and a coarse `claim_type` string.
- **FIELDS LOST:** entity/company name (even when it appears in the very same sentence — e.g. "Apple reported revenue of $109.42B" — the regex only ever captures the number and its immediate scale word, never the subject of the sentence), fiscal period (even "Q3 FY2026" in the same sentence is discarded), currency (assumed always USD via the `$` in the regex; a EUR/GBP figure would either not match at all or match a wrong pattern), comparison period for growth/decline claims (`growth_pct`/`decline_pct` capture only the delta number, never "from $94.04B" or "vs. Q3 FY2025"), and any table/paragraph context beyond the single sentence.
- **FIELDS FABRICATED:** none — this module is honest about what it doesn't know; it just doesn't try to know it.
- **EXISTING CAPABILITY THAT CAN BE REUSED:** the file's own header comment states this is "a TypeScript port of `finverify-terminal/backend/ingestion/transcripts.py::extract_claims()`" and instructs "if the backend patterns change, mirror the change here too." Confirmed: `ingestion/transcripts.py`'s `CLAIM_PATTERNS` (same 12, plus the phase-7A backtracking bug-fix comment for the standalone-`$`-amount pattern, `ingestion/transcripts.py` lines ~60-85) is the source of truth. **Divergence found:** the extension's `currency_raw` regex (`/\$\s*([\d,.]+)(?!\s*(?:billion|...))/gi`) does not visibly carry forward the backtracking guard the backend comment describes fixing for "$511 million"-style inputs; this should be verified against the current backend regex character-for-character before Phase 3 ships (P2, not blocking, listed in §23).

### 2.3 Question building — `packages/core/src/plugins/finance/index.ts` + `detect.ts::buildFinanceQuestion()`

- **INPUT:** `Pick<ExtractedClaim, "claim_type" | "bps_original" | "raw_value">`.
- **OUTPUT:** one of 10 hardcoded generic strings, e.g. `"What was the revenue figure?"`, `"What was the financial value in the statement?"`, and — for anything not matching a known `claim_type` — the catch-all `"What was the financial value?"` (line 156). This is the literal string the Phase-0-2 fix report already flagged.
- **FIELDS LOST:** entity, period, and the original sentence are all *available on the claim object passed in* (it's typed `Pick<ExtractedClaim, ...>` deliberately excluding `sentence`, `id`, `domain`, `match`, `offset` — i.e. the function signature itself throws these away before the question is even built). This is a second, independent place semantic context is dropped, on top of extraction already having lost it.

### 2.4 Session / transport — `packages/core/src/session.ts::verifyOne()` → `getOrCreateDeduped()` → `http-transport.ts`

- **FILE/FUNCTION:** `VerificationSession.verifyOne(claim)` (`session.ts:93-117`).
- Calls `plugin.buildQuestion(claim)` → `question`, then `getOrCreateDeduped(question, claim.raw_value)` (`session.ts:163-175`).
- **Dedup key:** `` `${question}|${rawValue}` `` — literally the generic question string plus the number. **This means two different companies' claims with the same generic question and the same numeric value are the same cache key and get merged into one network request and one shared result.** E.g. any two `"What was the revenue figure?"` claims worth exactly `109420000000` — regardless of company or period — dedup to one `/v1/verify` call and one shared `VerifiedClaim` result object delivered to both. Given the current payload has no entity/period to distinguish them anyway, this is *consistent* with today's semantics, but it is a landmine for Phase 3: once entity/period are added to the claim, the dedup key **must** be updated to include them, or the fix in §4 will be silently defeated by cache collisions across companies/periods that happen to share a value.
- **Transport call:** `this.deps.transport.verify({ question, raw_value: rawValue }, ...)` (`session.ts:172`). **`model_source` is never set anywhere in the traced path** — `VerificationTransport.verify()`'s request type is `V1VerifyRequest` which has an optional `model_source`, but no caller in `session.ts`, `engine.ts`, or `InlineBadge.tsx` ever populates it. It is dead-on-arrival: defined in the contract, never filled in production.
- **HTTP:** `http-transport.ts::createHttpTransport().verify()` POSTs `JSON.stringify(request)` to `${baseUrl}/v1/verify` (`http-transport.ts:50-51`), `baseUrl` defaulting to `https://aadi2026-finverify-api.hf.space`. Confirms the actual wire payload is exactly `{question, raw_value}` (no `model_source` in practice).

### 2.5 UI orchestration — `apps/extension/src/ui/InlineBadge.tsx`

- **INPUT:** `text` prop (assistant message text, streamed).
- Calls `engine.detectClaims(text)` (`InlineBadge.tsx:82`) then `session.verify(freshClaims)` (`InlineBadge.tsx:93`). No adapter id, page URL, or model name is threaded through here either — this confirms §2.1's finding structurally: even if an adapter *did* extract more context, `InlineBadge` doesn't currently have a slot to receive or forward it.

### 2.6 Backend endpoint — `app/main.py::v1_verify_endpoint()` (lines 368-433)

- **INPUT:** `V1VerifyRequest{question, raw_value, model_source}` (`app/models.py:78-81`).
- **Line 390:** `result = verify(Claim(question=req.question, raw_value=req.raw_value))` — **`model_source` is read only for logging (line 386-387: `logger.info("Model source: %s", req.model_source)`), never passed into the `Claim`.** No entity, metric, or period field exists on `V1VerifyRequest` to pass even if the client sent one.
- **FIELDS AVAILABLE BUT UNUSED at this exact call site:** none from the request — there's nothing left to use. The unused capability is downstream (§2.7-§2.9).
- Everything from line 391 onward (verification_status coercion to `unverified` when `evidence_tier` is `model`/`user`, delta_pct, correction_applied joining) is the Phase 0-2 logic already described in the brief and confirmed correct by this trace.

### 2.7 Core pipeline — `core/engine.py::verify()` (lines 34-68)

```
compiled = compile_claim(claim)                                   # core/compiler.py
compiled = resolve_entity(resolve_metric(resolve_time(compiled)))  # core/resolvers.py
context = VerificationContext(claim=compiled, entity=compiled.entity, ...)
evidence = evidence_retriever.retrieve(compiled, context=context)  # core/evidence.py
math_result = math_engine.run(compiled, context)                   # core/math_engine/engine.py
constraint_result = _run_constraint_verification(...)              # core/financial/constraints
trust = compute_trust(context, math_result, evidence)              # core/trust_engine.py
return build_result(...)                                           # core/output.py
```

- **`core/compiler.py::compile_claim`** (15 lines total) — trivial pass-through / dict-to-`Claim` coercion. Not where context is lost or gained.
- **`core/resolvers.py::resolve_entity/resolve_metric/resolve_time`** (39 lines total) — **this is the resolver that actually runs**, and it is far weaker than the entity/metric/period infrastructure that exists elsewhere in the same repo (see §5-§7). `resolve_entity` only fires `if claim.entity is not None: return claim` — i.e. it never overrides a client-supplied entity, but since the extension never supplies one, it always falls through to `re.search(r"\b[A-Z]{2,5}\b", claim.question)` against the **question string**, which for `/v1/verify` traffic is always one of the 10 generic templates from §2.3 (e.g. `"What was the revenue figure?"`) — none of which contain a ticker. Entity resolution silently fails for essentially all extension-originated claims today. (It would also false-positive on some questions if fed differently, e.g. matching `"EPS"` as a ticker-shaped token, if a template ever contained a bare 2-5-letter uppercase acronym — worth a regression test once real questions start flowing through.) `resolve_metric` is a 12-term substring check (`_METRIC_TERMS`) against the lowercased question — it *does* work today, weakly, because the generic templates happen to contain words like "revenue"/"margin"/"ratio". `resolve_time` regexes for a bare year or `Q[1-4] YYYY` in the question — also always fails on the generic templates, since they never contain a year.
- **`core/evidence.py::EvidenceRetriever.retrieve()`** (§2.8).
- **`core/math_engine/engine.py::MathEngine.run()`** (`math_engine/engine.py:15-45`) — runs scale/sign/magnitude *self-correction* rules against `claim.raw_value` only (via `RuleRegistry.apply(claim, context)`, `math_engine/rules/{scale,sign,magnitude}.py`). **It receives no `evidence` argument at all** — `MathEngine.run(claim, context)`, not `run(claim, context, evidence)`. It cannot and does not compare the claim's number to anything the evidence retriever found; it can only normalize the claim's own number (e.g. `0.326` → `32.6` for a percent-shaped claim). This is confirmed structurally, not just by the `scripts/verify_transcript.py` docstring quoted in §1.
- **`core/trust_engine.py::compute_trust()`** (§2.9, and see §16/§13 for the consequence).
- **`core/output.py::build_result()`** — assembles the final `VerificationResult`; not itself a source of context loss (it only shapes what upstream stages already decided).

### 2.8 Evidence retrieval — `core/evidence.py::EvidenceRetriever.retrieve()` (lines 15-59)

```python
provider = self.registry.resolve(claim)          # providers/base.py::ProviderRegistry.resolve
evidence = provider.retrieve(claim) if provider else []
if evidence: ...  return evidence
if claim.raw_value is not None:
    return [Evidence(source=Source(name=claim.model_source or "model_input", kind="model_output",
                                    authority=0.2, ...), claim=claim.question, value=claim.raw_value,
                      period=claim.period)]
return []
```

- The **only** registered provider is `SECProvider` (`providers/registry.py::default_registry()` → `ProviderRegistry([SECProvider()])`).
- `providers/sec.py::SECProvider.can_handle(claim)` — **`return bool(claim.entity and (claim.entity.ticker or claim.entity.cik))`**. Since §2.7 established `resolve_entity` essentially never populates a real ticker for extension traffic, `can_handle` returns `False`, `registry.resolve()` returns `None`, and evidence retrieval falls through to the "model_input" branch: a self-referential `Evidence` object whose `value` is literally `claim.raw_value` (the claim asserting itself), tagged `authority=0.2`, `kind="model_output"`.
- **This is the precise, traced mechanism by which "no independent evidence" happens today**, and it is a resolver-context problem, not a provider-coverage problem — the SEC ingestion pipeline itself (`ingestion/sec_edgar.py`, 537 lines, `TICKER_TO_CIK` map, `ingestion/db.py::get_fundamentals`) is real and is reachable the moment a ticker/CIK is present on `claim.entity`.

### 2.9 Trust — `core/trust_engine.py::compute_trust()` (lines 175-197)

- Calls `compute_findings()` (lines 115-132), which builds a `TrustFindings(evidence_tier=..., correction_severity=..., ambiguity=..., consistency=Consistency.PASS, rule_evidence=...)`. **`consistency` is a hardcoded literal `Consistency.PASS` at line 130 — it is never computed from anything.** `rule_evidence` comes from `_assess_rule_evidence(rule_names)` (lines 107-112), which only ever returns `NONE`/`SINGLE`/`MULTIPLE_AGREE` — **`RuleEvidence.CONFLICTING` is never returned by any function in this file** (confirmed by full-file read + `grep -rn "CONTRADICTED\|Consistency.FAIL\|RuleEvidence.CONFLICTING"` across the entire `backend/` tree outside `tests/`, which returns zero non-test matches other than the enum *definitions* themselves in `core/models.py`).
- Consequence, stated precisely: **`VerificationStatus.CONTRADICTED` is unreachable dead code on the path `app/main.py → core/engine.py → core/trust_engine.py`.** A claim can be evidence-backed by a primary source whose value flatly disagrees with the claim, and today's trust engine has no mechanism to notice — it will classify by `evidence_tier`/`correction_severity`/`ambiguity` alone (via `TRUST_RULES`, lines 22-65) and, if the tier is `PRIMARY` with no self-correction, label it `HIGH` / `VERIFIED` regardless of whether the number actually matches.
- The `test_conflicting_evidence_is_contradicted` test in `tests/test_trust_engine.py` (line 248) exists, but constructs a `TrustFindings`/`Consistency.FAIL` object directly to test `derive_label`'s dispatch — it does not exercise any code path that derives `FAIL` from real evidence, because no such code path exists. This is a real, passing test that nonetheless does not prove the system detects contradictions end-to-end.

### 2.10 `VerificationCard` (extension UI)

Renders whatever `V1VerifyResponse` says (`verification_status`, `trust_score`, `reasons`), with no independent logic of its own — confirmed by scope of `packages/core/src/session.ts::emitUpdate`/`emitFallback` and the UI layer being a pure renderer of `VerifiedClaim`. Not a source of new findings.

---

## 3. WHY CLAIMS BECOME UNVERIFIED — CAUSAL CHAIN (traced, using "Revenue was $109.42B in Q3 FY2026." as the tracing sentence; this exact structure applies to any entity/metric/period, not just this example)

```
Assistant sentence: "Apple reported revenue of $109.42B in Q3 FY2026."
  │
  ├─ detect.ts::detectFinanceClaims()
  │    → ExtractedClaim{ raw_value: 109420000000, claim_type: "revenue",
  │        sentence: "Apple reported revenue of $109.42B in Q3 FY2026.",
  │        match: "revenue of $109.42B" }
  │    entity/period discarded even though present in `sentence`.
  │
  ├─ finance/index.ts::buildQuestion() [via detect.ts::buildFinanceQuestion]
  │    → "What was the revenue figure?"     (sentence itself dropped here too)
  │
  ├─ session.ts::verifyOne() → getOrCreateDeduped()
  │    → POST /v1/verify { question: "What was the revenue figure?",
  │                          raw_value: 109420000000 }
  │    (model_source never populated)
  │
  ├─ app/main.py::v1_verify_endpoint()
  │    → Claim(question="What was the revenue figure?", raw_value=1.0942e11)
  │      (no entity/metric/period fields exist on V1VerifyRequest to carry)
  │
  ├─ core/engine.py::verify()
  │    → resolve_entity(): regex over the *question string* finds no ticker
  │      → claim.entity stays None
  │    → resolve_metric(): "revenue" substring IS in the question → metric="revenue"
  │    → resolve_time(): no year/quarter in the question → period stays None
  │
  ├─ core/evidence.py::EvidenceRetriever.retrieve()
  │    → providers/sec.py::SECProvider.can_handle(): entity is None → False
  │    → registry.resolve() → None → falls to "model_input" branch
  │    → evidence = [Evidence(source="model_input", authority=0.2,
  │                            value=109420000000, kind="model_output")]
  │
  ├─ core/trust_engine.py::compute_trust()
  │    → evidence_tier = EvidenceTier.USER (via resolve_provider_tier(),
  │      providers/base.py:24-31 — "model_input" name doesn't contain "sec"/
  │      "fred"/"dbnomics"/"model", so it falls through to the USER default)
  │    → findings.evidence_tier is USER and claim.raw_value is not None
  │      → returns TrustScore(label="N/A", status=UNVERIFIED,
  │                            reason="No independent evidence available")
  │
  └─ app/main.py:398-406
       evidence_tier in ("model","user") → verification_status forced to
       "unverified" (belt-and-suspenders on top of what trust_engine already
       decided) → this is the exact response the extension renders.
```

**Root cause, precisely stated:** the claim never carries a resolvable entity, so `SECProvider.can_handle()` never returns `True`, so real evidence is never fetched, so trust_engine correctly (per its own — currently correct — rule) reports no independent evidence. The system is not lying; it is accurately reporting that it was never given enough to check. This validates the Phase 0-2 fix's philosophy and confirms the brief's diagnosis. **What the brief did not fully capture, and this audit adds:** even after entity resolution is fixed and SEC evidence starts flowing, `core/engine.py::verify()` still would not compare the claim's `$109.42B` to whatever SEC's actual revenue figure is, because neither `MathEngine.run()` nor `compute_trust()` performs that comparison (§2.7, §2.9). Fixing entity resolution alone would make previously-`UNVERIFIED` claims become `VERIFIED` **merely because a primary source responded for the ticker**, not because the number was checked — which is arguably *worse* than the current state, since it would look like a genuine verification while still not being one. **Both gaps must be closed together, and the value-comparison gap should be closed first** (§23) because it's what makes "VERIFIED" actually mean what §16/the brief's final principle demands, and it doesn't require any extension changes to fix.

---

## 4. CURRENT CLAIM EXTRACTION CAPABILITIES

Already covered in depth in §2.2. Summary answer to the brief's specific semantic-distinction question: **no**, the current extractor does not understand the difference between `"Revenue was $109.42B"`, `"Revenue increased to $109.42B"`, `"Revenue grew from $94.04B to $109.42B"`, and `"Revenue increased 16.4% YoY"` as *related facts about one metric*. Each sentence produces independent `ExtractedClaim`s per regex match, with no notion that a `revenue` claim and a `growth_pct` claim in the same sentence describe the same underlying fact from two angles, and no capture of the comparison-period value in "grew from X to Y" (only "16.4%" or, separately, "$109.42B" would match, "$94.04B" would *also* independently match as its own `currency` claim with no link to the other two). This is the deduplication/derived-claim gap addressed in §12-§13.

**Recommended minimal canonical claim representation** (RECOMMENDATION, per brief §3's instruction to find the smallest robust shape, and matching what `core/models.py::Claim`/`BatchClaim` already define — see §22):

```
entity        (name, ticker?)      — optional, client hint only
metric        (name)               — optional, client hint only
value         (number)             — required
scale/unit    (currency/%/bps/x)   — required, deterministic from claim_type
period        (string)             — optional, client hint only
comparison_period (string)         — optional, only for growth/derived claims
claim_type    (enum, see §4b)      — required
context       (sentence, ≤200 chars) — required, replaces the generic question
```

This is deliberately close to `BatchClaim` (`core/models.py:147-165`), which already exists and is already accepted by `/v1/verify/batch`.

### 4b. Universal claim types (§4 of the brief)

Deriving from what `claim_type` values already exist in `detect.ts`/`transcripts.py` (`currency`, `currency_raw`, `percentage`, `bps`, `growth_pct`, `decline_pct`, `shares`, `eps`, `margin`, `revenue`, `ratio`, `return_metric`) plus what `VerificationStatus`/`Evidence`/math-engine rule categories (`scale_*`, `sign_*`, `magnitude_*`) already imply, the minimum useful taxonomy is:

| Claim type | Existing signal | Notes |
|---|---|---|
| REPORTED_VALUE | `currency`, `revenue`, `eps`, `shares` | direct filing/statement figure |
| GROWTH_RATE | `growth_pct`, `decline_pct` | needs a base + comparison period to be independently checkable |
| PERCENTAGE | `percentage` | ambiguous without more context — could be a margin, a rate, a share |
| PERCENTAGE_POINT_CHANGE | not currently detected | "expanded by 2.6 percentage points" is NOT matched by any current pattern — gap, see §23 P1 |
| BASIS_POINT_CHANGE | `bps` | already converts to `%`; conversion is a normalization, not a verification (§13) |
| RATIO / MULTIPLE | `ratio`, `return_metric` | `1.84x` vs `184%` ambiguity is a numeric-canonicalization concern, see §8 |
| DERIVED_VALUE | none currently | e.g. "grew from $94.04B to $109.42B" — two REPORTED_VALUEs implying a GROWTH_RATE |
| FORECAST/ESTIMATE | none currently | `core/financial/period.py::_GUIDANCE_CUE_RE`/`_FUTURE_CUE_RE` already detect this at the *period* layer for filings; not wired to claim_type classification for chat claims |

Do not add more categories than this — the existing `Metric`/`ConceptRegistry` (§6) already carries the "what is this a claim about" dimension; `claim_type` only needs to carry "what kind of numeric assertion is this."

---

## 5. ENTITY RESOLUTION AUDIT

Two independent entity resolvers exist, of very different quality:

1. **`core/resolvers.py::resolve_entity`** (used by `core/engine.py::verify()`, i.e. the one that actually runs for `/v1/verify`) — a single bare-ticker regex (`\b[A-Z]{2,5}\b`) against the question string. No alias table, no CIK, no disambiguation.
2. **`core/financial/company.py::resolve_company`** (used elsewhere — see below, not by `core/engine.py`) — a real alias table (`_COMPANY_ALIASES`, lines 16-42: `"apple"`/`"apple inc"`/`"apple inc."` → `AAPL`, similarly MSFT/NVDA/TSLA/JPM/GS) plus a ticker regex cross-checked against `ingestion.sec_edgar.TICKER_TO_CIK` (so a random uppercase word that isn't a real ticker won't false-positive), returning a `ResolvedCompany(ticker, cik, matched_text)`.

`resolve_company` is a materially better entity resolver — deterministic, alias-aware, disambiguated against a known-ticker set — and it is **not called by `core/engine.py::verify()` at all**. (Confirmed: `core/resolvers.py` imports nothing from `core.financial.company`.) This is a second, independent "existing capability disconnected from the runtime path" finding, distinct from the extension-context-loss one.

The brief's caution about multi-entity responses ("Apple revenue was..." doesn't prove every later number belongs to Apple) is correctly out of scope for `resolve_company`/`resolve_entity` as written — neither currently tracks "most recently mentioned entity" across a document at all, so there's no incorrect propagation happening today, only *no* propagation. Building sentence-scoped or paragraph-scoped entity propagation (most-recent-named-entity-in-scope, reset at explicit company-name mentions) is new work, not something to find pre-built — flag as a genuine gap, not a disconnection.

**RECOMMENDATION:** `core/resolvers.py::resolve_entity` should call `core/financial/company.py::resolve_company` (against `claim.question` **and**, once available, `claim.metadata["sentence"]`/a new `claim.context` field) instead of its own bare regex, before falling back to any client-supplied hint. `SECProvider.can_handle()` doesn't change; it already just checks for a populated `ticker`/`cik`.

---

## 6. METRIC RESOLUTION AUDIT

Same disconnection pattern as entity resolution:

- **`core/resolvers.py::resolve_metric`** (used by `verify()`): 12 hardcoded substrings (`_METRIC_TERMS`, line 8-11: `revenue, income, margin, ratio, growth, shares, eps, assets, liabilities, cash flow, yield, return, securities`), no canonicalization, no aliasing, no XBRL mapping.
- **`core/financial/concepts.py::ConceptRegistry`**, backed by `config/concepts.yaml` (confirmed to contain, among others, `Revenue` with aliases `["Net Sales", "Turnover", "Sales"]` and XBRL tags `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` etc.; `CostOfGoodsSold`, `GrossProfit`, `OperatingIncome`, `NetIncome`, `OperatingCashFlow`, `Assets`, and more) — a real alias-map + XBRL-tag-map metric registry, with `resolve_alias()` and `resolve_xbrl_tag()` methods already implemented (`concepts.py:43-47`).

`ConceptRegistry` **is** used inside `core/engine.py` — but only for constraint verification (`_resolve_constraint_metric`, `_load_constraint_registry`, lines 204-231), which runs *after* evidence retrieval and only affects `constraint_result`, not `context.metric` used to query `SECProvider`/`ingestion.db.get_fundamentals`. It is never used to *resolve* `claim.metric` before evidence retrieval. This means: even a metric registry rich enough to know `"COGS"` and `"cost of sales"` both mean `CostOfGoodsSold` is not consulted when deciding what to ask SEC EDGAR for — `resolve_metric`'s 12-substring check is what actually gates that.

**RECOMMENDATION:** `core/resolvers.py::resolve_metric` should call `ConceptRegistry.resolve_alias()` (loading the same `config/concepts.yaml` `_load_constraint_registry()` already loads, via `lru_cache`) instead of its own substring list, before evidence retrieval. Do not build a second metric taxonomy.

---

## 7. TEMPORAL RESOLUTION AUDIT

`core/financial/period.py` (154 lines) is a genuinely strong temporal layer: `parse_period_string()` handles fiscal-year (`FY2024`), quarter+fiscal-year (`Q3 FY2025`), quarter+year, word-quarters ("first quarter of fiscal 2025"), explicit dates, and — importantly — flags guidance/forecast language (`_GUIDANCE_CUE_RE`: guidance/expect/forecast/outlook/project/target) and future-relative language (`_FUTURE_CUE_RE`: "next quarter", "coming year") as **not** a resolvable historical period, and separately flags ambiguous relative phrases ("last quarter", "prior year", "full year" without an anchor) as unresolved rather than guessed (`_RELATIVE_AMBIGUOUS_RE`). `periods_compatible()` (same module) is the function that decides MATCH/MISMATCH/UNKNOWN between a claim's period and an evidence period — confirmed exercised by 12 parametrized cases in `tests/test_period_compatibility.py`, including exactly the brief's stated non-negotiable ("Q3 FY2025 evidence must not verify a Q3 FY2026 claim just because the number matches" — see `test_q4_revenue_does_not_verify_against_annual_evidence`, `test_quarterly_value_identical_to_annual_evidence_is_not_verified`, `test_guidance_value_identical_to_historical_evidence_is_not_verified`).

**This is the strongest, best-tested piece of infrastructure in the whole audit — and it is only reachable via `core/identity_verification.py`, which (§1, §9) is only called by `scripts/verify_transcript.py`.** `core/resolvers.py::resolve_time` (the one `verify()` actually calls) is a two-pattern bare-year/`Q[1-4] YYYY` regex with no guidance detection, no ambiguity detection, and no `periods_compatible()` call at all — it just extracts a raw string into `claim.period`; nothing downstream in `core/engine.py::verify()` ever calls `periods_compatible()` on it against evidence.

**RECOMMENDATION:** do not build any new period-parsing logic. `core/resolvers.py::resolve_time` should call `core/financial/period.py::parse_period_string()` and populate `claim.period_struct` (the field already exists on `Claim`, `core/models.py:127`, and is currently only ever set by `_build_batch_claim`/`claim_extractor.py`, never by `resolve_time`). The comparison step itself (§9) is what needs to be wired into `core/engine.py::verify()`.

---

## 8. NUMERIC SEMANTICS AUDIT

`numeric/canonicalizer.py` (555 lines) was not read line-by-line for this pass (flagged as a follow-up read before implementation — INFERENCE below is based on its imports/usage sites, not a full trace), but its usage is confirmed real: `ingestion/transcripts.py`'s module docstring states claim-number parsing "now delegates every parsed number to `numeric.canonicalizer.canonicalize()`... eliminating that duplication" (own quote), and it exports `CanonicalizationError`, `Unit`, `canonicalize` (imported at `ingestion/transcripts.py` top). `fcg/normalizer.py` (200 lines) and `fcg/constraint_engine.py` (360 lines) are a second, separate numeric layer under `fcg/` (Financial Constraint Graph, presumably) not yet traced against `numeric/canonicalizer.py` for overlap — **flagged as a required read before Phase 3 implementation, not concluded here** (avoiding the brief's explicit instruction not to assume or invent; better to say "unread" than to guess).

**FACT confirmed structurally regardless of that unread detail:** whatever `numeric/canonicalizer.py` normalizes, it normalizes the **claim's own value in isolation** — it has no evidence-comparison role, because (§2.7) `MathEngine.run()` never receives `evidence`. Normalizing `0.326` → `32.6` (brief §11's example) is exactly a normalization, not a verification, and the code path today does not conflate the two (it correctly labels it a "correction" in `math_result.corrections`), but that correctness is undermined by §2.9/§9's finding that no independent check follows it.

---

## 9. EVIDENCE RETRIEVAL AUDIT

| Source | Indexed by | Query requires | Independent? | Reached by extension traffic today? |
|---|---|---|---|---|
| SEC EDGAR (`ingestion/sec_edgar.py`, `ingestion/db.py::get_fundamentals`) | ticker → CIK → cached fundamentals rows | `claim.entity.ticker` or `.cik` | Yes — primary filing | **No** (§2.8: `can_handle()` never true) |
| Earnings transcripts (`ingestion/transcripts.py`) | ticker, hardcoded `SAMPLE_TRANSCRIPTS` (6 tickers only, per its own module docstring: "the repository does not contain a reliable transcript fetcher") | ticker | Yes, but tiny/static corpus | No — this is an extraction+offline-verification pipeline for transcripts as *input*, not a queryable evidence source for arbitrary claims |
| RAG (`rag/pipeline.py`, `rag/seed.py`) | not traced this pass | unknown | unknown | Not registered in `providers/registry.py::default_registry()` — **confirmed not reachable via `core/engine.py::verify()` regardless of claim content**, since `default_registry()` returns only `[SECProvider()]` |
| `core/identity_verification.py` (concept+period+value matching over already-retrieved evidence) | n/a — not a source, a comparator | canonical metric name, `FinancialPeriod` | n/a | **No** — only `scripts/verify_transcript.py` calls it (§1, confirmed by repo-wide grep) |

**Central question answered directly:** the existing FinVerify capability that can already independently verify numerical/financial claims is the combination of `ingestion/sec_edgar.py` + `providers/sec.py` + `core/identity_verification.py` + `core/financial/period.py`. All four pieces are real, and (for `identity_verification.py`/`period.py`) well-tested. **None of the four are reached by `/v1/verify`.** The RAG pipeline is a fifth candidate source that isn't even registered with the provider registry — before investing in it, confirm whether it's meant to be a second `Provider` (`providers/base.py::Provider` protocol) or whether `rag/pipeline.py` is presently orphaned/experimental; this audit did not have scope to determine that and it should not be assumed either way.

---

## 10. EVIDENCE IDENTITY / MATCHING AUDIT

Covered in depth at §7/§9. Restating the brief's three non-negotiable examples against the actual code:

- *Company A rev Q3'26 = $100B vs. evidence Company A rev Q3'25 = $100B* → correctly rejected **if and only if** `core/identity_verification.py::compare_value_to_evidence()` is called, because it calls `periods_compatible()` per evidence match before ever comparing values (lines 88-96: `MISMATCH` → skip, added to `mismatched_periods`). **Today, this function is not called by `verify()`, so this rejection does not happen on the `/v1/verify` path** — a same-value-wrong-period claim would currently just fail to find any SEC evidence at all (because entity/period never resolve, per §3) and land on `UNVERIFIED`, which is *accidentally* safe (wrong answer for the right reason: not enough context, not "checked and rejected"). Once entity resolution (§5) is fixed without also wiring in `identity_verification.py` (§9), this same claim could resolve a ticker, fetch Q3'25 SEC data, and — because nothing compares periods — could be marked `VERIFIED` by tier/correction-severity alone. **This is the concrete failure mode this audit is most worried about being introduced if fixes are sequenced wrong (see §23).**
- *Company A revenue vs. Company A operating income, same value* → rejected by `primary_evidence_matches()`'s canonical-concept-name check (`identity_verification.py:60-61: canonical_locator == canonical_metric`) — same caveat: only if wired in.
- *Company A vs. Company B, same value* → rejected structurally because `SECProvider.retrieve()` only ever fetches rows for `claim.entity.ticker` (`providers/sec.py:20-22`) — this one **is** already safe today, entity mixing across companies cannot happen via the SEC provider regardless of the wiring gap, since evidence is fetched per-ticker to begin with.

**Strongest identity required, confirmed as already implementable from existing types:** `Entity.ticker/cik` + `Metric.canonical_name` (via `ConceptRegistry.resolve_alias`) + `FinancialPeriod` (via `periods_compatible`) + relative-tolerance value match (`compare_value_to_evidence`'s `tolerance: float = 0.01` parameter, i.e. 1% relative tolerance today — confirm this is the intended production tolerance or should be tightened/config-driven before Phase 3, not assumed correct by default).

---

## 11. CORRECTION VS VERIFICATION AUDIT

The codebase's own naming is already correct and should be preserved: `math_result.corrections` (self-normalization of the claim's own number, e.g. scale/sign/magnitude) is clearly separated in the data model from `Evidence`/`trust_score` (independent corroboration). The bug is not conceptual confusion in the schema — it's that the "verification" half of that correctly-drawn line (§2.9, §9) currently does nothing. Do not rename or restructure `Correction`/`MathResult`/`Evidence` — they are already the right shape; wire the missing comparison into `compute_trust`/`verify()`, don't redesign around it.

---

## 12. CLAIM DEDUPLICATION AUDIT

Two separate dedup surfaces, both currently under-keyed once identity fields are added (flagged, not yet broken, because there's currently nothing to under-key):

1. **Extension-side, `session.ts::getOrCreateDeduped`** (§2.4): key is `` `${question}|${rawValue}` ``. Must become `` `${question}|${rawValue}|${entity?.ticker ?? ""}|${period ?? ""}` `` (or equivalent) the moment entity/period are added to `ExtractedClaim`/the request, or claims about different companies/periods that happen to produce the same generic question + same raw value will silently share one cached result (§2.4 detail).
2. **Backend-side:** no dedup found in `core/engine.py::verify_batch()` — each `BatchClaim` is verified independently (`engine.py:83-84`, a plain loop, no key/cache). For "100+ numeric claims in one response" (brief §18), today that means up to 100+ independent SEC/DB round-trips per response if/when entity resolution starts succeeding, with no de-duplication of e.g. the same `(ticker, metric, period)` triple appearing 5 times in one answer (once as "revenue was $109.42B", again as "revenue increased to $109.42B", again inside a "grew from $94.04B to $109.42B" sentence). This is a genuine gap, not a disconnection — flag as new work (§23, P2 — correctness first, performance second, per the brief's own prioritization framing).

**Recommended identity for both layers:** `(canonical_metric, ticker_or_entity_name, canonical_period, claim_type)` — same tuple `identity_verification.py` already uses for matching, reused here for dedup for consistency (RECOMMENDATION, not yet implemented anywhere).

---

## 13. DERIVED CLAIMS AUDIT

No code currently reproduces `(new - old) / old` and checks it against a stated growth percentage anywhere in `core/`, `fcg/`, or `numeric/` (confirmed by the structural read of `MathEngine`/`ConstraintVerifier` above — `fcg/constraint_engine.py` was not fully read this pass and is the most likely home for this kind of cross-metric check given its name and its existing role in `_run_constraint_verification`/`ConstraintVerifier` for things like margin identities; **flagged as the first place to check before writing a new derived-value verifier**, not concluded absent). `ConstraintVerifier` (`core/financial/constraints`, invoked from `core/engine.py:94-112`) already does cross-*metric* consistency checking within one claim/batch (e.g. gross margin = (revenue − COGS)/revenue, inferred from `config/concepts.yaml` entries carrying `"validation"` strings like `"Must be > 0"` and the presence of a whole `core/financial/constraints/` submodule) — whether it already supports cross-*period* consistency (this year vs. last year → stated growth rate) was not confirmed and should not be assumed either way pending a dedicated read of `core/financial/constraints/`.

**Recommended semantics (RECOMMENDATION):** a derived claim ("grew 16.4%") should never be marked `VERIFIED` directly — only `VERIFIED_DERIVED` (or an equivalent `metadata` flag alongside the existing `VerificationStatus`, not a new top-level status, to avoid the brief's §15 instruction not to multiply states) when *both* input values it implies (`$94.04B`, `$109.42B`) are themselves independently `VERIFIED` against primary evidence *and* the arithmetic checks out within tolerance. This preserves the brief §13 instruction to distinguish "derived correctly from verified inputs" from "directly reported by source."

---

## 14. FORECAST / ESTIMATE AUDIT

`core/financial/period.py::_GUIDANCE_CUE_RE`/`_FUTURE_CUE_RE` (§7) already flag guidance/forecast language at the period-parsing layer and are already exercised by `test_guidance_value_identical_to_historical_evidence_is_not_verified` — i.e. the existing infrastructure already treats a guidance-period claim as **not matchable** against historical evidence (correctly conservative — UNVERIFIED, not CONTRADICTED, per that test name). This satisfies the brief's requirement ("a forecast differing from actual is not necessarily a contradiction") at the period layer, again contingent on `identity_verification.py` being wired into `verify()` (§9) — today this protection, like the others in §10, is not reachable from `/v1/verify`.

---

## 15. VERIFICATION STATES — TRANSITION CONDITIONS (confirmed vs. brief's target table)

| Condition | Brief target | Current code (`core/trust_engine.py::compute_trust`) |
|---|---|---|
| No evidence | UNVERIFIED | ✅ matches (`evidence_tier is USER and raw_value is not None` branch) |
| Evidence conflicts with claim | CONTRADICTED | ❌ unreachable — no code path ever sets `Consistency.FAIL`/`RuleEvidence.CONFLICTING` (§2.9) |
| Evidence exactly supports claim | VERIFIED | ⚠️ partially — reachable via `TRUST_RULES` tier/correction matching, but **not gated on the evidence value actually matching the claim value** (§2.9) |
| Evidence exists but identity insufficient (wrong period/entity/metric) | UNVERIFIED | ❌ no identity-insufficiency check exists on this path at all (§10) — such a case either never retrieves evidence (falls to model_input/UNVERIFIED, accidentally correct) or, once entity resolution improves without §9's fix, could be mislabeled VERIFIED |
| Still running | PENDING | not traced this pass — `VerificationStatus.PENDING` exists in the enum; whether anything ever sets it in the current synchronous FastAPI request/response cycle is unconfirmed and likely N/A (no async job queue observed in `app/main.py`'s `/v1/verify`) |
| Infra failure | ERROR | not traced this pass — likely surfaces as an HTTP 5xx today rather than a `VerificationStatus.ERROR` payload; confirm before Phase 3 |

**Do not add new states.** The five-state enum is right; §9's fix is what makes CONTRADICTED reachable and makes VERIFIED mean what it should.

---

## 16. CONFIDENCE / TRUST AUDIT

`core/trust_engine.py`'s `TRUST_RULES` table (§2.9) already encodes several of the brief's listed factors (evidence tier, correction severity, ambiguity) but is missing the most important one for the brief's stated priority ("accuracy over verification rate"): **whether the value itself matched**. Once §9's fix adds a value-match result, it should become a first-class dimension in `TrustFindings` (a new field, e.g. `value_match: Literal["exact","within_tolerance","mismatch","not_compared"]`) and `TRUST_RULES` should be extended (not replaced — the existing rule-table pattern is reusable and already unit-tested rule-by-rule in `tests/test_trust_engine.py`) so that no rule can produce `HIGH`/`VERIFIED` without `value_match` being `exact` or `within_tolerance`. Do not average scores across claims — the existing per-claim, rule-matched, `DEFAULT_LABEL="LOW"`-on-no-match design (lines 67-70,135-145) is a defensible confidence model; the gap is an input to it, not the model itself.

---

## 17. PROVIDER NORMALIZATION AUDIT (ChatGPT / Claude)

Both adapters implement the same `ProviderAdapter` interface (`adapters/types.ts`) and, per §2.1, both currently normalize down to *only* `{ text: string }` for the finance plugin's purposes. The interface itself (`matches`, `findMessages`, `isStreaming`, `extractText`, `findToolbar`, `mountPoint`) is a reasonable minimum contract for future providers (Gemini/DeepSeek/Perplexity/Copilot/Grok) to implement — **do not change this interface** for Phase 3. What Phase 3 should add, at the interface level, is an *optional* `extractContext?(messageEl): { userQuestion？: string; modelLabel?: string }` method so any adapter (present or future) can supply richer context without every adapter being forced to implement DOM-specific extraction it may not support — a plugin/session layer change (§2.3, §2.5), not a per-provider one. This is additive to the existing registry pattern (`adapters/registry.ts`), which was not fully read this pass but is confirmed (by `stub.ts` existing alongside real adapters) to already support pluggable, incomplete/placeholder adapters — a good sign for future-provider onboarding not needing architecture changes, only new adapter files.

---

## 18. PERFORMANCE / BATCHING AUDIT

- **Does each claim cause an API request?** Yes, per-claim (`session.ts::verifyOne`, one `transport.verify()` call per unique dedup key) — no client-side batching to `/v1/verify/batch` observed anywhere in `packages/core/src/` (`http-transport.ts` implements only `verify()`/`checkHealth()`, no `verifyBatch()`; `session.ts` never imports or calls a batch endpoint).
- **Are duplicates eliminated before requests?** Only via the flawed dedup key discussed in §12 — genuinely-identical repeated claims within the *same* generic-question+value pair are deduped; anything richer is not, because there's no richer identity to dedup on yet.
- **Is evidence cached?** Not observed in `core/evidence.py` (a fresh `provider.retrieve(claim)` call every time; `ingestion/db.py::get_fundamentals` may itself cache at the DB layer — not traced this pass, flagged as a follow-up).
- **Parallelized?** Yes — `VerificationSession.verify()` runs a worker pool (`Math.max(1, Math.min(this.deps.concurrency, claims.length))` workers, default concurrency 3 via `DEFAULT_CONCURRENCY` in `engine.ts:24`) pulling from a shared cursor (`session.ts:76-86`). This is solid, reusable infrastructure.
- **Cancellation?** Yes — `VerificationSession.cancel()` aborts only controllers the session itself created (careful, well-commented ownership logic, `session.ts:38-59`, explicitly designed to not break a *different* session sharing a deduped in-flight request).
- **Retry?** Yes — `withRetry` (`retry.ts`, not fully read) wraps the HTTP call in `http-transport.ts:45-71`, distinguishing retryable (429, 5xx, network/timeout) from non-retryable (other 4xx) failures (`isRetryableStatus`, lines 10-12).

**Recommended path for "100+ claims per response" (RECOMMENDATION):** switch the extension from N calls to `/v1/verify` to one call to `/v1/verify/batch` per message (already exists server-side, §22), after deduping locally by the richer identity tuple from §12 — this is the single highest-leverage performance change and requires no new backend endpoint.

---

## 19. SECURITY / TRUST-BOUNDARY AUDIT

**Must remain backend-authoritative, confirmed by current code already doing this correctly and Phase 3 must not regress it:**
- `verification_status`, `confidence`, `trust_score`/`trust_color`, `reasons` — computed entirely server-side today (`core/trust_engine.py`); the client only ever *reads* these back from the response. ✅ safe today.
- `evidence` / evidence provenance (source name, URL, authority) — constructed entirely server-side (`Evidence`/`Source` models, populated inside `providers/sec.py`/`core/evidence.py`). ✅ safe today.
- Once entity/metric/period become **client-supplied hints** (§22), the backend must treat them exactly as `BatchClaim`'s existing fields are already treated by `_build_batch_claim`/`resolve_entity`/`resolve_metric`/`resolve_time`: **the client value is only ever used if the resolver can't find a better one itself, and it is never used to directly select which evidence counts as a match** — i.e. a malicious/wrong client-supplied `entity.ticker="AAPL"` on an actually-Microsoft claim should not be able to force `SECProvider` to fetch AAPL data and then have `identity_verification.py` (once wired in, §9) blindly trust that the fetched-AAPL-data "matches" — matching must still be against the *canonical resolved* entity, ideally independently re-derived from `claim.metadata["sentence"]`/context text server-side wherever possible, with the client hint only used as a tiebreak/performance shortcut, never as ground truth. This is a **new requirement to design in from the start**, not something existing code already enforces, because existing code (`resolve_entity`: `if claim.entity is not None: return claim`, `core/resolvers.py:15-16`) currently trusts a pre-set `claim.entity` unconditionally the moment one exists — that line is safe *today* only because nothing populates `claim.entity` from an untrusted client. The moment `V1VerifyRequest` gains an `entity` field, that trust-on-sight behavior becomes a real spoofing vector and `resolve_entity` must change to re-derive/validate rather than pass through. **Flag this explicitly as a must-fix concurrent with §22's schema change, not a later hardening pass.**
- `model_source` — logging-only today (§2.6); fine to keep as an untrusted, informational-only field.

---

## 20. TEST MATRIX

| # | Case | Status |
|---|---|---|
| 1 | exact financial value | PARTIAL — `tests/test_numeric_canonicalizer.py`, `test_normalizer.py` cover parsing; no end-to-end `/v1/verify`-path test with real entity+metric+period+SEC-backed value confirms VERIFIED |
| 2 | exact percentage | PARTIAL — same as above |
| 3 | exact EPS | MISSING (not found in `tests/test_verify_api.py`'s 6 cases, which are all ratio/margin-correction focused) |
| 4 | exact ratio | EXISTS — `test_v1_verify_cet1_ratio_no_correction`, `test_v1_verify_pe_ratio_no_correction` |
| 5 | exact count (shares) | MISSING |
| 6 | exact growth rate | PARTIAL — `test_v1_verify_revenue_growth_scale_mul100` exists but tests *correction*, not evidence-backed verification |
| 7 | percentage points | MISSING (claim_type doesn't even exist yet, §4b) |
| 8 | basis points | EXISTS (transcripts/claim-type level; not confirmed at `/v1/verify` evidence-matching level) |
| 9 | unit normalization | EXISTS — `test_numeric_canonicalizer.py` |
| 10 | scale normalization | EXISTS — `test_numeric_canonicalizer.py`, `test_v1_verify_scale_mul100_profit_margin` |
| 11 | wrong value | MISSING at the `/v1/verify` engine level (§2.9's core gap — nothing to test yet because nothing checks it) |
| 12 | wrong entity | MISSING at engine level (same reason); EXISTS conceptually only via §10's cross-company non-mixing, untested end-to-end |
| 13 | wrong metric | MISSING at engine level |
| 14 | wrong period | **EXISTS and strong** — `tests/test_period_compatibility.py`, but only exercised through `identity_verification.py`/`scripts/verify_transcript.py`, not through `core/engine.py::verify()` |
| 15 | wrong unit | MISSING |
| 16 | duplicate claims | MISSING (no dedup logic to test at richer-identity level, §12) |
| 17 | derived claims | MISSING (§13 — no derived-value verifier exists yet) |
| 18 | verified-input calculations | MISSING |
| 19 | forecasts | PARTIAL — `test_guidance_value_identical_to_historical_evidence_is_not_verified` exists but again only via the disconnected `identity_verification.py` path |
| 20 | estimates | MISSING |
| 21 | no evidence | EXISTS — `test_no_independent_evidence_is_unverified_not_low` |
| 22 | ambiguous context | PARTIAL — `test_ambiguous_relative_period_is_not_guessed` covers period ambiguity only |
| 23 | multiple entities | MISSING |
| 24 | multiple periods | PARTIAL — `test_periods_compatible_matrix` (parametrized) covers the comparator; not the full pipeline |
| 25 | table extraction | MISSING (no table-context extraction exists at all, §2.2) |
| 26 | long responses | MISSING at extension-integration level; `e2e/performance.spec.ts` exists (not read this pass — flagged) |
| 27 | batching | PARTIAL — `tests/test_batch_verify.py` exists for the backend batch endpoint; no client-side batching to test yet (§18) |
| 28 | provider normalization | not traced (extension test suite not fully enumerated this pass) |
| 29 | evidence provenance | PARTIAL — covered implicitly by `Source`/`Evidence` model tests where they exist; no dedicated provenance-tamper test found |
| 30 | client tampering | MISSING — no test found that POSTs a client-supplied `entity`/`ticker` to `/v1/verify` and asserts the server doesn't blindly trust it (consistent with §19's finding that this isn't designed for yet either) |

---

## 21. EXISTING CAPABILITIES THAT ARE CURRENTLY DISCONNECTED (roll-up)

1. `core/identity_verification.py` (value+concept+period identity matching) — built, tested, used only by `scripts/verify_transcript.py`.
2. `core/financial/company.py::resolve_company` (alias-aware entity resolution) — built, not called by `core/resolvers.py::resolve_entity`.
3. `core/financial/concepts.py::ConceptRegistry` (alias/XBRL-aware metric resolution) — built, used only for constraint verification, not for pre-evidence-retrieval metric resolution.
4. `core/financial/period.py::parse_period_string`/`periods_compatible` — built, tested, reachable only via `identity_verification.py`'s disconnected path.
5. `core/engine.py::verify_batch()` + `BatchClaim` (entity/ticker/cik/metric/period/period_struct-carrying request shape) — fully built and already exposed at `POST /v1/verify/batch`; the extension calls only the impoverished `/v1/verify` singular endpoint and never this one.
6. `ingestion/sec_edgar.py` + `providers/sec.py` (real primary-source evidence) — built, gated entirely behind entity resolution succeeding (#2 above).

---

## 22. MISSING CAPABILITIES (roll-up)

1. Value-vs-evidence comparison wired into `core/engine.py::verify()` for the single-claim (`/v1/verify`) path — §9/§1's central finding.
2. Sentence/context-level entity+period extraction in the extension (`detect.ts`) and a place to carry it (`ExtractedClaim`, `V1VerifyRequest`) — §2.2/§2.6/§22b below.
3. Percentage-point-change claim type (distinct from bps and plain percentage) — §4b.
4. Derived-claim (two-value growth) detection and verified-input-gated status — §13.
5. Richer dedup identity, both client and server side — §12.
6. Client-hint trust-boundary hardening for entity/metric/period once they become request fields — §19.

### 22b. Minimum new contract (answering brief §22 directly)

```jsonc
// Extend V1VerifyRequest (app/models.py) — additive, backward compatible:
{
  "question": "...",              // keep; becomes secondary once "context" exists
  "raw_value": 109420000000,
  "model_source": "chatgpt",      // start actually populating this (§2.4 gap)
  "context": "Apple reported revenue of $109.42B in Q3 FY2026.",  // NEW, required-ish: the sentence, not a template
  "claim_type": "revenue",        // NEW: from ExtractedClaim.claim_type, already computed client-side, currently dropped
  "entity_hint": {"name": "Apple", "ticker": null},  // NEW, optional, client hint only — see §19
  "metric_hint": "revenue",       // NEW, optional, client hint only
  "period_hint": "Q3 FY2026",     // NEW, optional, client hint only
  "comparison_period_hint": null  // NEW, optional — only for growth/derived claims
}
```

- **Required:** `question` or `context` (at least one), `raw_value`, `claim_type`.
- **Optional / client hints, never trusted as ground truth (§19):** `entity_hint`, `metric_hint`, `period_hint`, `comparison_period_hint`, `model_source`.
- **Backend must independently resolve, not trust:** the *canonical* entity/metric/period actually used for evidence matching — hints only shortcut/bias resolution, per §19.
- **Backward compatibility:** every new field is optional; existing callers sending only `{question, raw_value}` continue to work exactly as today (falling into the current, correctly-conservative UNVERIFIED-on-no-evidence path).
- This is intentionally close to, but not identical to, the brief's §22 draft — it drops `value`/`unit`/`scale`/`currency` as separate top-level fields because `numeric/canonicalizer.py`/`claim_type` already derive those deterministically from `raw_value` + `claim_type` (§8), avoiding a duplicate numeric-shape system the brief itself (§3) warns against inventing.

---

## 23. P0 / P1 / P2 / P3 TABLE AND RECOMMENDED ORDER

| Pri | Item | Why this priority |
|---|---|---|
| **P0** | Wire `core/identity_verification.py` (value+concept+period comparison) into `core/engine.py::verify()` for the single-claim path, and make `CONTRADICTED`/proper `VERIFIED` reachable from it. | This is the one change that makes "VERIFIED" mean what the brief's final principle requires. Backend-only, no extension change needed, reuses tested code. Must land **before** entity-resolution improvements (below), or entity-resolution-only fixes will start marking claims VERIFIED on tier/correction alone (§3's warned-about failure mode). |
| **P0** | `core/resolvers.py::resolve_entity`/`resolve_metric`/`resolve_time` call `resolve_company`/`ConceptRegistry`/`parse_period_string` instead of their own weak regexes, sourced from the new `context`/`claim_type` fields (not just the generic question string). | Without this, the P0 above has nothing to compare against for extension-originated claims — `SECProvider.can_handle()` still never fires. |
| **P0** | Extension: pass the matched sentence (already captured as `ExtractedClaim.sentence`) through to the backend instead of discarding it in `buildQuestion()`; extend `V1VerifyRequest`/`Claim` per §22b. | Source of the entity/period text the two P0 items above need to resolve against. |
| **P1** | Client-hint trust-boundary hardening (§19) for the new `entity_hint`/`metric_hint`/`period_hint` fields, landed **in the same change** as §22b, not after. | New attack surface introduced by the very fields being added; must not ship in a state where a spoofed hint can select evidence. |
| **P1** | Update both dedup keys (extension `session.ts`, and add server-side dedup for batch) to the richer `(metric, entity, period, claim_type)` identity. | Prevents cross-company/cross-period result collisions the moment richer identity fields exist (§12). |
| **P1** | Derived-claim (growth-from-two-values) detection + `verified-if-inputs-verified` semantics (§13). | Directly named in the brief as a required capability; currently fully absent. |
| **P1** | Percentage-point-change claim type + pattern (§4b). | Currently silently mis-captured or missed entirely by the regex set. |
| **P2** | Switch extension from per-claim `/v1/verify` calls to `/v1/verify/batch` with local pre-dedup (§18). | Real performance win, already has a backend endpoint; sequenced after correctness fixes per the brief's own stated priority. |
| **P2** | Confirm/port the Phase-7A backtracking bug-fix into the extension's `currency_raw` regex (§2.2). | Real but narrow divergence; low blast radius. |
| **P2** | Read `fcg/constraint_engine.py` and `numeric/canonicalizer.py` fully to confirm whether cross-period derived-value checking already partially exists there before building §13's derived-claim verifier from scratch. | Avoids duplicate work; flagged as unread in this audit. |
| **P3** | RAG pipeline (`rag/pipeline.py`) registration as a second `Provider`, if it's meant to be one — status unconfirmed this pass. | Secondary evidence source, not blocking core correctness. |
| **P3** | Table/paragraph-context extraction beyond single-sentence. | Real gap (§2.2/§20 test #25) but lower yield than sentence-level fixes above. |
| **P3** | New provider adapters (Gemini/DeepSeek/Perplexity/Copilot/Grok) per the brief's explicit "not now" instruction. | Out of scope by the brief's own framing; architecture already supports it via `ProviderAdapter` (§17). |

---

## 24. RECOMMENDED UNIVERSAL VERIFICATION ARCHITECTURE (target state, reusing existing components only)

```
DOM (assistant text + user question, adapter-extracted)
  → detect.ts::detectFinanceClaims()      [keep regexes; stop discarding entity/period text
                                            already present in the matched sentence]
  → buildQuestion()  [keep for display; ALSO pass through the raw `sentence` as `context`]
  → session.ts        [dedup key: (claim_type, raw_value, entity_hint, period_hint) — extend]
  → POST /v1/verify {question, raw_value, model_source, context, claim_type,
                      entity_hint?, metric_hint?, period_hint?, comparison_period_hint?}
  → app/main.py::v1_verify_endpoint()  [build a richer Claim, pass hints through]
  → core/engine.py::verify()
       compile_claim()
       resolve_entity()   → core/financial/company.py::resolve_company()   [existing]
       resolve_metric()   → core/financial/concepts.py::ConceptRegistry    [existing]
       resolve_time()     → core/financial/period.py::parse_period_string  [existing]
       EvidenceRetriever.retrieve()  → providers/sec.py (unchanged)        [existing]
       MathEngine.run()   (self-correction, unchanged)                    [existing]
       NEW: identity_verification.primary_evidence_matches() +
            compare_value_to_evidence()  → value_match result             [existing, newly wired]
       compute_trust()    extended with value_match dimension             [existing rule-table, extended]
  → V1VerifyResponse (unchanged shape; verification_status now genuinely
                       earned, not just evidence-tier-derived)
```

No new subsystems are proposed. Every box above already exists in the repository; the architecture change is entirely about **wiring order and context propagation**, not new components — exactly per the brief's §21 instruction.

---

## 25. MINIMUM API / SCHEMA CHANGES

Covered in §22b. Restated compactly:

- `app/models.py::V1VerifyRequest` — add `context`, `claim_type`, `entity_hint`, `metric_hint`, `period_hint`, `comparison_period_hint`, all optional. Start actually reading `model_source` past the log line.
- `app/models.py::V1VerifyResponse` — add `value_match: str | None` (mirrors the new `TrustFindings` dimension, §16) so the extension can eventually explain *why* something is VERIFIED, not just that it is.
- `packages/core/src/types.ts::V1VerifyRequest`/`ExtractedClaim` — mirror the above additively.
- No changes to `BatchClaim`/`BatchVerifyRequest`/`/v1/verify/batch` — already sufficient (§22).

---

## 26. FILE-BY-FILE IMPLEMENTATION PLAN

| File | Change |
|---|---|
| `finverify-terminal/backend/core/engine.py::verify()` | After `evidence = evidence_retriever.retrieve(...)` and before `trust = compute_trust(...)`, call `core/identity_verification.py::primary_evidence_matches()` + `compare_value_to_evidence()` using `compiled.metric`, `compiled.period_struct`, `compiled.raw_value`/`math_result.verified_value`, and a `ConceptRegistry` instance (reuse `_load_constraint_registry()`, already `lru_cache`d). Pass the resulting `EvidenceValueComparison` into `compute_trust()`. |
| `finverify-terminal/backend/core/trust_engine.py::compute_findings()`/`TrustFindings` (`core/models.py`) | Add `value_match` field; set `consistency=Consistency.FAIL` when `EvidenceValueComparison.matched is False` and at least one period matched (i.e. a real, period-compatible mismatch — not just "nothing to compare"); extend `TRUST_RULES` so no rule yields VERIFIED without a positive match. |
| `finverify-terminal/backend/core/resolvers.py` | Replace `resolve_entity`'s bare regex with a call to `core.financial.company.resolve_company`; replace `resolve_metric`'s substring list with `ConceptRegistry.resolve_alias`; replace `resolve_time`'s two-pattern regex with `core.financial.period.parse_period_string`, populating `claim.period_struct`. Resolve against `claim.question` **and** a new `claim.metadata["context"]` (the sentence) once available. |
| `finverify-terminal/backend/app/models.py::V1VerifyRequest`/`V1VerifyResponse` | Add fields per §25. |
| `finverify-terminal/backend/app/main.py::v1_verify_endpoint()` | Build `Claim(question=..., raw_value=..., metadata={"context": req.context}, entity=Entity(name=req.entity_hint) if hinted else None, ...)` — hints only, never trusted directly for matching (§19); pass `req.model_source` into `Claim.model_source` (currently dropped, §2.6). |
| `finverify-extension/packages/core/src/plugins/finance/detect.ts` | Stop truncating context out of the pipeline: keep `sentence` on the object actually sent (already captured, just currently dropped by `buildQuestion`'s narrow `Pick<...>` type). |
| `finverify-extension/packages/core/src/types.ts::V1VerifyRequest` | Mirror backend additions. |
| `finverify-extension/packages/core/src/session.ts::getOrCreateDeduped` | Extend dedup key with entity/period once available (§12/P1). |
| `finverify-extension/apps/extension/src/adapters/types.ts` + `chatgpt/claude/index.ts` | Add optional `extractContext?()` for future user-question/model-label extraction (§17) — not required for the P0 items, sequence after. |

---

## 27. FUNCTION/CLASS CHANGES (summary of signatures touched)

- `core/resolvers.py`: `resolve_entity(claim: Claim) -> Claim`, `resolve_metric(claim: Claim) -> Claim`, `resolve_time(claim: Claim) -> Claim` — same signatures, new internals only.
- `core/engine.py::verify()` — internal addition of an identity-match step between evidence retrieval and trust computation; return type (`VerificationResult`) unchanged.
- `core/trust_engine.py::compute_findings(context, math_result, evidence) -> TrustFindings` — new optional parameter or overload to receive the `EvidenceValueComparison`; `TrustFindings` gains one field.
- `core/models.py::TrustFindings`, `V1VerifyRequest`/`V1VerifyResponse` (`app/models.py`), `ExtractedClaim`/`V1VerifyRequest` (`types.ts`) — additive fields only, per §25.

---

## 28. TEST PLAN

Add, at minimum, the currently-MISSING/PARTIAL rows from §20's matrix (#3, #5, #7, #11-13, #15-18, #20, #23, #30 especially), plus:
- An end-to-end `/v1/verify` test that sends a real ticker + metric + period + a value matching seeded SEC fixture data, and asserts `verification_status == "verified"` **and** `reasons` reflects a genuine value match (not just tier/correction) — this test cannot pass today and is the direct regression guard for §23's top P0 item.
- A companion test with the same entity/metric/period but a wrong value, asserting `verification_status == "contradicted"` — currently impossible to write meaningfully (§2.9), should be the first new test added.
- A client-tampering test: POST a client-supplied `entity_hint` that's wrong for the `context` sentence, assert the server doesn't blindly trust it (§19/#30).

---

## 29. ACCEPTANCE CRITERIA

1. A claim with a real ticker, resolvable metric, resolvable period, and a value that matches seeded/live SEC data returns `verification_status: "verified"` with `reasons` naming the matched source and period — not just "primary source, no corrections."
2. The same claim with the value changed to something that disagrees with the evidence returns `verification_status: "contradicted"`.
3. A claim whose period cannot be matched to any retrieved evidence (even though the entity/metric matched) returns `"unverified"`, never `"verified"`.
4. Existing Phase 0-2 behavior (no evidence → unverified, `trust_score: "N/A"`, `confidence: null`) is unchanged for callers that don't send any new hint fields.
5. All 557 existing backend tests and 89 existing extension tests still pass.
6. A spoofed/incorrect client-supplied `entity_hint` cannot cause a claim to be marked verified against the wrong company's evidence.

---

## 30. REGRESSION RISKS

- **Most important risk:** wiring in real value-comparison (§23 top item) will, correctly, flip some currently-`UNVERIFIED` claims to `CONTRADICTED` once entity resolution also improves — this is *intended* per the brief's final principle, but will look like a regression in verification-rate dashboards if anyone is tracking "% verified" as a success metric. Flag this explicitly to whoever reviews the Phase 3 rollout so it isn't reverted as a false regression.
- Changing `resolve_entity`/`resolve_metric`/`resolve_time` internals changes what `context.metadata`/`context.provider` end up being for claims that previously fell through to `model_input` — downstream code that pattern-matches on `provider == "model_input"` (if any exists outside what was traced here) should be checked.
- Extending the dedup key (§12) will reduce cache-hit rate for the existing narrow key — expected and correct, but worth confirming request-volume impact given the 100-req/min rate limit noted in `app/main.py`'s `/v1/verify` docstring (line 375).
- `TrustFindings.value_match` is a new field on a `BaseModel` (`core/models.py`) that is currently `exclude=True` on the public `TrustScore.findings` (`core/models.py:112`) — confirm this exclusion is intentional (internal-only diagnostic) before assuming `reasons` (the public string list, already built manually in `trust_engine.py::build_trust`, lines 157-164) is the only place to surface it publicly; extend that string-building function too, don't just add the field and assume it's visible.

---

## 31. EXPLICIT DO-NOT-CHANGE LIST

- `core/models.py::VerificationStatus` — keep exactly `VERIFIED | CONTRADICTED | UNVERIFIED | PENDING | ERROR`. Do not add states.
- `Claim`/`BatchClaim`/`VerificationContext`/`Evidence`/`Source`/`MathResult`/`Correction` shapes — already correctly designed; extend additively only (per §25/§27), never restructure.
- `core/financial/period.py`, `core/financial/company.py`, `core/financial/concepts.py`, `core/identity_verification.py` — do not rewrite; these are the strongest, best-tested parts of the codebase. Wire them in; don't reinvent them.
- `providers/sec.py::SECProvider.can_handle()`/`retrieve()` — unchanged; it's already correctly scoped to "only fetch for a resolvable ticker."
- The Phase 0-2 no-evidence → UNVERIFIED behavior in `app/main.py` (lines 398-406) — keep as the correct fallback/floor; the new value-comparison logic sits *inside* the "evidence exists" branch, it does not replace this guard.
- `VerificationSession`'s cancellation/dedup ownership model (`session.ts`) — subtle and already correctly handles the shared-promise-vs-owned-controller distinction (§2.4); extend the dedup *key*, don't touch the ownership logic.
- Provider expansion (Gemini/DeepSeek/Perplexity/Copilot/Grok) and UI redesign — explicitly out of scope per the brief.

---

## MOST IMPORTANT QUESTIONS — DIRECT ANSWERS

**1. What is the current universal claim representation?**
At the wire level, for `/v1/verify`: `{question: str, raw_value: float, model_source?: str}` — effectively just a number and a templated generic question (`ExtractedClaim`/`Claim` internally hold more, but almost none of it reaches this endpoint). The *backend-internal* representation (`core/models.py::Claim`) is already rich (entity, metric, period, period_struct, accounting_basis, scope, value_role, temporal_frame) — it's simply never populated for extension traffic.

**2. What semantic information is currently lost between the LLM response and `/v1/verify`?**
Entity/company, fiscal period, comparison period (for growth claims), currency, the original sentence/context, and `model_source` (defined in the contract but never actually populated by any caller). Lost in two places independently: `detect.ts::detectFinanceClaims()` never captures it, and `buildFinanceQuestion()`'s narrow input type drops even the `sentence` field that *is* captured.

**3. What existing FinVerify backend infrastructure can already independently verify numerical/financial claims?**
`ingestion/sec_edgar.py` + `providers/sec.py` (primary-source evidence retrieval) combined with `core/identity_verification.py` (value+concept+period identity matching) and `core/financial/period.py` (period parsing/compatibility) and `core/financial/company.py`/`core/financial/concepts.py` (entity/metric resolution). All exist, all work, all are reachable only from `scripts/verify_transcript.py` or the constraint-verification side-path — none are exercised by `core/engine.py::verify()`'s value-checking logic.

**4. Why is that infrastructure currently not being reached or supplied enough context?**
Two independent reasons: (a) `/v1/verify` never sends entity/metric/period, so `SECProvider.can_handle()` never returns True; (b) even when evidence IS retrieved (e.g. via `/v1/verify/batch` with a client-supplied entity), `core/engine.py::verify()` never calls `identity_verification.py` to actually compare the claim's value to the evidence's value — that comparison logic exists but only `scripts/verify_transcript.py` calls it.

**5. What minimum context must travel from the extension to the backend?**
The matched sentence (`context`), the claim's `claim_type`, and optionally entity/metric/period *hints* extracted from the same sentence — see §22b for the concrete schema.

**6. What must the backend independently resolve rather than trust from the client?**
The canonical entity (ticker/CIK), canonical metric name, and canonical period actually used to select and match evidence. Client-supplied hints may bias/shortcut resolution but must never be the sole basis for what evidence counts as a match (§19) — this is a new requirement to build in, not an existing protection.

**7. How should arbitrary numeric/financial claims be canonicalized?**
Via the already-built `numeric/canonicalizer.py` for value/scale/unit, `core/financial/concepts.py::ConceptRegistry` for metric identity, and `core/financial/period.py` for period identity — no new canonicalization system is needed; these need to be *called* from the resolution stage that currently uses weaker ad hoc logic (`core/resolvers.py`).

**8. How should evidence identity be established before marking a claim VERIFIED?**
Exactly as `core/identity_verification.py::primary_evidence_matches()` + `compare_value_to_evidence()` already implement: canonical metric match, period-compatibility match (not just period-string equality), and value match within tolerance — currently implemented, currently unused by the live verification path.

**9. How should derived claims be verified?**
Only as `VERIFIED` (with a derived/calculated qualifier, not a new top-level status) when every input value the derivation depends on is itself independently `VERIFIED`, and the arithmetic checks out within tolerance — this capability does not currently exist and needs new logic, most likely extending `fcg/constraint_engine.py`/`ConstraintVerifier` rather than building a parallel system (unconfirmed pending a full read of that file — flagged, not assumed).

**10. How should duplicate claims be handled?**
Deduped by `(canonical_metric, canonical_entity, canonical_period, claim_type)`, both client-side (extending `session.ts`'s existing dedup cache key) and server-side (currently absent entirely for `/v1/verify/batch`'s claim list).

**11. What is the smallest safe architecture that connects the extension to the existing verification infrastructure?**
No new architecture — thread the sentence/context and coarse hints from `detect.ts` through the existing `V1VerifyRequest`/`Claim`/`VerificationContext` chain (all of which already have the fields or near-equivalents), replace `core/resolvers.py`'s three weak resolver functions with calls to the three existing strong resolvers (`resolve_company`, `ConceptRegistry`, `parse_period_string`), and wire `core/identity_verification.py`'s comparison into `core/engine.py::verify()`. Every piece already exists in the repository.

**12. What EXACT Phase 3 implementation should Codex perform first?**
Wire `core/identity_verification.py`'s value/concept/period comparison into `core/engine.py::verify()` and extend `core/trust_engine.py`'s `TrustFindings`/`TRUST_RULES` to require a positive value match before `VERIFIED`, together with the corresponding `test_conflicting_evidence...`/`test_...wrong_period...`-style tests at the `/v1/verify` API level (not just at the currently-tested `identity_verification.py` unit level). This is backend-only, requires zero extension changes, cannot regress any currently-passing test (it only makes previously-impossible-to-reach code paths reachable), and is the single change that makes the word "VERIFIED" actually mean what the brief's final principle demands. Entity/metric/period resolver improvements (§23's second P0 item) and the extension context-propagation change (§23's third P0 item) should follow immediately after, in that order, specifically because landing them *before* the value-comparison wiring would let claims start being marked VERIFIED on evidence-tier alone — the exact false-verification failure mode this entire audit is structured to prevent.
