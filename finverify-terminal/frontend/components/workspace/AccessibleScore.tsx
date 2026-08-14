"use client";

import React from "react";

interface AccessibleScoreProps {
  label: string;
  value: number;
  valueText: string;
  className?: string;
  children: React.ReactNode;
}

/**
 * Exposes a visual score as a named ARIA meter and gives keyboard users a
 * visible focus target without adding button-like behavior.
 */
export default function AccessibleScore({
  label,
  value,
  valueText,
  className = "",
  children,
}: AccessibleScoreProps) {
  const boundedValue = Math.max(0, Math.min(value, 100));

  return (
    <span
      role="meter"
      tabIndex={0}
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={boundedValue}
      aria-valuetext={valueText}
      className={`rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-t-blue ${className}`}
    >
      {children}
    </span>
  );
}
