import { createUnverifiedStub } from "@/adapters/stub";

// TODO(unverified): see docs/adding-a-provider.md before activating.
export const copilotAdapter = createUnverifiedStub({
  id: "copilot",
  displayName: "Copilot",
  hostnames: ["copilot.microsoft.com"],
});
