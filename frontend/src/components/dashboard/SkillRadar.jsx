import { useEffect, useMemo, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";

// Axis order mirrors SKILL_CATEGORIES in backend/app/models/gap_report.py.
const AXIS_ORDER = [
  "Languages",
  "Frameworks & Libraries",
  "Tools & Platforms",
  "Cloud & DevOps",
  "Data & ML",
  "Concepts & Soft Skills",
];

// Compact labels so long category names don't collide around the chart.
const SHORT_LABELS = {
  "Languages": "Languages",
  "Frameworks & Libraries": "Frameworks",
  "Tools & Platforms": "Tools",
  "Cloud & DevOps": "Cloud/DevOps",
  "Data & ML": "Data/ML",
  "Concepts & Soft Skills": "Concepts",
};

const SIZE = 260;
const CENTER = SIZE / 2;
const MAX_R = 88;
const RINGS = [0.25, 0.5, 0.75, 1];

function polar(angleDeg, radius) {
  const a = (angleDeg * Math.PI) / 180;
  return [CENTER + radius * Math.cos(a), CENTER + radius * Math.sin(a)];
}

/**
 * Skill-gap radar: one axis per skill category present in the gap report,
 * each plotted as the % of that category's requirements the resume already
 * covers. Renders nothing (the caller falls back to the flat matched/missing
 * view) when fewer than three categories carry data — a radar needs ≥3 axes.
 */
export default function SkillRadar({ categories }) {
  const axes = useMemo(() => {
    if (!categories) return [];
    return AXIS_ORDER.flatMap((name) => {
      const bucket = categories[name];
      if (!bucket) return [];
      const matched = bucket.matched?.length ?? 0;
      const missing = bucket.missing?.length ?? 0;
      const total = matched + missing;
      if (total === 0) return [];
      return [{ name, matched, total, value: Math.round((100 * matched) / total) }];
    });
  }, [categories]);

  const reduce =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [armed, setArmed] = useState(reduce);
  useEffect(() => {
    if (reduce) return undefined;
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, [reduce]);

  const overall = axes.length
    ? Math.round(
        (100 * axes.reduce((sum, a) => sum + a.matched, 0)) /
          axes.reduce((sum, a) => sum + a.total, 0),
      )
    : 0;
  const shown = useCountUp(armed ? overall : 0);

  if (axes.length < 3) return null;

  const angleFor = (i) => -90 + (i * 360) / axes.length;
  const dataPoints = axes
    .map((axis, i) => polar(angleFor(i), MAX_R * (axis.value / 100)).join(","))
    .join(" ");

  return (
    <figure className="flex flex-col items-center">
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={`Skill coverage by category: ${axes
          .map((a) => `${a.name} ${a.value}%`)
          .join(", ")}`}
        className="max-w-full"
      >
        {RINGS.map((ring) => (
          <polygon
            key={ring}
            points={axes
              .map((_, i) => polar(angleFor(i), MAX_R * ring).join(","))
              .join(" ")}
            fill="none"
            stroke="#1B2334"
            strokeWidth={1}
          />
        ))}

        {axes.map((axis, i) => {
          const [sx, sy] = polar(angleFor(i), MAX_R);
          const [lx, ly] = polar(angleFor(i), MAX_R + 16);
          const anchor =
            Math.abs(lx - CENTER) < 8 ? "middle" : lx > CENTER ? "start" : "end";
          return (
            <g key={axis.name}>
              <line
                x1={CENTER}
                y1={CENTER}
                x2={sx}
                y2={sy}
                stroke="#1B2334"
                strokeWidth={1}
              />
              <text
                x={lx}
                y={ly}
                textAnchor={anchor}
                dominantBaseline="middle"
                fill="#EAE7DC"
                className="text-[10px] font-semibold"
              >
                {SHORT_LABELS[axis.name] ?? axis.name}
              </text>
            </g>
          );
        })}

        <g
          style={{
            transformBox: "view-box",
            transformOrigin: `${CENTER}px ${CENTER}px`,
            transform: armed ? "scale(1)" : "scale(0)",
            transition: reduce
              ? "none"
              : "transform 900ms cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        >
          <polygon
            points={dataPoints}
            fill="#D6B26A"
            fillOpacity={0.22}
            stroke="#D6B26A"
            strokeWidth={2}
            strokeLinejoin="round"
          />
          {axes.map((axis, i) => {
            const [px, py] = polar(angleFor(i), MAX_R * (axis.value / 100));
            return <circle key={axis.name} cx={px} cy={py} r={3} fill="#E3C88A" />;
          })}
        </g>

        <text
          x={CENTER}
          y={CENTER - 2}
          textAnchor="middle"
          fill="#FBFAF7"
          className="font-display text-2xl font-semibold"
        >
          {shown}%
        </text>
        <text
          x={CENTER}
          y={CENTER + 14}
          textAnchor="middle"
          fill="#EAE7DC"
          fillOpacity={0.6}
          className="text-[10px] font-medium"
        >
          covered
        </text>
      </svg>
      <figcaption className="mt-1 text-xs text-paper-200/60">
        Coverage by skill category
      </figcaption>
    </figure>
  );
}
