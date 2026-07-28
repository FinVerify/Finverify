/**
 * Shared debug-logging gate for provider adapters.
 *
 * The ChatGPT adapter (and the orchestrator that drives it) originally
 * shipped with ~40 unconditional `console.log`/`console.error` calls left
 * over from bring-up debugging. They're genuinely useful when diagnosing
 * why injection stopped working on a real page, so we don't delete them —
 * but they have no business running by default in every user's console on
 * every keystroke of every streamed response.
 *
 * Flip this on from the browser console with:
 *   window.__FINVERIFY_DEBUG__ = true
 * No rebuild required, and it stays off for everyone who hasn't opted in.
 */

declare global {
  interface Window {
    __FINVERIFY_DEBUG__?: boolean;
  }
}

function isDebugEnabled(): boolean {
  try {
    return typeof window !== "undefined" && window.__FINVERIFY_DEBUG__ === true;
  } catch {
    return false;
  }
}

export function adapterDebugLog(...args: unknown[]): void {
  if (isDebugEnabled()) {
    // eslint-disable-next-line no-console
    console.log(...args);
  }
}

export function adapterDebugError(...args: unknown[]): void {
  if (isDebugEnabled()) {
    // eslint-disable-next-line no-console
    console.error(...args);
  }
}
