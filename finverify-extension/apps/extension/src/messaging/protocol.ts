import type { HealthStatus, V1VerifyRequest, V1VerifyResponse } from "@finverify/core";

/**
 * Messages passed between content script and background service worker.
 * All network calls are routed through the background worker so the
 * content script never needs host-page CORS/CSP cooperation — this is
 * purely an extension-runtime concern and has no equivalent in
 * @finverify/core (a VS Code/Desktop/CLI client would just call
 * createHttpTransport() directly with no messaging layer at all).
 *
 * Every request carries a `requestId` so CANCEL_CLAIM can tell the
 * background worker which in-flight fetch to abort, and so a response
 * that arrives after the caller stopped caring can be identified and
 * ignored.
 */
export type ExtensionMessage =
  | { type: "VERIFY_CLAIM"; requestId: string; payload: V1VerifyRequest }
  | { type: "CANCEL_CLAIM"; requestId: string }
  | { type: "CHECK_HEALTH" };

export type ExtensionResponse =
  | { type: "VERIFY_CLAIM_RESULT"; requestId: string; ok: true; data: V1VerifyResponse }
  | { type: "VERIFY_CLAIM_RESULT"; requestId: string; ok: false; error: string; cancelled?: boolean }
  | { type: "HEALTH_RESULT"; ok: true; data: HealthStatus }
  | { type: "HEALTH_RESULT"; ok: false; error: string };
