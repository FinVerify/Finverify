import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FinVerify — Intelligence Workspace",
  description:
    "Always-on financial intelligence workspace with DVL-verified data, real-time market monitoring, and integrity scoring.",
};

/**
 * WorkspaceLayout — Now inherits root layout's header + TickerBar.
 * Applies overflow-hidden so the workspace fills remaining viewport
 * without page-level scroll, while still using the shared chrome.
 */
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
