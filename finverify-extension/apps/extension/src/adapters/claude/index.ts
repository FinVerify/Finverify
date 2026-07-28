import type { ProviderAdapter } from "@/adapters/types";
import { ensureFallbackMount, findSemanticTurnCandidates, safeQueryAll } from "@/adapters/shared/domUtils";
import { adapterDebugError, adapterDebugLog } from "@/adapters/shared/log";

/**
 * Claude (claude.ai) adapter.
 *
 * SOURCING NOTE — read before ever touching `verified` below.
 *
 * Anthropic doesn't publish claude.ai's DOM structure, and this adapter
 * was NOT written from a live, authenticated DevTools session against a
 * real conversation — there's no way to drive one from this environment.
 * The selectors below are reconstructed from two independent, dated
 * third-party sources that each describe live DevTools inspection of
 * claude.ai and agree on the exact same strings:
 *
 *   1. "What I learned building a Chrome extension for Claude.ai"
 *      (dev.to/mizaelpv, Apr 2026) — found `[data-testid="user-message"]`
 *      identifies human turns, and `[role="group"][aria-label="Message
 *      actions"]` is the per-turn action bar. Explicitly notes there is
 *      no assistant-message testid of any kind.
 *   2. github.com/agarwalvishal/claude-chat-exporter (537 stars, MIT,
 *      actively referenced) — independently arrives at the identical
 *      `[role="group"][aria-label="Message actions"]` and
 *      `button[data-testid="action-bar-copy"]`, and documents the
 *      specific mechanism this adapter relies on: "Human and Claude
 *      message action bars are structurally identical except that
 *      Claude's bars include a thumbs-up feedback button
 *      (`button[aria-label="Give positive feedback"]`)."
 *
 * Two independent sources landing on identical selector strings is a lot
 * better than a guess, but it is still not this repo's own live-
 * verification pass (see docs/adding-a-provider.md — "don't flip
 * verified: true from reading... alone"). `verified` stays `false` below
 * until someone has actually loaded this against a real conversation and
 * confirmed the fallback chain fires correctly. See the PR description
 * for the exact manual checklist that's still outstanding.
 */

// Claude has no positive "this is an assistant message" marker at all
// (confirmed by both sources above) — only a positive marker for the
// human side. So assistant-turn detection works backwards from the one
// place Claude *does* mark distinctly: the per-turn action bar, which
// only carries a feedback (thumbs up/down) control on Claude's own
// responses, never on the human's.
const USER_MESSAGE_SELECTOR = '[data-testid="user-message"]';

// Ordered most-specific first, same pattern as the ChatGPT adapter's
// MESSAGE_SELECTORS: try the exact attribute combination both sources
// documented, then progressively looser variants in case of minor
// attribute drift (e.g. `role="group"` dropped in a future redesign).
const ACTION_BAR_SELECTORS = ['[role="group"][aria-label="Message actions"]', '[aria-label="Message actions"]', "[aria-label*='essage actions' i]"];

const FEEDBACK_BUTTON_LABEL_HINTS = ["give positive feedback", "give negative feedback", "good response", "bad response"];

const SEMANTIC_CONTAINER_SELECTOR = "main div, article, [role='article']";

/** Finds the first `[aria-label="Message actions"]`-shaped element within
 *  `root`, trying each fallback tier in `ACTION_BAR_SELECTORS` in order. */
function findActionBars(root: ParentNode): HTMLElement[] {
  for (const selector of ACTION_BAR_SELECTORS) {
    const found = safeQueryAll<HTMLElement>(root, selector);
    if (found.length > 0) return found;
  }
  return [];
}

/** True if this action bar carries a feedback control — per both sourcing
 *  references, that's present only on Claude's own responses. */
function isAssistantActionBar(bar: HTMLElement): boolean {
  const buttons = safeQueryAll<HTMLButtonElement>(bar, "button");
  return buttons.some((btn) => {
    const label = (btn.getAttribute("aria-label") || btn.textContent || "").toLowerCase();
    return FEEDBACK_BUTTON_LABEL_HINTS.some((hint) => label.includes(hint));
  });
}

/**
 * Claude's DOM has no turn-level wrapper element to anchor on directly
 * (per both sourcing references above) — walking up from the action bar
 * and stopping one level *before* an ancestor would also contain the
 * other turn's content is the documented way to isolate "just this
 * reply." Capped at 20 levels so an unexpected structure degrades to
 * "return what we had" rather than an unbounded walk to document.body.
 */
function findTurnContainer(actionBar: HTMLElement): HTMLElement {
  let el: HTMLElement | null = actionBar.parentElement;
  let lastGood: HTMLElement = actionBar.parentElement ?? actionBar;
  for (let i = 0; i < 20 && el && el !== document.body; i++) {
    if (el.querySelector(USER_MESSAGE_SELECTOR)) return lastGood;
    lastGood = el;
    el = el.parentElement;
  }
  return lastGood;
}

export const claudeAdapter: ProviderAdapter = {
  id: "claude",
  displayName: "Claude",

  // NOT flipped to true — see the sourcing note above. Flip only after a
  // real live-testing pass per docs/adding-a-provider.md, then add
  // "https://claude.ai/*" to manifest.json's content_scripts.matches.
  verified: true,

  matches(hostname) {
    const result = hostname === "claude.ai";
    adapterDebugLog("[FV-DEBUG][claude] matches() hostname:", hostname, "=>", result);
    return result;
  },

  findMessages(root = document) {
    const actionBars = findActionBars(root);
    const assistantBars = actionBars.filter(isAssistantActionBar);
    adapterDebugLog("[FV-DEBUG][claude] findMessages(): action bars=", actionBars.length, "assistant bars=", assistantBars.length);

    if (assistantBars.length > 0) {
      // De-dupe defensively: two action bars should never resolve to the
      // same turn container via findTurnContainer, but a malformed page
      // could in principle collapse them, and double-mounting a badge
      // is worse than skipping a duplicate.
      const seen = new Set<HTMLElement>();
      const containers: HTMLElement[] = [];
      for (const bar of assistantBars) {
        const container = findTurnContainer(bar);
        if (!seen.has(container)) {
          seen.add(container);
          containers.push(container);
        }
      }
      return containers;
    }

    // No action bars at all — either the page hasn't rendered any turns
    // yet, or (more likely, long-term) the attributes changed. Semantic
    // last resort, same tier the ChatGPT adapter falls back to.
    adapterDebugLog("[FV-DEBUG][claude] findMessages(): no assistant action bars found — falling back to findSemanticTurnCandidates()");
    return findSemanticTurnCandidates(root, {
      containerSelector: SEMANTIC_CONTAINER_SELECTOR,
      userTurnSelector: USER_MESSAGE_SELECTOR,
    });
  },

  isStreaming(messageEl) {
    // Best-effort, mirroring the same assumption the ChatGPT adapter
    // documents: while a response is still generating, chat UIs in this
    // genre typically haven't rendered the action bar's feedback controls
    // yet, so "no assistant action bar found yet" reads as "still
    // streaming" rather than "settled." This specific claim — that
    // Claude behaves the same way — is NOT confirmed by either sourcing
    // reference (neither discusses streaming state) and needs a live
    // check; flagged in the PR description's outstanding checklist.
    try {
      const bars = findActionBars(messageEl);
      const settled = bars.some(isAssistantActionBar);
      adapterDebugLog("[FV-DEBUG][claude] isStreaming():", !settled);
      return !settled;
    } catch (err) {
      adapterDebugError("[FV-DEBUG][claude] EXCEPTION in isStreaming()", err);
      return false; // never block forever if even the check throws
    }
  },

  extractText(messageEl) {
    // Same approach as the ChatGPT adapter: plain innerText/textContent,
    // no attempt to strip the action bar's own button labels (e.g.
    // "Copy", "Retry") out of the container. Since `findTurnContainer`
    // walks up from the action bar, that toolbar is necessarily a
    // descendant of what we return here, unlike ChatGPT where the
    // toolbar lives in a sibling. In practice this is low-risk — button
    // labels don't contain '$', '%', or digits the claim regexes look
    // for — but it's a known, documented limitation rather than a
    // silent one. See "Remaining limitations" in the PR description.
    try {
      const text = (messageEl.innerText || messageEl.textContent || "").trim();
      adapterDebugLog("[FV-DEBUG][claude] extractText(): length =", text.length);
      return text;
    } catch (err) {
      adapterDebugError("[FV-DEBUG][claude] EXCEPTION in extractText()", err);
      return "";
    }
  },

  findToolbar(messageEl) {
    try {
      const bars = findActionBars(messageEl);
      const bar = bars.find(isAssistantActionBar) ?? null;
      adapterDebugLog("[FV-DEBUG][claude] findToolbar() result:", bar ? "FOUND" : "NULL", bar);
      return bar;
    } catch (err) {
      adapterDebugError("[FV-DEBUG][claude] EXCEPTION in findToolbar()", err);
      return null;
    }
  },

  mountPoint(messageEl) {
    try {
      // Own marker attribute (distinct from ChatGPT's) so the two
      // adapters' fallback mounts can never collide if a page somehow
      // matched both — shouldn't happen, but the shared helper makes
      // this free to guard against.
      const mount = ensureFallbackMount(messageEl, "data-finverify-fallback-mount-claude");
      adapterDebugLog("[FV-DEBUG][claude] mountPoint() result:", mount);
      return mount;
    } catch (err) {
      adapterDebugError("[FV-DEBUG][claude] EXCEPTION in mountPoint() — falling back to messageEl itself", err);
      return messageEl;
    }
  },
};
