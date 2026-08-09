"use client";

import React from "react";
import { usePathname } from "next/navigation";

export default function NavModeToggle() {
  const pathname = usePathname();
  const isActive = (path: string) => path === "/" ? pathname === "/" : pathname === path;
  const items = [
    { label: "WORKSPACE", href: "/", active: "bg-t-green/10 text-t-green" },
    { label: "VERIFY", href: "/terminal", active: "bg-t-green/10 text-t-green" },
    { label: "MARKET", href: "/market", active: "bg-t-amber/10 text-t-amber" },
    { label: "RESEARCH", href: "/metrics", active: "bg-t-amber/10 text-t-amber" },
  ];

  return (
    <div className="flex items-center border border-t-border rounded overflow-hidden">
      {items.map((item, index) => (
        <a
          key={item.href}
          href={item.href}
          className={`px-2 py-1 text-[9px] font-mono font-bold uppercase tracking-wider transition-colors sm:px-3 sm:text-[10px] ${
            isActive(item.href)
              ? `${item.active} ${index < items.length - 1 ? "border-r border-t-border" : ""}`
              : `text-t-muted hover:text-t-secondary ${index < items.length - 1 ? "border-r border-t-border" : ""}`
          }`}
        >
          {item.label}
        </a>
      ))}
    </div>
  );
}
