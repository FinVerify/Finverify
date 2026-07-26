import { VerificationEngine, financePlugin } from "@finverify/core";
import { createChromeTransport } from "@/messaging/chromeTransport";

/**
 * One engine instance per extension context (content script has its own,
 * background/popup don't need one — background only needs the raw HTTP
 * transport, see background/index.ts).
 *
 * This is the entire integration point between the extension and
 * @finverify/core. Adding a new domain plugin (healthcare, legal,
 * aerospace, climate) to this extension in the future means adding one
 * line to the `plugins` array below — nothing else in the extension
 * changes, since adapters/UI work in terms of @finverify/core's generic
 * `VerifiedClaim`/`EngineEvent` types, not finance-specific ones.
 */
export const engine = new VerificationEngine({
  transport: createChromeTransport("chatgpt.com"),
  plugins: [financePlugin],
});
