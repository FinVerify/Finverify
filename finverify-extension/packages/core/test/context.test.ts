import { describe, expect, it } from "vitest";
import { VerificationEngine } from "../src/engine.js";
import { financePlugin } from "../src/plugins/finance/index.js";
import type { V1VerifyResponse } from "../src/types.js";

const response = (request: { question: string; raw_value: number }): V1VerifyResponse => ({
  ...request,
  verified_value: request.raw_value,
  correction_applied: null,
  trust_score: "HIGH",
  trust_color: "#00ff88",
  verification_status: "verified",
  confidence: 0.9,
  reasons: [],
  delta_pct: 0,
  dvl_version: "test",
  timestamp: "test",
});

describe("contextual verification transport", () => {
  it("carries semantic hints and the actual provider identity", async () => {
    const requests: unknown[] = [];
    const engine = new VerificationEngine({
      plugins: [financePlugin],
      transport: {
        verify: async (request) => {
          requests.push(request);
          return response(request);
        },
      },
    });
    const session = engine.createSession({ modelSource: "claude.ai" });
    await session.verify(engine.detectClaims("Apple reported revenue of $94.04 billion in Q3 FY2026."));

    expect(requests).toHaveLength(1);
    expect(requests[0]).toMatchObject({
      model_source: "claude.ai",
      entity_hint: "Apple",
      metric_hint: "Revenue",
      period_hint: "Q3 FY2026",
      context_text: "Apple reported revenue of $94.04 billion in Q3 FY2026.",
    });
  });
});
