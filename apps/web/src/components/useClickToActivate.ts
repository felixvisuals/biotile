import { type RefObject, useEffect, useState } from "react";

/**
 * Embedded maps and 3D views stay passive while the page scrolls past them: wheel and swipe
 * events go to the page. A click (or tap) activates the element; moving the mouse out or
 * touching anywhere else deactivates it again. While active, Lenis leaves the element alone.
 */
export function useClickToActivate(ref: RefObject<HTMLElement | null>, onChange: (active: boolean) => void) {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const set = (v: boolean) => {
      setActive(v);
      if (v) el.setAttribute("data-lenis-prevent", "");
      else el.removeAttribute("data-lenis-prevent");
      onChange(v);
    };
    const activate = () => set(true);
    const leave = (e: PointerEvent) => { if (e.pointerType === "mouse") set(false); };
    const outside = (e: PointerEvent) => { if (!el.contains(e.target as Node)) set(false); };
    el.addEventListener("pointerdown", activate);
    el.addEventListener("pointerleave", leave);
    document.addEventListener("pointerdown", outside);
    return () => {
      el.removeEventListener("pointerdown", activate);
      el.removeEventListener("pointerleave", leave);
      document.removeEventListener("pointerdown", outside);
    };
    // onChange is read once per element; callers pass a stable function
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref]);

  return active;
}
