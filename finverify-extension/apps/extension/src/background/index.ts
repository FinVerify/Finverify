/**
 * Background service worker (MV3).
 *
 * This is intentionally thin: it owns the requestId -> AbortController
 * bookkeeping needed to support CANCEL_CLAIM (a chrome-extension-specific
 * concern — there's no equivalent in @finverify/core, since a Node-based
 * client would just pass its own AbortSignal straight into
 * transport.verify()) and nothing else. All retry/backoff/timeout logic
 * is @finverify/core's createHttpTransport — the background worker calls
 * it directly since it (unlike the content script) has real fetch access
 * with no CORS/CSP restriction from the host page.
 */
import { createHttpTransport, TransportError } from "@finverify/core";
import type { ExtensionMessage, ExtensionResponse } from "@/messaging/protocol";

const transport = createHttpTransport();

/** requestId → controller for the in-flight fetch backing it. */
const inFlight = new Map<string, AbortController>();

async function handleVerifyClaim(message: ExtensionMessage & { type: "VERIFY_CLAIM" }): Promise<ExtensionResponse> {
  const controller = new AbortController();
  inFlight.set(message.requestId, controller);

  try {
    const data = await transport.verify(message.payload, { signal: controller.signal });
    return { type: "VERIFY_CLAIM_RESULT", requestId: message.requestId, ok: true, data };
  } catch (err) {
    if (err instanceof TransportError) {
      return {
        type: "VERIFY_CLAIM_RESULT",
        requestId: message.requestId,
        ok: false,
        error: err.message,
        cancelled: err.cancelled,
      };
    }
    const messageText = err instanceof Error ? err.message : "Unknown error";
    return { type: "VERIFY_CLAIM_RESULT", requestId: message.requestId, ok: false, error: messageText };
  } finally {
    inFlight.delete(message.requestId);
  }
}

function handleCancelClaim(message: ExtensionMessage & { type: "CANCEL_CLAIM" }): void {
  inFlight.get(message.requestId)?.abort();
  inFlight.delete(message.requestId);
}

async function handleCheckHealth(): Promise<ExtensionResponse> {
  try {
    if (!transport.checkHealth) throw new Error("Transport does not support health checks");
    const data = await transport.checkHealth();
    return { type: "HEALTH_RESULT", ok: true, data };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend unreachable";
    return { type: "HEALTH_RESULT", ok: false, error: message };
  }
}

chrome.runtime.onMessage.addListener((message: ExtensionMessage, _sender, sendResponse) => {
  if (message.type === "VERIFY_CLAIM") {
    handleVerifyClaim(message).then(sendResponse);
    return true; // keep the message channel open for the async response
  }
  if (message.type === "CANCEL_CLAIM") {
    handleCancelClaim(message);
    return false; // fire-and-forget
  }
  if (message.type === "CHECK_HEALTH") {
    handleCheckHealth().then(sendResponse);
    return true;
  }
  return false;
});
