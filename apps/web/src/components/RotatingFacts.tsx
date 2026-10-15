import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const SHOW_MS = 8000; // long enough to read two lines

/** Short facts about image-to-3D and moss, shown in turn while a 3D model is being made. */
export default function RotatingFacts({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const facts = t("progress.facts", { returnObjects: true }) as string[];
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setI((k) => k + 1), SHOW_MS);
    return () => window.clearInterval(id);
  }, []);
  const fact = facts[i % facts.length];
  return (
    <div className={`min-h-[5.5em] ${className}`} aria-live="polite">
      <div className="font-mono text-[10px] uppercase tracking-widest opacity-40">
        {t("progress.facts_label")} · {(i % facts.length) + 1}/{facts.length}
      </div>
      <AnimatePresence mode="wait">
        <motion.p key={fact} className="mt-2 text-sm leading-relaxed opacity-70"
          initial={reduce ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          exit={reduce ? undefined : { opacity: 0, y: -6 }} transition={{ duration: 0.35 }}>
          {fact}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
