import { createUnverifiedStub } from "@/adapters/stub";

// TODO(unverified): claude.ai's assistant-message markup has not been
// inspected. Do not flip `verified: true` or add claude.ai to
// manifest.json until someone has confirmed real selectors against a
// live conversation. See docs/adding-a-provider.md.
export const claudeAdapter = createUnverifiedStub({
  id: "claude",
  displayName: "Claude",
  hostnames: ["claude.ai"],
});
