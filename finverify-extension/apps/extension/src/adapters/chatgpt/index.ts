import type { ProviderAdapter } from "@/adapters/types";

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
 *      attribute name at all (see `semanticAssistantCandidates`).
 *   3. Every query is wrapped so a thrown DOMException (e.g. from a
 *      malformed selector after a partial API change) degrades to "found
 *      nothing" instead of crashing the whole content script.
 *
 * If injection silently stops working, this is the one file to open.
 */

function safeQueryAll<E extends Element = Element>(root: ParentNode, selector: string): E[] {
  try {
    return Array.from(root.querySelectorAll<E>(selector));
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    console.error("[FV-DEBUG] 10. EXCEPTION in safeQueryAll() for selector:", selector, err);
    return [];
  }
}

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

/** Semantic last resort: a conversation turn that is NOT a user turn and
 *  contains a non-trivial amount of prose. This deliberately does not
 *  depend on any ChatGPT-specific attribute — only on the general shape
 *  a chat UI turn has (substantial text, not an input/textarea, not
 *  editable). It will be less precise than the attribute-based selectors
 *  (may occasionally pick up system/notice text) but keeps the extension
 *  functional through a markup change instead of going fully dark. */
function semanticAssistantCandidates(root: ParentNode): HTMLElement[] {
  const candidates = safeQueryAll<HTMLElement>(root, "article, [role='article'], main div");
  const filtered = candidates.filter((el) => {
    if (el.querySelector("textarea, input")) return false;
    if (el.isContentEditable) return false;
    if (el.closest('[data-message-author-role="user"]')) return false;
    const text = (el.innerText || "").trim();
    // Long enough to plausibly be a full assistant reply, short enough
    // that we're not just grabbing <main> itself.
    return text.length > 40 && text.length < 20_000 && el.children.length < 40;
  });
  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] semanticAssistantCandidates(): candidates=", candidates.length, "after filter=", filtered.length);
  return filtered;
}

const TOOLBAR_BUTTON_LABEL_HINTS = ["copy", "regenerate", "read aloud", "good response", "bad response"];

function findToolbarBySelector(messageEl: HTMLElement): HTMLElement | null {
  const turnContainer = messageEl.closest("article") ?? messageEl.parentElement ?? messageEl;
  // TEMP DEBUG — remove after diagnosis
  console.log(
    "[FV-DEBUG] findToolbarBySelector(): turnContainer resolved via",
    messageEl.closest("article") ? "closest('article')" : messageEl.parentElement ? "parentElement fallback" : "messageEl itself (last resort)",
    turnContainer,
  );

  const buttons = safeQueryAll<HTMLButtonElement>(turnContainer, "button");
  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] findToolbarBySelector(): buttons found in turnContainer scope =", buttons.length, buttons);

  const match = buttons.find((btn) => {
    const label = (btn.getAttribute("aria-label") || btn.textContent || "").toLowerCase();
    return TOOLBAR_BUTTON_LABEL_HINTS.some((hint) => label.includes(hint));
  });

  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] findToolbarBySelector(): matched toolbar button =", match ?? "NONE — no button label matched hints", TOOLBAR_BUTTON_LABEL_HINTS);

  return match?.parentElement ?? null;
}

/** Fallback when no toolbar can be found at all: a container immediately
 *  following the message, built fresh if necessary. Always succeeds. */
function ensureFallbackMount(messageEl: HTMLElement): HTMLElement {
  const existing = messageEl.parentElement?.querySelector<HTMLElement>('[data-finverify-fallback-mount="true"]');
  if (existing) {
    // TEMP DEBUG — remove after diagnosis
    console.log("[FV-DEBUG] ensureFallbackMount(): reusing existing fallback mount node", existing);
    return existing;
  }
  const mount = document.createElement("div");
  mount.setAttribute("data-finverify-fallback-mount", "true");
  messageEl.insertAdjacentElement("afterend", mount);
  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] 7c. ensureFallbackMount(): created NEW fallback mount node after messageEl", mount, "messageEl.parentElement=", messageEl.parentElement);
  return mount;
}

export const chatgptAdapter: ProviderAdapter = {
  id: "chatgpt",
  displayName: "ChatGPT",
  verified: true,

  matches(hostname) {
    const result = hostname === "chatgpt.com" || hostname === "chat.openai.com";
    // TEMP DEBUG — remove after diagnosis
    console.log("[FV-DEBUG] chatgptAdapter.matches() hostname:", hostname, "=>", result);
    return result;
  },

  findMessages(root = document) {
    for (const selector of MESSAGE_SELECTORS) {
      const found = safeQueryAll<HTMLElement>(root, selector);
      // TEMP DEBUG — remove after diagnosis
      console.log("[FV-DEBUG] findMessages(): selector", JSON.stringify(selector), "=>", found.length, "match(es)");
      if (found.length > 0) return found;
    }
    // Every attribute-based selector came up empty — markup has likely
    // changed. Fall back to semantic detection rather than finding nothing.
    // TEMP DEBUG — remove after diagnosis
    console.log("[FV-DEBUG] findMessages(): all attribute-based selectors returned 0 — falling back to semanticAssistantCandidates()");
    return semanticAssistantCandidates(root);
  },

  isStreaming(messageEl) {
    // Best-effort only (see ProviderAdapter doc): if we can't find a
    // settled toolbar yet, assume the message is still streaming rather
    // than extracting from partial text. This can false-positive (treat a
    // genuinely-broken toolbar lookup as "still streaming" forever) which
    // is why the orchestrator caps how long it will wait per message.
    try {
      const streaming = findToolbarBySelector(messageEl) === null;
      // TEMP DEBUG — remove after diagnosis
      console.log("[FV-DEBUG] isStreaming():", streaming);
      return streaming;
    } catch (err) {
      // TEMP DEBUG — remove after diagnosis
      console.error("[FV-DEBUG] 10. EXCEPTION in isStreaming()", err);
      return false; // if even the check throws, don't block forever — proceed
    }
  },

  extractText(messageEl) {
    try {
      const text = (messageEl.innerText || messageEl.textContent || "").trim();
      // TEMP DEBUG — remove after diagnosis
      console.log("[FV-DEBUG] extractText(): length =", text.length);
      return text;
    } catch (err) {
      // TEMP DEBUG — remove after diagnosis
      console.error("[FV-DEBUG] 10. EXCEPTION in extractText()", err);
      return "";
    }
  },

  findToolbar(messageEl) {
    try {
      const result = findToolbarBySelector(messageEl);
      // TEMP DEBUG — remove after diagnosis
      console.log("[FV-DEBUG] 6. findToolbar() public wrapper result:", result ? "FOUND" : "NULL", result);
      return result;
    } catch (err) {
      // TEMP DEBUG — remove after diagnosis
      console.error("[FV-DEBUG] 10. EXCEPTION in findToolbar()", err);
      return null;
    }
  },

  mountPoint(messageEl) {
    try {
      const mount = ensureFallbackMount(messageEl);
      // TEMP DEBUG — remove after diagnosis
      console.log("[FV-DEBUG] 7d. mountPoint() public wrapper result:", mount);
      return mount;
    } catch (err) {
      // TEMP DEBUG — remove after diagnosis
      console.error("[FV-DEBUG] 10. EXCEPTION in mountPoint() — falling back to messageEl itself", err);
      return messageEl;
    }
  },
};
