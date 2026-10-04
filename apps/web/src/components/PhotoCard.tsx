import { type ReactNode, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { CloseIcon } from "./ui";

/**
 * Photo with its details on hover: while the details are shown, the image is strongly
 * blurred and monochrome, so the text stays readable. Click (or Enter) opens it large.
 * On touch devices the first tap shows the details, the second opens the photo.
 */
export default function PhotoCard({ src, alt, children, caption, className = "" }: {
  src: string | null; alt: string; children: ReactNode; caption?: ReactNode; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [touched, setTouched] = useState(false);
  return (
    <figure className={`bg-surface ${className}`}>
      <button
        type="button"
        className="group relative block aspect-square w-full cursor-zoom-in overflow-hidden"
        onClick={() => { if (!src) return; if (window.matchMedia("(hover: none)").matches && !touched) { setTouched(true); return; } setOpen(true); }}
        onBlur={() => setTouched(false)}
        aria-label={alt}
      >
        {src ? (
          <img src={src} alt={alt} loading="lazy"
            className={`h-full w-full object-cover transition-[filter,transform] duration-300 group-hover:scale-[1.06] group-hover:blur-[14px] group-hover:grayscale group-focus-visible:blur-[14px] group-focus-visible:grayscale ${touched ? "scale-[1.06] blur-[14px] grayscale" : ""}`} />
        ) : <div className="h-full w-full" />}
        <div className={`absolute inset-0 flex flex-col justify-end gap-1.5 bg-bg/35 p-4 text-left text-sm text-fg opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100 ${touched ? "opacity-100" : ""}`}>
          {children}
        </div>
      </button>
      {caption && <figcaption className="p-3 font-mono text-xs opacity-60">{caption}</figcaption>}
      {open && src && <Lightbox src={src} alt={alt} onClose={() => setOpen(false)}>{children}</Lightbox>}
    </figure>
  );
}

function Lightbox({ src, alt, onClose, children }: { src: string; alt: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", onKey); document.body.style.overflow = prev; };
  }, [onClose]);
  return createPortal(
    <div role="dialog" aria-modal="true" aria-label={alt} data-lenis-prevent
      className="fixed inset-0 z-[100] flex flex-col bg-bg/95 backdrop-blur-sm" onClick={onClose}>
      <div className="wrap flex items-center justify-end py-4">
        <button className="icon-btn" onClick={onClose} aria-label="close"><CloseIcon /></button>
      </div>
      <div className="wrap grid min-h-0 flex-1 gap-6 pb-8 md:grid-cols-12" onClick={(e) => e.stopPropagation()}>
        <img src={src} alt={alt} className="max-h-[78vh] w-full object-contain md:col-span-9" />
        <div className="space-y-2 text-sm md:col-span-3">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
