import { useEffect, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";

// Ring colours tuned to read on the dark ink card: emerald / gold-400 / red.
function scoreColor(value) {
  if (value >= 75) return "#34B27B";
  if (value >= 50) return "#D6B26A";
  return "#E06B62";
}

/** Radial gauge: the ring fills and the number counts up on reveal. */
export default function ScoreGauge({ label, value, size = 150 }) {
  const [armed, setArmed] = useState(false);
  const shown = useCountUp(armed ? value : 0);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - (armed ? value : 0) / 100);
  const color = scoreColor(value);

  return (
    <figure className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          role="img"
          aria-label={`${label}: ${value} out of 100`}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1B2334"
            strokeWidth={strokeWidth}
          />
          <circle
            className="gauge-progress"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-4xl font-semibold text-paper-50">
            {shown}
          </span>
          <span className="text-xs font-medium text-paper-200/60">/ 100</span>
        </div>
      </div>
      <figcaption className="mt-3 text-sm font-semibold text-paper-200">
        {label}
      </figcaption>
    </figure>
  );
}
