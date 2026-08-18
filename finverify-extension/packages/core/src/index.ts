// Engine
export { VerificationEngine } from "./engine.js";
export type { VerificationEngineConfig } from "./engine.js";

// Sessions
export { VerificationSession } from "./session.js";

// Events
export { EventBus } from "./events.js";
export type { EngineEvent, EngineEventListener } from "./events.js";

// Transport
export type { VerificationTransport } from "./transport.js";
export { TransportError } from "./transport.js";
export { createHttpTransport } from "./http-transport.js";
export type { HttpTransportOptions } from "./http-transport.js";
export { withRetry } from "./retry.js";
export type { RetryOptions } from "./retry.js";

// Plugins
export { PluginRegistry } from "./plugins/registry.js";
export type { VerifierPlugin, OfflineFallbackResult } from "./plugins/types.js";
export { financePlugin } from "./plugins/finance/index.js";

// Trust display helpers
export { trustPalette, trustIcon, trustLabel, formatValue, TRUST_COLORS } from "./trust.js";

// Semantic verification states (VERIFIED / CONTRADICTED / UNVERIFIED / VERIFICATION UNAVAILABLE)
export {
  claimSemanticState,
  summarizeSemanticStates,
  formatSemanticSummary,
  deriveSemanticOverall,
  semanticPalette,
  semanticIcon,
  semanticLabel,
  semanticExplanation,
} from "./semantic.js";
export type { SemanticState, ResolvedSemanticState, SemanticSummary, SemanticOverall } from "./semantic.js";

// Share / export formatting
export { formatClaimShareText, formatClaimSetShareText } from "./share.js";

// Shared types
export type {
  V1VerifyRequest,
  V1VerifyResponse,
  TrustScore,
  VerificationStatus,
  ExtractedClaim,
  VerifiedClaim,
  HealthStatus,
} from "./types.js";
