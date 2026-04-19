"use client";

export function ProgressRing({
  size = 40,
  strokeWidth = 3,
  progress,
  trackColor,
  progressColor,
  className,
}: {
  size?: number;
  strokeWidth?: number;
  progress: number;
  trackColor: string;
  progressColor: string;
  className?: string;
}) {
  const normalizedProgress = Math.min(Math.max(progress, 0), 1);
  const radius = (size - strokeWidth * 2) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - normalizedProgress);

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      aria-hidden="true"
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={trackColor}
        strokeWidth={strokeWidth}
      />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={progressColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
      />
    </svg>
  );
}
