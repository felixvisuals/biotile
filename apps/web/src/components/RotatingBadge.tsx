import { useId } from "react";

/** Circular text that slowly turns (after theodore.net's "More Work" badge). */
export default function RotatingBadge({ text, size = 132, className = "" }: { text: string; size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} className={`spin-slow ${className}`} aria-hidden>
      <defs>
        <path id={id} d="M50,50 m-38,0 a38,38 0 1,1 76,0 a38,38 0 1,1 -76,0" />
      </defs>
      <text className="fill-current font-mono" fontSize="8.4" letterSpacing="1.6">
        <textPath href={`#${id}`} textLength={238.7} lengthAdjust="spacing">{text.repeat(2)}</textPath>
      </text>
    </svg>
  );
}
