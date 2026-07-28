/**
 * Shared DOM-reading helpers for provider adapters.
 *
 * This module holds the parts of the ChatGPT adapter's DOM logic that are
 * NOT actually ChatGPT-specific: safe querying (never throw on a bad
 * selector), a semantic last-resort finder for "the assistant's reply"
 * that only relies on generic chat-UI shape, an aria-label-based toolbar
 * finder, and a fallback-mount helper. Every one of these was previously
 * duplicated inline in `adapters/chatgpt/index.ts`; new adapters (Claude,
 * Gemini, Copilot, Perplexity, and whatever comes after) should reuse them
 * rather than re-implementing the same defensive plumbing per provider.
 *
 * What stays OUT of this file on purpose: any concrete selector string.
 * Selectors are the one thing that's genuinely provider-specific and must
 * be written against real, live markup for that product (see
 * docs/adding-a-provider.md) — this file only provides the scaffolding
 * around them.
 */

import { adapterDebugError, adapterDebugLog } from "@/adapters/shared/log";

/** Runs `root.querySelectorAll(selector)` and degrades to `[]` instead of
 *  throwing if `selector` is malformed (e.g. after a partial vendor markup
 *  change breaks a `:has()`/attribute selector in some browsers). */
export function safeQueryAll<E extends Element = Element>(root: ParentNode, selector: string): E[] {
  try {
    return Array.from(root.querySelectorAll<E>(selector));
  } catch (err) {
    adapterDebugError("[FV-DEBUG] EXCEPTION in safeQueryAll() for selector:", selector, err);
    return [];
  }
}

export interface SemanticCandidateOptions {
  /** CSS selector(s) describing plausible "one conversation turn" containers,
   *  e.g. "article, [role='article'], main div". Kept per-provider since
   *  the generic containers a product uses vary (article vs div vs li). */
  containerSelector: string;
  /** Selector matching a known "this is a user turn" marker, so it can be
   *  excluded. Optional — omit if the provider has no such marker to key
   *  off (the length/shape heuristics below still apply). */
  userTurnSelector?: string;
  minTextLength?: number;
  maxTextLength?: number;
  maxChildren?: number;
}

const DEFAULTS = { minTextLength: 40, maxTextLength: 20_000, maxChildren: 40 };

/**
 * Semantic last-resort: finds elements that look like a substantial,
 * non-input, non-user conversation turn — without depending on any
 * product-specific attribute. Precision is lower than an attribute-based
 * selector (it can pick up a system notice or sidebar text) but it keeps
 * an adapter functional through a markup change instead of going fully
 * dark. Ported from the ChatGPT adapter's `semanticAssistantCandidates`,
 * generalized so any provider can use the same fallback tier.
 */
export function findSemanticTurnCandidates(root: ParentNode, opts: SemanticCandidateOptions): HTMLElement[] {
  const { containerSelector, userTurnSelector, minTextLength, maxTextLength, maxChildren } = { ...DEFAULTS, ...opts };

  const candidates = safeQueryAll<HTMLElement>(root, containerSelector);
  const filtered = candidates.filter((el) => {
    if (el.querySelector("textarea, input")) return false;
    if (el.isContentEditable) return false;
    if (userTurnSelector && el.closest(userTurnSelector)) return false;
    const text = (el.innerText || "").trim();
    return text.length > minTextLength && text.length < maxTextLength && el.children.length < maxChildren;
  });

  adapterDebugLog("[FV-DEBUG] findSemanticTurnCandidates(): candidates=", candidates.length, "after filter=", filtered.length);
  return filtered;
}

/** Finds a native action toolbar by matching button `aria-label`/text
 *  content against known hint substrings (e.g. "copy", "regenerate").
 *  aria-label content is far more stable across a product's redesigns
 *  than class names, per docs/adding-a-provider.md. Searches within
 *  `scopeEl` (typically the nearest turn container). */
export function findToolbarByLabelHints(scopeEl: HTMLElement, labelHints: string[]): HTMLElement | null {
  const buttons = safeQueryAll<HTMLButtonElement>(scopeEl, "button");
  const match = buttons.find((btn) => {
    const label = (btn.getAttribute("aria-label") || btn.textContent || "").toLowerCase();
    return labelHints.some((hint) => label.includes(hint));
  });
  adapterDebugLog("[FV-DEBUG] findToolbarByLabelHints(): matched =", match ?? "NONE", "hints=", labelHints);
  return match?.parentElement ?? null;
}

/** Fallback insertion point for the verification card when no real
 *  toolbar can be located: a marker `<div>` inserted right after the
 *  message, created once and reused on subsequent scans. `markerAttr`
 *  namespaces it per-provider so two adapters never fight over the same
 *  marker if a page somehow matches both (shouldn't happen, but cheap to
 *  guard against). */
export function ensureFallbackMount(messageEl: HTMLElement, markerAttr = "data-finverify-fallback-mount"): HTMLElement {
  const existing = messageEl.parentElement?.querySelector<HTMLElement>(`[${markerAttr}="true"]`);
  if (existing) {
    adapterDebugLog("[FV-DEBUG] ensureFallbackMount(): reusing existing mount node", existing);
    return existing;
  }
  const mount = document.createElement("div");
  mount.setAttribute(markerAttr, "true");
  messageEl.insertAdjacentElement("afterend", mount);
  adapterDebugLog("[FV-DEBUG] ensureFallbackMount(): created new mount node", mount);
  return mount;
}
