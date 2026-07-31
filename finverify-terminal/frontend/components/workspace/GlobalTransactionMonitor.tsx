"use client";

import React from "react";
import HeroNetwork from "@/components/HeroNetwork";

export default function GlobalTransactionMonitor() {
  return (
    <div className="w-full h-full relative bg-zinc-950/50 rounded border border-zinc-800/60 overflow-hidden">
      {/* ── Background Map ── */}
      <div className="absolute inset-0 opacity-50 pointer-events-none">
        <HeroNetwork />
      </div>

      {/* ── Overlay: City Nodes + Arcs ── */}
      <div className="absolute inset-0 pointer-events-none">
        <svg viewBox="0 0 600 200" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
          {/* Transaction arcs */}
          <g className="transaction-arcs" fill="none" stroke="#00ff88" strokeWidth="0.8" opacity="0.6">
            <path id="arc-0" d="M112 88 Q 180 60 264 64" />
            <path id="arc-1" d="M264 64 Q 300 50 350 116" />
            <path id="arc-2" d="M350 116 Q 380 100 392 128" />
            <path id="arc-3" d="M112 88 Q 200 140 392 128" />
            <path id="arc-4" d="M264 64 Q 350 60 500 116" />
            <path id="arc-5" d="M500 116 Q 530 80 550 94" />
            <path id="arc-6" d="M550 94 Q 560 140 558 172" />
          </g>

          {/* Animated packets */}
          <g className="packets">
            {[0, 1, 2, 3, 4, 5, 6].map((i) => (
              <circle key={i} r="2" fill="#00ff88">
                <animateMotion dur="6s" repeatCount="indefinite" begin={`${i * 0.8}s`}>
                  <mpath href={`#arc-${i}`} />
                </animateMotion>
              </circle>
            ))}
          </g>

          {/* City nodes */}
          <g className="city-nodes" fill="#00ff88">
            <circle cx="112" cy="88" r="4" />
            <text x="118" y="86" className="text-[6px] fill-zinc-400 font-mono">NY</text>

            <circle cx="264" cy="64" r="4" />
            <text x="270" y="62" className="text-[6px] fill-zinc-400 font-mono">LD</text>

            <circle cx="350" cy="116" r="4" />
            <text x="356" y="114" className="text-[6px] fill-zinc-400 font-mono">DU</text>

            <circle cx="392" cy="128" r="4" />
            <text x="398" y="126" className="text-[6px] fill-zinc-400 font-mono">MU</text>

            <circle cx="500" cy="116" r="4" />
            <text x="506" y="114" className="text-[6px] fill-zinc-400 font-mono">HK</text>

            <circle cx="550" cy="94" r="4" />
            <text x="556" y="92" className="text-[6px] fill-zinc-400 font-mono">TK</text>

            <circle cx="558" cy="172" r="4" />
            <text x="564" y="170" className="text-[6px] fill-zinc-400 font-mono">SY</text>
          </g>

          {/* Labels */}
          <text x="10" y="20" className="text-[8px] fill-zinc-500 font-mono">GLOBAL TRANSACTION MONITOR</text>
          <text x="10" y="32" className="text-[6px] fill-zinc-600 font-mono">• live flows • demo</text>
        </svg>
      </div>
    </div>
  );
}
