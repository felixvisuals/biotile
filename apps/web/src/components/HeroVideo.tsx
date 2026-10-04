import { useEffect, useRef, useState } from "react";

const FADE_S = 0.9; // fade in at the start and out at the end of every loop

/**
 * Background video next to the hero text: muted autoplay (works on phones with playsInline),
 * fades in and out at each loop, soft edges through a CSS mask. Reduced motion: poster only.
 */
export default function HeroVideo({ src, poster, label, className = "" }: {
  src: string; poster: string; label: string; className?: string;
}) {
  const ref = useRef<HTMLVideoElement>(null);
  const [opacity, setOpacity] = useState(0);
  const [reduce] = useState(() => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  useEffect(() => {
    const v = ref.current;
    if (!v || reduce) return;
    let raf = 0;
    const tick = () => {
      const d = v.duration;
      if (d && Number.isFinite(d) && !v.paused) {
        const t = v.currentTime;
        setOpacity(Math.max(0, Math.min(1, t / FADE_S, (d - t) / FADE_S)));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    // pause when off screen (battery on phones), resume when visible
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) void v.play().catch(() => {});
      else v.pause();
    }, { threshold: 0.1 });
    io.observe(v);
    void v.play().catch(() => {});
    return () => { cancelAnimationFrame(raf); io.disconnect(); };
  }, [reduce]);

  const mask = "radial-gradient(ellipse 72% 70% at 50% 50%, #000 55%, transparent 100%)";
  return (
    <div className={`relative overflow-hidden rounded-[28px] ${className}`} aria-label={label} role="img">
      {reduce ? (
        <img src={poster} alt="" className="h-full w-full object-cover" style={{ WebkitMaskImage: mask, maskImage: mask }} />
      ) : (
        <video
          ref={ref}
          src={src}
          poster={poster}
          muted
          loop
          playsInline
          autoPlay
          preload="metadata"
          aria-hidden
          className="h-full w-full object-cover"
          style={{ opacity, transition: "opacity 120ms linear", WebkitMaskImage: mask, maskImage: mask }}
        />
      )}
    </div>
  );
}
