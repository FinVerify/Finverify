import "@/content/index.css";
import { startOrchestrator } from "@/content/orchestrator";

// TEMP DEBUG — remove after diagnosis
console.log("[FV-DEBUG] 1. content script loaded", {
  href: window.location.href,
  hostname: window.location.hostname,
  readyState: document.readyState,
  timestamp: Date.now(),
});

if (document.readyState === "loading") {
  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] document still loading — deferring startOrchestrator() to DOMContentLoaded");
  document.addEventListener("DOMContentLoaded", () => {
    // TEMP DEBUG — remove after diagnosis
    console.log("[FV-DEBUG] DOMContentLoaded fired — calling startOrchestrator()");
    startOrchestrator();
  });
} else {
  // TEMP DEBUG — remove after diagnosis
  console.log("[FV-DEBUG] document already ready — calling startOrchestrator() immediately");
  startOrchestrator();
}
