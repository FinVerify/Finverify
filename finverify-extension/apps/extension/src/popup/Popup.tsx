import { useEffect, useState } from "react";
import type { HealthStatus } from "@finverify/core";
import { engine } from "@/engineInstance";

type Status = { kind: "loading" } | { kind: "ok"; data: HealthStatus } | { kind: "error"; message: string };

export function Popup() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    engine
      .checkHealth()
      .then((data) => setStatus({ kind: "ok", data }))
      .catch((err) => setStatus({ kind: "error", message: err instanceof Error ? err.message : "Unreachable" }));
  }, []);

  return (
    <div className="fv-p-4 fv-font-mono fv-text-t-primary fv-bg-t-bg">
      <div className="fv-mb-3 fv-flex fv-items-center fv-gap-2">
        <span className="fv-text-t-green fv-font-bold fv-text-sm">FinVerify</span>
        <span className="fv-text-[10px] fv-text-t-secondary">v0.3.0</span>
      </div>

      <div
        className="fv-rounded-md fv-border fv-border-t-border fv-p-3 fv-text-xs"
        role="status"
        aria-live="polite"
      >
        {status.kind === "loading" && <span className="fv-text-t-secondary">Checking backend…</span>}
        {status.kind === "ok" && (
          <div className="fv-flex fv-flex-col fv-gap-1">
            <Row label="DVL engine" value={status.data.dvl} ok={status.data.dvl === "online"} />
            <Row label="LLM inference" value={status.data.llm} ok={status.data.llm === "online"} />
            <Row label="Model" value={status.data.model} ok />
          </div>
        )}
        {status.kind === "error" && (
          <div className="fv-text-t-red">
            Backend unreachable — verification will fall back to a client-side heuristic.
            <div className="fv-mt-1 fv-text-[10px] fv-text-t-muted">{status.message}</div>
          </div>
        )}
      </div>

      <p className="fv-mt-3 fv-text-[10px] fv-leading-relaxed fv-text-t-secondary">
        Open a ChatGPT conversation and look for a small colored dot next to any assistant reply — that's FinVerify
        checking its numbers against the DVL. Click it to expand the details.
      </p>
    </div>
  );
}

function Row({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="fv-flex fv-items-center fv-justify-between">
      <span className="fv-text-t-secondary">{label}</span>
      <span style={{ color: ok ? "#00ff88" : "#f87171" }}>{value}</span>
    </div>
  );
}
