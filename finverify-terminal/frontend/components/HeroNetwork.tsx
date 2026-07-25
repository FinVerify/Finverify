"use client";

const HUBS = [
  { name: "NEW YORK", x: 112, y: 88, status: "OPEN", color: "#00ff88" },
  { name: "LONDON", x: 264, y: 64, status: "OPEN", color: "#00ff88" },
  { name: "FRANKFURT", x: 286, y: 78, status: "OPEN", color: "#00ff88" },
  { name: "DUBAI", x: 350, y: 116, status: "OPEN", color: "#00ff88" },
  { name: "MUMBAI", x: 392, y: 128, status: "OPEN", color: "#00ff88" },
  { name: "SINGAPORE", x: 472, y: 150, status: "OPEN", color: "#00ff88" },
  { name: "HONG KONG", x: 500, y: 116, status: "OPEN", color: "#00ff88" },
  { name: "TOKYO", x: 550, y: 94, status: "OPEN", color: "#00ff88" },
  { name: "SYDNEY", x: 558, y: 172, status: "CLOSED", color: "#fbbf24" },
];

const ROUTES = [
  [HUBS[0], HUBS[1]], [HUBS[1], HUBS[2]], [HUBS[2], HUBS[3]],
  [HUBS[3], HUBS[4]], [HUBS[4], HUBS[5]], [HUBS[5], HUBS[6]],
  [HUBS[6], HUBS[7]], [HUBS[0], HUBS[4]], [HUBS[1], HUBS[6]],
  [HUBS[7], HUBS[8]],
];

export default function HeroNetwork() {
  return (
    <div className="hero-network" aria-label="Global financial hub network">
      <svg viewBox="0 0 600 200" role="img" aria-hidden="true">
        <g className="hero-map" fill="none" stroke="currentColor" strokeWidth="1">
          <path d="M22 61 54 36 92 31 122 47 144 42 159 58 143 73 126 75 113 91 88 86 72 101 45 94 31 78Z" />
          <path d="M158 105 183 101 204 119 214 145 204 177 187 165 181 140 165 124Z" />
          <path d="m248 48 26-16 33 7 11 19 28 6 17 25-20 14-18-8-20 15-23-9-20-23Z" />
          <path d="m304 99 28-4 26 17-12 19-19 6-16-15Z" />
          <path d="m370 75 34-15 35 12 31-2 30 20-10 18-38 5-13 22-34-8-17-22Z" />
          <path d="m450 142 25-8 31 13 15 22-32 9-28-12Z" />
          <path d="m518 64 26-13 31 19 3 30-20 16-25-13-15-20Z" />
        </g>

        <g className="hero-routes">
          {ROUTES.map(([from, to], index) => (
            <g key={`${from.name}-${to.name}`}>
              <path id={`route-${index}`} d={`M ${from.x} ${from.y} Q ${(from.x + to.x) / 2} ${Math.min(from.y, to.y) - 24 - (index % 2) * 8} ${to.x} ${to.y}`} />
              <circle r="1.8" className="hero-packet" style={{ animationDelay: `${index * 1.4}s` }}>
                <animateMotion dur={`${7 + (index % 3)}s`} repeatCount="indefinite" begin={`${index * 0.8}s`}>
                  <mpath href={`#route-${index}`} />
                </animateMotion>
              </circle>
            </g>
          ))}
        </g>

        <g className="hero-hubs">
          {HUBS.map((hub) => (
            <g key={hub.name} transform={`translate(${hub.x} ${hub.y})`}>
              <circle r="5" className="hero-hub-ring" style={{ color: hub.color }} />
              <circle r="2.2" fill={hub.color} />
              <text x="7" y="-5">{hub.name}</text>
              <text x="7" y="5" className="hero-hub-status" style={{ fill: hub.color }}>{hub.status}</text>
            </g>
          ))}
        </g>
      </svg>
      <div className="hero-network-label">GLOBAL MARKET NETWORK <span>● LIVE ROUTING</span></div>
    </div>
  );
}
