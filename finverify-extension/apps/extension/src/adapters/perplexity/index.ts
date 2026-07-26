import { createUnverifiedStub } from "@/adapters/stub";

// TODO(unverified): see docs/adding-a-provider.md before activating.
export const perplexityAdapter = createUnverifiedStub({
  id: "perplexity",
  displayName: "Perplexity",
  hostnames: ["www.perplexity.ai"],
});
