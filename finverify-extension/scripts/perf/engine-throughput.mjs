const CORE_DIST = new URL("../../packages/core/dist/index.js", import.meta.url);

async function main() {
  const { VerificationEngine, financePlugin } = await import(CORE_DIST.href);

  // --- Claim extraction throughput (pure regex, no network) ---
  const sampleSentence =
    "Revenue grew 12.5% to $94.9 billion, with EPS of $1.42 beating estimates. " +
    "Operating margin was 22.1% while the CET1 ratio held at 13.4%. ";
  const longText = sampleSentence.repeat(50); // ~7KB, roughly a long ChatGPT response

  const engine = new VerificationEngine({
    transport: { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "bench", timestamp: "" }) },
    plugins: [financePlugin],
  });

  const extractionIterations = 200;
  const extractStart = performance.now();
  let totalClaims = 0;
  for (let i = 0; i < extractionIterations; i++) {
    totalClaims += engine.detectClaims(longText).length;
  }
  const extractMs = performance.now() - extractStart;
  const claimsPerRun = totalClaims / extractionIterations;

  console.log("=== Claim extraction throughput ===");
  console.log(`Input size: ${longText.length} chars (~50x a dense financial paragraph)`);
  console.log(`Claims found per run: ${claimsPerRun}`);
  console.log(`${extractionIterations} extraction runs: ${extractMs.toFixed(1)}ms total, ${(extractMs / extractionIterations).toFixed(3)}ms/run`);
  console.log();

  // --- Engine throughput: claims/sec through a session at varying concurrency ---
  console.log("=== Session verification throughput (mock transport, ~2ms simulated latency) ===");
  const claims = engine.detectClaims(longText);

  for (const concurrency of [1, 3, 10]) {
    const latencyEngine = new VerificationEngine({
      transport: {
        verify: async (r) => {
          await new Promise((resolve) => setTimeout(resolve, 2));
          return { ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "bench", timestamp: "" };
        },
      },
      plugins: [financePlugin],
      concurrency,
    });
    // Vary raw_value per claim so dedup doesn't collapse the benchmark
    // into a single request (which would make every concurrency setting
    // look identical).
    const uniqueClaims = claims.map((c, i) => ({ ...c, raw_value: c.raw_value + i * 0.0001 }));

    const session = latencyEngine.createSession();
    const start = performance.now();
    await session.verify(uniqueClaims);
    const elapsed = performance.now() - start;
    console.log(`concurrency=${concurrency}: ${uniqueClaims.length} claims in ${elapsed.toFixed(1)}ms (${(uniqueClaims.length / (elapsed / 1000)).toFixed(0)} claims/sec)`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
