import { motion, type MotionValue, useScroll, useTransform } from "framer-motion";
import Lenis from "lenis";
import { useEffect, useRef, useState } from "react";
import credits from "../data/surface-credits.json";

/**
 * Parallax overview of biological / bioreceptive surfaces.
 * Adapted from Skiper UI "Skiper30 Parallax_002" (React + framer-motion + lenis),
 * inspired by siena.film. Attribution: Skiper UI, https://skiper-ui.com (@gurvinder-singh02).
 */

// Public-domain / CC0 photos from Wikimedia Commons (scripts/fetch_surface_images.py);
// sources and authors are listed on the Credits page.
const images = (credits as { file: string }[]).map((c) => `/images/surfaces/${c.file}`);

export default function SurfaceParallax({ topLabel, bottomLabel }: { topLabel: string; bottomLabel?: string }) {
  const gallery = useRef<HTMLDivElement>(null);
  const [dimension, setDimension] = useState({ width: 0, height: 0 });

  const { scrollYProgress } = useScroll({ target: gallery, offset: ["start end", "end start"] });
  const { height } = dimension;
  const y = useTransform(scrollYProgress, [0, 1], [0, height * 2]);
  const y2 = useTransform(scrollYProgress, [0, 1], [0, height * 3.3]);
  const y3 = useTransform(scrollYProgress, [0, 1], [0, height * 1.25]);
  const y4 = useTransform(scrollYProgress, [0, 1], [0, height * 3]);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const lenis = reduce ? null : new Lenis();
    let raf = 0;
    const loop = (time: number) => {
      lenis?.raf(time);
      raf = requestAnimationFrame(loop);
    };
    const resize = () => setDimension({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(loop);
    resize();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      lenis?.destroy();
    };
  }, []);

  return (
    <div className="w-full">
      <ScrollHint label={topLabel} />
      <div ref={gallery} className="relative box-border flex h-[175vh] gap-[2vw] overflow-hidden bg-surface p-[2vw]">
        <Column images={[images[0], images[1], images[2]]} y={y} />
        <Column images={[images[3], images[4], images[5]]} y={y2} />
        <Column images={[images[6], images[7], images[8]]} y={y3} />
        <Column images={[images[9], images[10], images[11]]} y={y4} />
      </div>
      {bottomLabel && <ScrollHint label={bottomLabel} />}
    </div>
  );
}

function ScrollHint({ label }: { label: string }) {
  return (
    <div className="relative flex h-[22vh] items-start justify-center pt-6">
      <span className="relative max-w-[16ch] text-center text-xs uppercase leading-tight tracking-widest opacity-40 after:absolute after:left-1/2 after:top-full after:mt-2 after:h-16 after:w-px after:bg-gradient-to-b after:from-transparent after:to-fg after:content-['']">
        {label}
      </span>
    </div>
  );
}

function Column({ images, y }: { images: string[]; y: MotionValue<number> }) {
  return (
    <motion.div
      className="relative -top-[45%] flex h-full w-1/4 min-w-[160px] flex-col gap-[2vw] first:top-[-45%] [&:nth-child(2)]:top-[-95%] [&:nth-child(3)]:top-[-45%] [&:nth-child(4)]:top-[-75%]"
      style={{ y }}
    >
      {images.map((src, i) => (
        <div key={i} className="relative h-full w-full overflow-hidden">
          <img src={src} alt="" loading="lazy" className="pointer-events-none h-full w-full object-cover" />
        </div>
      ))}
    </motion.div>
  );
}
