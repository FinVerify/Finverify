/**
 * Provider Adapter contract.
 *
 * This is the seam the whole "FinVerify ecosystem" vision depends on: the
 * verification engine and UI layer talk ONLY to this interface. Adding a
 * new AI surface (Claude, Gemini, Copilot, a future one nobody's built yet)
 * means writing one adapter — nothing in src/verification or src/ui should
 * ever import from src/adapters/<provider> directly.
 *
 * Design constraints baked into this interface, and why:
 *
 * - `findMessages` returns HTMLElement[], not a single element — providers
 *   render conversations differently, so "give me all current assistant
 *   turns" is the only operation guaranteed to make sense everywhere.
 *
 * - `isStreaming` is a *best-effort* signal, not a guarantee. Every
 *   provider's streaming indicator is unstable, private DOM state. Adapters
 *   must degrade to "assume settled" rather than throwing when they can't
 *   tell — a false "not streaming" costs us a slightly stale extraction;
 *   a thrown error costs us the whole message.
 *
 * - `extractText` returns plain text, not markdown/HTML. The verification
 *   engine's claim extractor is a regex pipeline ported from the backend's
 *   transcript parser (see verification/claimExtractor.ts) and expects
 *   plain financial prose, not markup.
 *
 * - Adapters are pure DOM readers. They never call the verification API,
 *   never render UI, never mutate the host page beyond what `mount()`
 *   explicitly asks for. Keeping that boundary is what makes it possible
 *   to unit-test the verification engine with zero DOM at all.
 */

export interface ProviderAdapter {
  /** Stable identifier, e.g. "chatgpt". Used as a cache-key namespace and
   *  sent as `model_source` on verification requests. */
  readonly id: string;
  readonly displayName: string;

  /** Whether this adapter's selectors have actually been exercised against
   *  the live product. The registry (adapters/registry.ts) refuses to
   *  activate an adapter with `verified: false` unless explicitly opted
   *  into via dev-mode — a guessed selector set that silently no-ops (or
   *  worse, misfires) on a product nobody tested it against is worse than
   *  the feature not existing yet. Flip this once someone has actually
   *  loaded the extension against the real product and confirmed
   *  `findMessages`/`findToolbar`/`extractText` behave correctly. */
  readonly verified: boolean;

  /** Whether this adapter should activate on the current page. */
  matches(hostname: string): boolean;

  /** All assistant message elements currently in the DOM, both old and new.
   *  Callers are responsible for tracking which ones they've already
   *  processed (see verification/processedRegistry.ts) — adapters are
   *  stateless on purpose, so they can't get out of sync with the caller. */
  findMessages(root?: ParentNode): HTMLElement[];

  /** Best-effort signal for "this message is still being generated".
   *  MUST NOT throw. MUST default to `false` (i.e. "treat as settled")
   *  when the provider gives no reliable signal, per the module doc above. */
  isStreaming(messageEl: HTMLElement): boolean;

  /** Plain-text content of a message, for claim extraction. */
  extractText(messageEl: HTMLElement): string;

  /** Finds (or best-effort locates) the message's native action toolbar
   *  (Copy/Regenerate/etc.), used as an anchor to inject an inline badge.
   *  Returns null if none can be found — callers must handle that by
   *  falling back to `mountPoint`, not by giving up on the message. */
  findToolbar(messageEl: HTMLElement): HTMLElement | null;

  /** Fallback insertion point for the verification card when no toolbar
   *  is available to anchor an inline badge to. Must always return an
   *  element (never null) — worst case, the message element itself. */
  mountPoint(messageEl: HTMLElement): HTMLElement;
}

/** A message handle the orchestrator tracks across observer callbacks.
 *  Kept provider-agnostic so content/orchestrator.ts never branches on
 *  which adapter produced it. */
export interface TrackedMessage {
  element: HTMLElement;
  adapterId: string;
}
