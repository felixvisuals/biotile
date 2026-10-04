import { useEffect, useState } from "react";

/** Static prefix followed by variants that are typed, held, deleted and retyped in a loop, with a
 *  blinking block cursor. Restarts on language switch. Screen readers get the first variant once;
 *  with reduced motion the first variant is shown without animation. */
export default function Typewriter({ prefix, variants, className = "", speed = 55, hold = 2200, startDelay = 400 }: {
  prefix: string; variants: string[]; className?: string; speed?: number; hold?: number; startDelay?: number;
}) {
  const [idx, setIdx] = useState(0);
  const [n, setN] = useState(0);
  const key = variants.join("|");

  useEffect(() => {
    setIdx(0);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(variants[0]?.length ?? 0);
      return;
    }
    setN(0);
    let v = 0, i = 0, dir = 1, timer = 0;
    const step = () => {
      const text = variants[v] ?? "";
      if (dir === 1) {
        i += 1; setN(i);
        if (i < text.length) timer = window.setTimeout(step, speed + Math.random() * speed * 0.6);
        else if (variants.length > 1) { dir = -1; timer = window.setTimeout(step, hold); }
      } else {
        i -= 1; setN(i);
        if (i > 0) timer = window.setTimeout(step, speed * 0.45);
        else { dir = 1; v = (v + 1) % variants.length; setIdx(v); timer = window.setTimeout(step, 350); }
      }
    };
    timer = window.setTimeout(step, startDelay);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, speed, hold, startDelay]);

  return (
    <span className={className}>
      <span className="sr-only">{prefix}{variants[0]}</span>
      <span aria-hidden>
        {prefix}{(variants[idx] ?? "").slice(0, n)}
        <span className="type-caret" />
      </span>
    </span>
  );
}
