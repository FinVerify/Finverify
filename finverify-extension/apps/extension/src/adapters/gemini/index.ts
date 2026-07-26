import { createUnverifiedStub } from "@/adapters/stub";

// TODO(unverified): see docs/adding-a-provider.md before activating.
export const geminiAdapter = createUnverifiedStub({
  id: "gemini",
  displayName: "Gemini",
  hostnames: ["gemini.google.com"],
});
