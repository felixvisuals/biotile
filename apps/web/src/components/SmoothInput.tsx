import { motion, useMotionValue, useReducedMotion, useSpring } from "framer-motion";
import { type ComponentPropsWithoutRef, useEffect, useRef, useState } from "react";

/**
 * Text input with a spring-animated caret.
 * Adapted from Skiper UI "Skiper106" (attribution: skiper-ui.com). The dialkit tuning panel of
 * the original is replaced by fixed props, so nothing dev-only ships to users.
 */

const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

const PASSWORD_CHAR = typeof navigator !== "undefined" && /firefox|fxios/i.test(navigator.userAgent) ? "●" : "•";
const SPRING = { stiffness: 500, damping: 30, mass: 0.5 };

type SmoothInputProps = Omit<ComponentPropsWithoutRef<"input">, "type"> & {
  type?: "text" | "password" | "email";
  wrapperClassName?: string;
  fontSize?: number;
};

export default function SmoothInput({
  className, wrapperClassName, value, defaultValue, onChange, onBlur, type = "text", placeholder, style, fontSize = 20, ...props
}: SmoothInputProps) {
  const [internalValue, setInternalValue] = useState(defaultValue ?? "");
  const caretX = useMotionValue(0);
  const caretOpacity = useMotionValue(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const measureRef = useRef<HTMLSpanElement>(null);
  const reduce = useReducedMotion();
  const springX = useSpring(caretX, reduce ? { stiffness: 10000, damping: 100, mass: 0.1 } : SPRING);
  const isControlled = value !== undefined;
  const inputValue = isControlled ? String(value) : String(internalValue);

  const measure = (text: string) => {
    const input = inputRef.current;
    const span = measureRef.current;
    if (!input || !span) return null;
    const st = window.getComputedStyle(input);
    span.style.font = `${st.fontStyle} ${st.fontWeight} ${st.fontSize} ${st.fontFamily}`;
    span.style.letterSpacing = st.letterSpacing;
    span.textContent = text;
    const pl = parseFloat(st.paddingLeft) || 0;
    return text.length > 0 ? span.offsetWidth + pl : pl - 1;
  };

  const update = (t: HTMLInputElement) => {
    const start = t.selectionStart ?? 0;
    const end = t.selectionEnd ?? 0;
    const idx = start === end ? start : t.selectionDirection === "backward" ? start : end;
    const before = t.type === "password" ? PASSWORD_CHAR.repeat(idx) : t.value.slice(0, idx);
    const w = measure(before);
    if (w === null) return;
    const st = window.getComputedStyle(t);
    const pr = parseFloat(st.paddingRight) || 0;
    if (w > t.scrollLeft + t.clientWidth - pr) t.scrollLeft = w - t.clientWidth + pr;
    if (w < t.scrollLeft) t.scrollLeft = Math.max(0, w);
    const pos = w - t.scrollLeft;
    caretX.set(Math.min(pos, t.clientWidth - pr));
    caretOpacity.set(start !== end ? 0 : 1);
  };
  const updateRef = useRef(update);
  updateRef.current = update;

  useEffect(() => {
    const input = inputRef.current;
    if (input && document.activeElement === input) updateRef.current(input);
  }, [inputValue]);

  useEffect(() => {
    const input = inputRef.current;
    const container = containerRef.current;
    if (!input || !container) return;
    const ifFocused = () => { if (document.activeElement === input) updateRef.current(input); };
    const onSel = () => requestAnimationFrame(ifFocused);
    document.addEventListener("selectionchange", onSel);
    void document.fonts.ready.then(ifFocused);
    input.addEventListener("scroll", ifFocused);
    const ro = new ResizeObserver(ifFocused);
    ro.observe(container);
    return () => {
      document.removeEventListener("selectionchange", onSel);
      input.removeEventListener("scroll", ifFocused);
      ro.disconnect();
    };
  }, []);

  return (
    <div className={cn("relative w-full rounded-xl bg-surface px-4 py-3.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-fg/30", wrapperClassName)}>
      <div ref={containerRef} className="relative grid grid-cols-1" style={{ caretColor: "transparent", fontSize }}>
        <input
          {...props}
          ref={inputRef}
          // Browsers expose no caret position for type="email" (selectionStart is null), which
          // froze the animated caret. A text field with the e-mail keyboard behaves the same.
          type={type === "email" ? "text" : type}
          inputMode={type === "email" ? "email" : props.inputMode}
          autoCapitalize={type === "email" ? "none" : props.autoCapitalize}
          spellCheck={type === "email" ? false : props.spellCheck}
          placeholder={placeholder}
          className={cn("col-start-1 row-start-1 w-full bg-transparent font-medium outline-none placeholder:text-fg/30", className)}
          style={style}
          value={inputValue}
          onFocus={(e) => { updateRef.current(e.target); props.onFocus?.(e); }}
          onChange={(e) => {
            if (!isControlled) setInternalValue(e.target.value);
            onChange?.(e);
            const target = e.target;
            requestAnimationFrame(() => updateRef.current(target));
          }}
          onBlur={(e) => { caretOpacity.set(0); onBlur?.(e); }}
        />
        <span ref={measureRef} aria-hidden className="pointer-events-none invisible absolute left-0 top-0 whitespace-pre" />
        <motion.div className="pointer-events-none col-start-1 row-start-1 h-[0.9em] w-0.5 self-center bg-fg" style={{ x: springX, opacity: caretOpacity }} />
      </div>
    </div>
  );
}
