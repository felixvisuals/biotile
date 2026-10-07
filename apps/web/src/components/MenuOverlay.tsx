import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { CloseIcon } from "./ui";

/**
 * Fullscreen menu. Item animation after Skiper UI "Skiper58" (TextRoll), attribution on the
 * Credits page. The overlay is opaque: the page behind is not visible while it is open.
 */
const STAGGER = 0.035;

export function TextRoll({ children, className = "", center = false }: { children: string; className?: string; center?: boolean }) {
  const letters = children.split("");
  const delay = (i: number) => (center ? STAGGER * Math.abs(i - (letters.length - 1) / 2) : STAGGER * i);
  return (
    <motion.span initial="initial" whileHover="hovered" whileFocus="hovered" className={`relative block overflow-hidden whitespace-nowrap ${className}`} style={{ lineHeight: 1.02, paddingTop: "0.06em" }}>
      <span className="block">
        {letters.map((l, i) => (
          <motion.span key={i} className="inline-block whitespace-pre" variants={{ initial: { y: 0 }, hovered: { y: "-100%" } }}
            transition={{ ease: "easeInOut", delay: delay(i) }}>{l}</motion.span>
        ))}
      </span>
      <span className="absolute inset-0 block" aria-hidden>
        {letters.map((l, i) => (
          <motion.span key={i} className="inline-block whitespace-pre" variants={{ initial: { y: "100%" }, hovered: { y: 0 } }}
            transition={{ ease: "easeInOut", delay: delay(i) }}>{l}</motion.span>
        ))}
      </span>
    </motion.span>
  );
}

export type MenuItem = { label: string; to?: string; onClick?: () => void };

export default function MenuOverlay({ open, onClose, items, footer, closeLabel }: {
  open: boolean; onClose: () => void; items: MenuItem[]; footer?: React.ReactNode; closeLabel: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog" aria-modal="true" data-lenis-prevent
          className="fixed inset-0 z-[90] flex flex-col bg-bg"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}
        >
          <div className="wrap flex h-[88px] items-center justify-between border-b border-line md:h-[120px]">
            <span className="text-md font-semibold tracking-tight">BIOTILE</span>
            <button className="icon-btn" onClick={onClose} aria-label={closeLabel}><CloseIcon size={26} /></button>
          </div>
          <nav className="flex flex-1 items-center justify-center overflow-y-auto py-10">
            <ul className="flex flex-col items-center gap-1 md:gap-2">
              {items.map((item, i) => {
                const inner = (
                  <span className="flex items-start gap-3">
                    <span className="mt-1 font-mono text-xs opacity-40">[{i}]</span>
                    {/* one line at every width: a wrapped label would reveal the hidden second roll layer */}
                    <TextRoll center className="text-[clamp(1.25rem,7vw,3.75rem)] font-extrabold uppercase tracking-[-0.03em]">{item.label}</TextRoll>
                  </span>
                );
                return (
                  <motion.li key={item.label} initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.05 + i * 0.04, duration: 0.3 }}>
                    {item.to
                      ? <Link to={item.to} onClick={onClose} className="block outline-none">{inner}</Link>
                      : <button type="button" onClick={() => { item.onClick?.(); onClose(); }} className="block cursor-pointer outline-none">{inner}</button>}
                  </motion.li>
                );
              })}
            </ul>
          </nav>
          {footer && <div className="wrap border-t border-line py-5">{footer}</div>}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
