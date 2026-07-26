import type { ProviderAdapter } from "@/adapters/types";
import { chatgptAdapter } from "@/adapters/chatgpt";
import { claudeAdapter } from "@/adapters/claude";
import { geminiAdapter } from "@/adapters/gemini";
import { copilotAdapter } from "@/adapters/copilot";
import { perplexityAdapter } from "@/adapters/perplexity";

const ALL_ADAPTERS: ProviderAdapter[] = [chatgptAdapter, claudeAdapter, geminiAdapter, copilotAdapter, perplexityAdapter];

/**
 * Resolves the adapter for the current page.
 *
 * `allowUnverified` exists only for local development against a stub
 * (e.g. while building out a new provider's selectors) — it is never set
 * true in the shipped build. Without it, an unverified adapter matching
 * the hostname is treated the same as no adapter at all, so a stub can
 * exist in the registry (for architectural completeness — see the long-
 * term ecosystem vision) without ever actually running on a real page.
 */
export function resolveAdapter(hostname: string, options: { allowUnverified?: boolean } = {}): ProviderAdapter | null {
  const candidate = ALL_ADAPTERS.find((adapter) => adapter.matches(hostname));
  if (!candidate) return null;
  if (!candidate.verified && !options.allowUnverified) return null;
  return candidate;
}

export function listAdapters(): readonly ProviderAdapter[] {
  return ALL_ADAPTERS;
}
