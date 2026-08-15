/**
 * Finance claim detection.
 *
 * TypeScript port of
 *   finverify-terminal/backend/ingestion/transcripts.py::extract_claims()
 * The backend's transcript pipeline already solves "find numeric claims in
 * unstructured financial prose" — any AI chat response is just another
 * blob of unstructured financial prose, so the same regex pipeline
 * applies unchanged. Do not fork these patterns from the backend's; if
 * the backend patterns change, mirror the change here too.
 *
 * This module is intentionally not exported from the package root —
 * consumers interact with the finance plugin through `./index.js`'s
 * `financePlugin` object (the `VerifierPlugin` contract), not with these
 * internals directly.
 */
import type { ExtractedClaim } from "../../types.js";

interface ClaimPattern {
  regex: RegExp;
  claimType: string;
}

// Order matters: earlier patterns claim their matches first. Mirrors the
// backend's CLAIM_PATTERNS list order exactly.
const CLAIM_PATTERNS: ClaimPattern[] = [
  { regex: /\$\s*([\d,.]+)\s*(billion|million|thousand|B|M|K|bn|mn)/gi, claimType: "currency" },
  { regex: /\$\s*([\d,.]+)(?![\d,.])(?!\s*(?:billion|million|thousand|B|M|K|bn|mn))/gi, claimType: "currency_raw" },
  { regex: /([\d,.]+)\s*%/gi, claimType: "percentage" },
  { regex: /([\d,.]+)\s*(?:basis\s*points?|bps)/gi, claimType: "bps" },
  { regex: /(?:grew|growth|increased|rose|up|gained|improved|expanded)\s+([\d,.]+)\s*%/gi, claimType: "growth_pct" },
  { regex: /(?:declined?|decreased?|fell|down|dropped|contracted|narrowed)\s+([\d,.]+)\s*%/gi, claimType: "decline_pct" },
  { regex: /([\d,.]+)\s*(?:million|billion)\s*shares/gi, claimType: "shares" },
  { regex: /EPS\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)/gi, claimType: "eps" },
  { regex: /margin\s*(?:of|was|:)?\s*([\d,.]+)\s*%?/gi, claimType: "margin" },
  { regex: /revenue\s*(?:of|was|:)?\s*\$?\s*([\d,.]+)\s*(billion|million|B|M|bn|mn)?/gi, claimType: "revenue" },
  { regex: /(?:CET1|tier\s*1|capital)\s*(?:ratio)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?/gi, claimType: "ratio" },
  { regex: /(?:return|ROTCE|ROE|ROA)\s*(?:on\s*\w+\s*\w*)?\s*(?:of|was|:)?\s*([\d,.]+)\s*%?/gi, claimType: "return_metric" },
];

const SCALE_MAP: Record<string, number> = {
  billion: 1e9, B: 1e9, bn: 1e9,
  million: 1e6, M: 1e6, mn: 1e6,
  thousand: 1e3, K: 1e3,
};

function inferEntityHint(sentence: string): string | undefined {
  const match = sentence.match(/^\s*(.+?)\s+(?:reported|announced|posted|generated|recorded|had|has|saw|expects|forecast)\b/i);
  if (!match) return undefined;
  const candidate = match[1].replace(/^according to\s+/i, "").replace(/[’']s$/i, "").trim();
  return candidate && !/^(the company|it|they|this company)$/i.test(candidate) ? candidate : undefined;
}

function inferMetricHint(sentence: string, claimType: string): string | undefined {
  const lower = sentence.toLowerCase();
  if (lower.includes("operating margin")) return "Operating Margin";
  if (lower.includes("gross margin")) return "Gross Margin";
  if (lower.includes("net income")) return "Net Income";
  if (lower.includes("operating income")) return "Operating Income";
  if (lower.includes("free cash flow")) return "Free Cash Flow";
  if (claimType === "revenue") return "Revenue";
  if (claimType === "eps") return "Earnings Per Share Diluted";
  if (claimType === "shares") return "Shares Outstanding";
  return undefined;
}

function inferPeriodHint(sentence: string): string | undefined {
  return sentence.match(/\bQ[1-4]\s*(?:FY\s*)?20\d{2}\b|\bFY\s*20\d{2}\b/i)?.[0];
}

/** Mirrors backend's sentence splitter: split on ./!/? followed by
 *  whitespace+uppercase, or on newlines, while preserving decimals like "5.2%". */
function splitSentences(text: string): string[] {
  return text.split(/(?<=[.!?])\s+(?=[A-Z])|\n+/);
}

/**
 * Extract numeric financial claims from arbitrary text. Faithful port of
 * extract_claims(); the only behavioral difference is that we also
 * record the character offset of each match in the *full* text (the
 * backend only needs sentence-local matches since it doesn't highlight
 * inline in a DOM). `claim.domain` is left unset here — the plugin
 * registry stamps it (see plugins/registry.ts) to keep that concern out
 * of the detection logic itself.
 */
export function detectFinanceClaims(text: string): ExtractedClaim[] {
  const claims: ExtractedClaim[] = [];
  const seenMatches = new Set<string>();

  let cursor = 0;
  for (const rawSentence of splitSentences(text)) {
    const sentenceStart = text.indexOf(rawSentence, cursor);
    const sentence = rawSentence.trim();
    cursor = sentenceStart >= 0 ? sentenceStart + rawSentence.length : cursor;
    if (sentence.length < 10) continue;

    for (const { regex, claimType } of CLAIM_PATTERNS) {
      // Reset lastIndex since these regexes are reused across sentences.
      regex.lastIndex = 0;
      let m: RegExpExecArray | null;
      while ((m = regex.exec(sentence)) !== null) {
        try {
          const numStr = m[1]?.replace(/,/g, "");
          if (!numStr) continue;
          let value = parseFloat(numStr);
          if (Number.isNaN(value)) continue;

          let scaleLabel: string | undefined;
          if (m.length > 2 && m[2]) {
            scaleLabel = m[2];
            if (scaleLabel in SCALE_MAP) {
              value *= SCALE_MAP[scaleLabel];
            }
          }

          let bpsOriginal: number | undefined;
          if (claimType === "bps") {
            bpsOriginal = value;
            value = value / 100.0; // 240 bps = 2.40%
          }

          const matchKey = `${sentence.slice(0, 50)}:${m[0]}`;
          if (seenMatches.has(matchKey)) continue;
          seenMatches.add(matchKey);

          const offsetInFullText = sentenceStart >= 0 ? sentenceStart + m.index : -1;
          const matchedText = m[0];

          // Multiple patterns intentionally recognize the same numeric span
          // (for example currency and revenue). Keep the semantic pattern
          // when it overlaps a generic currency match, so one source claim
          // cannot become several verification requests.
          const overlapIndex = claims.findIndex((existing) => {
            const existingEnd = existing.offset + existing.match.length;
            const currentEnd = offsetInFullText + matchedText.length;
            return existing.offset < currentEnd && offsetInFullText < existingEnd && existing.raw_value === value;
          });
          if (overlapIndex >= 0) {
            const existing = claims[overlapIndex];
            const generic = existing.claim_type === "currency" || existing.claim_type === "currency_raw";
            if (generic && claimType !== "currency" && claimType !== "currency_raw") claims.splice(overlapIndex, 1);
            else if (generic) continue;
          }

          claims.push({
            id: `finance:${matchKey}:${claims.length}`,
            domain: "finance",
            sentence: sentence.slice(0, 200),
            raw_value: value,
            claim_type: claimType,
            match: matchedText,
            offset: offsetInFullText,
            bps_original: bpsOriginal,
            scale_label: scaleLabel,
            entity_hint: inferEntityHint(sentence),
            metric_hint: inferMetricHint(sentence, claimType),
            period_hint: inferPeriodHint(sentence),
          });
        } catch {
          continue;
        }

        // Guard against zero-width matches causing infinite loops.
        if (m[0].length === 0) regex.lastIndex++;
      }
    }
  }

  return claims;
}

/** Mirrors build_question_from_claim(): builds a DVL question that avoids
 *  ratio keywords for non-ratio claim types (otherwise DVL's scale_div100
 *  correction false-positives on legitimate values like "154% YoY growth"). */
export function buildFinanceQuestion(claim: Pick<ExtractedClaim, "claim_type" | "bps_original" | "raw_value">): string {
  switch (claim.claim_type) {
    case "growth_pct":
    case "decline_pct":
      return "What was the stated numerical figure?";
    case "margin":
      return "What was the margin value?";
    case "percentage":
      return "What was the numeric value?";
    case "bps": {
      const bpsVal = claim.bps_original ?? claim.raw_value * 100;
      return `What was the basis point change of ${bpsVal} bps?`;
    }
    case "eps":
      return "What was the earnings per share?";
    case "ratio":
    case "return_metric":
      return "What was the financial ratio?";
    case "currency":
      return "What was the financial value in the statement?";
    case "revenue":
      return "What was the revenue figure?";
    case "shares":
      return "What was the share count?";
    default:
      return "What was the financial value?";
  }
}

/** Mirrors widget.js::clientDVL(q, raw) — a deliberately simple,
 *  dependency-free fallback used only when the transport is unreachable. */
export function financeOfflineFallback(question: string, raw: number) {
  const ratioKeywords = ["ratio", "margin", "return", "yield", "growth", "change", "percent", "rate"];
  const isRatio = ratioKeywords.some((k) => question.toLowerCase().includes(k));

  let value = raw;
  let correction: string | null = null;
  let trust: "HIGH" | "MEDIUM" = "HIGH";

  if (isRatio) {
    if (Math.abs(value) > 100) {
      value = value / 100;
      correction = "scale_div100";
      trust = "MEDIUM";
    } else if (Math.abs(value) < 1) {
      value = value * 100;
      correction = "scale_mul100";
      trust = "MEDIUM";
    }
  }

  return { verified_value: value, correction_applied: correction, trust_score: trust };
}
