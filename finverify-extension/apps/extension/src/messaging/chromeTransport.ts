import type { HealthStatus, V1VerifyRequest, V1VerifyResponse, VerificationTransport } from "@finverify/core";
import { TransportError } from "@finverify/core";
import type { ExtensionMessage, ExtensionResponse } from "@/messaging/protocol";

function newRequestId(): string {
  return `fv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * The extension's one and only implementation of @finverify/core's
 * `VerificationTransport` interface. This is the entire "extension-
 * specific" part of getting a claim verified — everything upstream of
 * this (retry/backoff, dedup, batching, cancellation bookkeeping) is
 * handled generically by the engine in @finverify/core.
 */
export function createChromeTransport(defaultModelSource: string): VerificationTransport {
  return {
    verify(request: V1VerifyRequest, options?: { signal?: AbortSignal }): Promise<V1VerifyResponse> {
      const requestId = newRequestId();
      const fullRequest: V1VerifyRequest = { model_source: defaultModelSource, ...request };

      const promise = new Promise<V1VerifyResponse>((resolve, reject) => {
        chrome.runtime.sendMessage(
          { type: "VERIFY_CLAIM", requestId, payload: fullRequest } satisfies ExtensionMessage,
          (response: ExtensionResponse) => {
            if (chrome.runtime.lastError) {
              reject(new TransportError(chrome.runtime.lastError.message ?? "Extension messaging error", true));
              return;
            }
            if (response.type !== "VERIFY_CLAIM_RESULT") return;
            if (response.ok) {
              resolve(response.data);
            } else {
              reject(new TransportError(response.error, !response.cancelled, response.cancelled ?? false));
            }
          },
        );
      });

      // Cooperate with the caller's AbortSignal by forwarding cancellation
      // to the background worker, which owns the actual in-flight fetch.
      options?.signal?.addEventListener(
        "abort",
        () => {
          chrome.runtime.sendMessage({ type: "CANCEL_CLAIM", requestId } satisfies ExtensionMessage);
        },
        { once: true },
      );

      return promise;
    },

    checkHealth(): Promise<HealthStatus> {
      return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: "CHECK_HEALTH" } satisfies ExtensionMessage, (response: ExtensionResponse) => {
          if (chrome.runtime.lastError) {
            reject(new TransportError(chrome.runtime.lastError.message ?? "Extension messaging error", true));
            return;
          }
          if (response.type !== "HEALTH_RESULT") return;
          if (response.ok) resolve(response.data);
          else reject(new TransportError(response.error, true));
        });
      });
    },
  };
}
