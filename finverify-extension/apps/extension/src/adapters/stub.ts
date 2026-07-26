import type { ProviderAdapter } from "@/adapters/types";

/**
 * Produces a stub adapter for a provider we haven't verified selectors
 * against yet. It's intentionally inert: `findMessages` returns `[]`
 * rather than a guessed selector, so if it were ever accidentally
 * activated it would do nothing rather than misfire on unfamiliar markup.
 *
 * To turn a stub into a real adapter: see docs/adding-a-provider.md.
 * Short version — open the product, inspect its actual assistant-message
 * markup, replace the selectors, set `verified: true`, add its origin to
 * manifest.json's content_scripts.matches, and get someone to confirm
 * injection works on a live conversation before merging.
 */
export function createUnverifiedStub(config: {
  id: string;
  displayName: string;
  hostnames: string[];
}): ProviderAdapter {
  return {
    id: config.id,
    displayName: config.displayName,
    verified: false,
    matches: (hostname) => config.hostnames.includes(hostname),
    findMessages: () => [],
    isStreaming: () => false,
    extractText: () => "",
    findToolbar: () => null,
    mountPoint: (messageEl) => messageEl,
  };
}
