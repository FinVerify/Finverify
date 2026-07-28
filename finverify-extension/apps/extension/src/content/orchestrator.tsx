import { createRoot, type Root } from "react-dom/client";
import { resolveAdapter } from "@/adapters/registry";
import type { ProviderAdapter } from "@/adapters/types";
import { adapterDebugError, adapterDebugLog } from "@/adapters/shared/log";
import { InlineBadge } from "@/ui/InlineBadge";

interface TrackedEntry {
  root: Root;
  container: HTMLElement;
  lastText: string;
  anchoredInToolbar: boolean;
}

/**
 * Not a WeakMap: we need to *iterate* this registry every scan to detect
 * messages that have left the DOM (ChatGPT prunes old turns from the DOM
 * on long conversations, and regenerating a response replaces the node
 * entirely). A WeakMap can't be enumerated, so a bounded, actively-pruned
 * Map is the right tool here.
 */
const tracked = new Map<HTMLElement, TrackedEntry>();

function mountBadgeFor(adapter: ProviderAdapter, messageEl: HTMLElement): TrackedEntry {
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] 5. mountBadgeFor() called for messageEl:", messageEl);

  const container = document.createElement("span");
  container.setAttribute("data-finverify-badge", "true");

  const toolbar = adapter.findToolbar(messageEl);
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] 6. adapter.findToolbar() result:", toolbar ? "FOUND" : "NULL", toolbar);

  if (toolbar) {
    toolbar.appendChild(container);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] container appended into real toolbar", toolbar);
  } else {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] 7. no toolbar found — using fallback mount point via adapter.mountPoint()");
    const mountPoint = adapter.mountPoint(messageEl);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] 7b. fallback mount point resolved to:", mountPoint, "same as messageEl?", mountPoint === messageEl);
    mountPoint.appendChild(container);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] container appended into fallback mount point. Is container in document?", document.body.contains(container));
  }

  let root: Root;
  try {
    root = createRoot(container);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] 8. createRoot() succeeded", { container });
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugError("[FV-DEBUG] 10. EXCEPTION in createRoot()", err);
    throw err; // rethrow — behavior unchanged, only observing
  }

  const entry: TrackedEntry = { root, container, lastText: "", anchoredInToolbar: toolbar !== null };
  tracked.set(messageEl, entry);
  return entry;
}

function updateEntry(adapter: ProviderAdapter, messageEl: HTMLElement, entry: TrackedEntry): void {
  // Re-attempt anchoring into the real toolbar if we started in the
  // fallback mount point (message was still streaming when discovered).
  // Moving an existing DOM node preserves its React root/state — no need
  // to unmount/remount, which would cancel in-flight verification.
  if (!entry.anchoredInToolbar) {
    const toolbar = adapter.findToolbar(messageEl);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] 6b. re-attempt findToolbar() in updateEntry():", toolbar ? "FOUND" : "still NULL");
    if (toolbar) {
      toolbar.appendChild(entry.container);
      entry.anchoredInToolbar = true;
      // TEMP DEBUG — remove after diagnosis
      adapterDebugLog("[FV-DEBUG] container re-anchored into real toolbar on a later scan");
    }
  }

  let text: string;
  try {
    text = adapter.extractText(messageEl);
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugError("[FV-DEBUG] 10. EXCEPTION in adapter.extractText()", err);
    throw err; // rethrow — behavior unchanged, only observing
  }

  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] extractText() length:", text.length, "unchanged since last render?", text === entry.lastText);

  if (text === entry.lastText) return; // guard against redundant re-renders
  entry.lastText = text;

  try {
    entry.root.render(<InlineBadge text={text} />);
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] 9. entry.root.render(<InlineBadge/>) called without throwing (does not confirm DOM output — check data-finverify-badge span's childElementCount separately)");
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugError("[FV-DEBUG] 10. EXCEPTION thrown synchronously from root.render()", err);
    throw err; // rethrow — behavior unchanged, only observing
  }
}

function pruneRemoved(): void {
  for (const [messageEl, entry] of tracked) {
    if (!document.body.contains(messageEl)) {
      // TEMP DEBUG — remove after diagnosis
      adapterDebugLog("[FV-DEBUG] pruning tracked entry — messageEl no longer in document", messageEl);
      entry.root.unmount(); // triggers InlineBadge's cleanup effect, cancelling its VerificationSession
      tracked.delete(messageEl);
    }
  }
}

function scan(adapter: ProviderAdapter): void {
  pruneRemoved();

  let messages: HTMLElement[];
  try {
    messages = adapter.findMessages(document);
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugError("[FV-DEBUG] 10. EXCEPTION in adapter.findMessages()", err);
    throw err; // rethrow — behavior unchanged, only observing
  }

  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] 4. adapter.findMessages() returned", messages.length, "message(s)", messages);

  for (const messageEl of messages) {
    const existing = tracked.get(messageEl);
    if (existing) {
      // TEMP DEBUG — remove after diagnosis
      adapterDebugLog("[FV-DEBUG] messageEl already tracked — calling updateEntry()", messageEl);
      updateEntry(adapter, messageEl, existing);
      continue;
    }
    // Mount immediately regardless of streaming state — to a fallback
    // point if no toolbar exists yet — so verification starts on partial
    // text rather than waiting for the whole response.
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] messageEl NOT yet tracked — will mount a new badge", messageEl);
    const entry = mountBadgeFor(adapter, messageEl);
    updateEntry(adapter, messageEl, entry);
  }
}

let scheduled = false;
function scheduleScan(adapter: ProviderAdapter): void {
  if (scheduled) return;
  scheduled = true;
  // requestAnimationFrame coalesces the flood of mutations a streaming
  // response produces into one scan per frame instead of one per token.
  requestAnimationFrame(() => {
    scheduled = false;
    try {
      scan(adapter);
    } catch (err) {
      // TEMP DEBUG — remove after diagnosis
      adapterDebugError("[FV-DEBUG] 10. EXCEPTION escaped scan() inside scheduleScan()'s rAF callback", err);
      throw err; // rethrow — behavior unchanged, only observing
    }
  });
}

export function startOrchestrator(): void {
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] 2. startOrchestrator() entered", { hostname: window.location.hostname });

  const adapter = resolveAdapter(window.location.hostname);
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] 3. resolveAdapter() result:", adapter ? `"${adapter.id}" (verified=${adapter.verified})` : "NULL — no adapter for this hostname");

  if (!adapter) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugLog("[FV-DEBUG] startOrchestrator() exiting early — no adapter resolved, nothing further will run");
    return; // no verified adapter for this page — do nothing
  }

  try {
    scan(adapter);
  } catch (err) {
    // TEMP DEBUG — remove after diagnosis
    adapterDebugError("[FV-DEBUG] 10. EXCEPTION escaped initial synchronous scan() call", err);
    throw err; // rethrow — behavior unchanged, only observing
  }

  const observer = new MutationObserver(() => scheduleScan(adapter));
  // characterData:true matters here: some streaming renderers update a
  // message's text via direct text-node mutation without adding any new
  // elements, which childList/subtree alone would miss.
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] MutationObserver attached to document.body");

  // Belt-and-suspenders safety net: SPA navigation (switching
  // conversations) can occasionally replace large subtrees in ways that
  // don't fire the granular mutations above in every ChatGPT build.
  setInterval(() => scheduleScan(adapter), 4_000);
  // TEMP DEBUG — remove after diagnosis
  adapterDebugLog("[FV-DEBUG] fallback setInterval(4000ms) scheduled");
}
