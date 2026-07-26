import type { VerifierPlugin } from "../types.js";
import { detectFinanceClaims, buildFinanceQuestion, financeOfflineFallback } from "./detect.js";

/**
 * The finance domain verifier plugin — numeric/financial claim detection
 * (currency, percentages, bps, margins, EPS, ratios, etc.) plus DVL
 * question-building. This is the reference implementation every future
 * domain plugin (healthcare, legal, aerospace, climate) should follow the
 * shape of: detection + question-building + an optional offline fallback,
 * nothing else.
 */
export const financePlugin: VerifierPlugin = {
  id: "finance",
  displayName: "Finance",
  detectClaims: detectFinanceClaims,
  buildQuestion: buildFinanceQuestion,
  offlineFallback: financeOfflineFallback,
};
