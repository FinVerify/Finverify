import type { ProviderAdapter } from "@/adapters/types";
import { ensureFallbackMount, findSemanticTurnCandidates, findToolbarByLabelHints, safeQueryAll } from "@/adapters/shared/domUtils";
import { adapterDebugError, adapterDebugLog } from "@/adapters/shared/log";

/**
 * ChatGPT adapter.
 *
 * Every selector below is reverse-engineered from ChatGPT's current
 * markup and will eventually break when OpenAI changes it — that's
 * unavoidable for any DOM-based integration. What we control is how
 * *gracefully* it breaks:
 *
 *   1. Multiple fallback selectors, tried in order, most-specific first.
 *   2. A semantic last resort that doesn't depend on any particular
 *      attribute name at all (see `adapters/shared/domUtils`'s
 *      `findSemanticTurnCandidates`).
 *   3. Every query is wrapped so a thrown DOMException (e.g. from a
 *      malformed selector after a partial API change) degrades to "found
 *      nothing" instead of crashing the whole content script.
 *
 * The defensive plumbing (safe querying, semantic fallback, label-based
 * toolbar matching, fallback mount points) lives in `adapters/shared/`
 * now, since it isn't actually ChatGPT-specific — only the selector
 * strings and hint lists below are. If injection silently stops working,
 * this is still the one file to open first.
 */

// Tried in order; first selector that returns results wins. Kept as an
// ordered list (not a single combined selector) so we know *which* fallback
// fired, which matters when deciding how much to trust the result.
const MESSAGE_SELECTORS = [
  '[data-message-author-role="assistant"]',
  // Older/alternate markup seen in some ChatGPT builds.
  'div[data-testid^="conversation-turn"] [data-message-author-role="assistant"]',
  // Group/turn wrapper without the inner role marker.
  'article:has([data-message-author-role="assistant"])',
];

const SEMANTIC_CONTAINER_SELECTOR = "article, [role='article'], main div";
const SEMANTIC_USER_TURN_SELECTOR = '[data-message-author-role="user"]';

const TOOLBAR_BUTTON_LABEL_HINTS = ["copy", "regenerate", "read aloud", "good response", "bad response"];

function findToolbarBySelector(messageEl: HTMLElement): HTMLElement | null {
  const turnContainer = messageEl.closest("article") ?? messageEl.parentElement ?? messageEl;
  adapterDebugLog(
    "[FV-DEBUG] findToolbarBySelector(): turnContainer resolved via",
    messageEl.closest("article") ? "closest('article')" : messageEl.parentElement ? "parentElement fallback" : "messageEl itself (last resort)",
    turnContainer,
  );
  return findToolbarByLabelHints(turnContainer as HTMLElement, TOOLBAR_BUTTON_LABEL_HINTS);
}

export const chatgptAdapter: ProviderAdapter = {
  id: "chatgpt",
  displayName: "ChatGPT",
  verified: true,

  matches(hostname) {
    const result = hostname === "chatgpt.com" || hostname === "chat.openai.com";
    adapterDebugLog("[FV-DEBUG] chatgptAdapter.matches() hostname:", hostname, "=>", result);
    return result;
  },

  findMessages(root = document) {
    for (const selector of MESSAGE_SELECTORS) {
      const found = safeQueryAll<HTMLElement>(root, selector);
      adapterDebugLog("[FV-DEBUG] findMessages(): selector", JSON.stringify(selector), "=>", found.length, "match(es)");
      if (found.length > 0) return found;
    }
    // Every attribute-based selector came up empty — markup has likely
    // changed. Fall back to semantic detection rather than finding nothing.
    adapterDebugLog("[FV-DEBUG] findMessages(): all attribute-based selectors returned 0 — falling back to findSemanticTurnCandidates()");
    return findSemanticTurnCandidates(root, {
      containerSelector: SEMANTIC_CONTAINER_SELECTOR,
      userTurnSelector: SEMANTIC_USER_TURN_SELECTOR,
    });
  },

  isStreaming(messageEl) {
    // Best-effort only (see ProviderAdapter doc): if we can't find a
    // settled toolbar yet, assume the message is still streaming rather
    // than extracting from partial text. This can false-positive (treat a
    // genuinely-broken toolbar lookup as "still streaming" forever) which
    // is why the orchestrator caps how long it will wait per message.
    try {
      const streaming = findToolbarBySelector(messageEl) === null;
      adapterDebugLog("[FV-DEBUG] isStreaming():", streaming);
      return streaming;
    } catch (err) {
      adapterDebugError("[FV-DEBUG] EXCEPTION in isStreaming()", err);
      return false; // if even the check throws, don't block forever — proceed
    }
  },

  extractText(messageEl) {
    try {
      const text = (messageEl.innerText || messageEl.textContent || "").trim();
      adapterDebugLog("[FV-DEBUG] extractText(): length =", text.length);
      return text;
    } catch (err) {
      adapterDebugError("[FV-DEBUG] EXCEPTION in extractText()", err);
      return "";
    }
  },

  findToolbar(messageEl) {
    try {
      const result = findToolbarBySelector(messageEl);
      adapterDebugLog("[FV-DEBUG] findToolbar() public wrapper result:", result ? "FOUND" : "NULL", result);
      return result;
    } catch (err) {
      adapterDebugError("[FV-DEBUG] EXCEPTION in findToolbar()", err);
      return null;
    }
  },

  mountPoint(messageEl) {
    try {
      const mount = ensureFallbackMount(messageEl, "data-finverify-fallback-mount");
      adapterDebugLog("[FV-DEBUG] mountPoint() public wrapper result:", mount);
      return mount;
    } catch (err) {
      adapterDebugError("[FV-DEBUG] EXCEPTION in mountPoint() — falling back to messageEl itself", err);
      return messageEl;
    }
  },
};
