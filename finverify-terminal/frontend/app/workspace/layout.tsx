import type { Metadata } from "next";
import { ConnectionProvider } from "@/lib/connection";

export const metadata: Metadata = {
  title: "FinVerify — Intelligence Workspace",
  description:
    "Always-on financial intelligence workspace with DVL-verified data, real-time market monitoring, and integrity scoring.",
};

/**
 * WorkspaceLayout — Dedicated layout for the Intelligence Workspace.
 * Provides a true h-screen, no-page-scroll frame separate from the root
 * layout's Terminal-oriented chrome (header + TickerBar).
 * Per §3.1 of UI_IMPLEMENTATION_PLAN.md.
 */
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ConnectionProvider>
      <div className="h-screen w-screen overflow-hidden flex flex-col bg-t-bg">
        {children}
      </div>
    </ConnectionProvider>
  );
}
