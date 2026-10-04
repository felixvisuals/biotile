import { Orb } from "@yogesharc/thinking-orbs";
import type { ComponentProps, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { Check } from "../api";

type OrbState = ComponentProps<typeof Orb>["state"];

/** Book of Shapes slider: label above, 2px track with filled part, value right. */
export function Slider({ label, hint, value, min, max, step, unit, onChange, format }: {
  label: string; hint?: string; value: number; min: number; max: number; step: number; unit?: string;
  onChange: (v: number) => void; format?: (v: number) => string;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <label className="label">{label}</label>
      <div className="flex items-center gap-2">
        <div className="relative flex h-6 flex-1 items-center">
          <div className="pointer-events-none absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 rounded-sm bg-fg/20">
            <div className="h-full rounded-sm bg-fg" style={{ width: `${pct}%` }} />
          </div>
          <input type="range" className="range" aria-label={label} min={min} max={max} step={step} value={value}
            onChange={(e) => onChange(Number(e.target.value))} />
        </div>
        <span className="w-14 text-right text-xs tabular-nums opacity-50">{format ? format(value) : value}{unit ? ` ${unit}` : ""}</span>
      </div>
      {hint && <p className="mt-0.5 text-xs opacity-40">{hint}</p>}
    </div>
  );
}

/** Pill choice group (single select). */
export function Pills<T extends string | number>({ label, value, options, onChange }: {
  label?: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div>
      {label && <div className="label">{label}</div>}
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button key={String(o.value)} type="button" className="pill" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 py-1 text-sm font-medium">
      <span>{label}</span>
      <span className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${checked ? "bg-fg" : "bg-fg/20"}`}>
        <span className={`absolute top-0.5 size-4 rounded-full bg-bg transition-transform ${checked ? "translate-x-4.5" : "translate-x-0.5"}`} />
      </span>
      <input type="checkbox" className="sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

/** Thinking-orb loader: the orb's motion says what is happening. */
export function Loading({ label, state = "base", size = 20, className = "" }: { label?: string; state?: OrbState; size?: number; className?: string }) {
  const { t } = useTranslation();
  const text = label ?? t("common.loading");
  return (
    <span className={`inline-flex items-center gap-2 text-sm ${className}`} role="status">
      <Orb state={state} size={size} label={text} />
      <span>{text}</span>
    </span>
  );
}

/** Orb state per pipeline step (what the "agent" is doing right now). */
export function orbForStep(step: string | null | undefined): OrbState {
  switch (step) {
    case "tripo_upload": case "download": return "searching";
    case "tripo_generate": return "reasoning";
    case "rasterize": case "relief": case "metrics": return "working";
    case "tools": return "background";
    case "package": return "compacting";
    default: return "base";
  }
}

export function ProgressLine({ value }: { value: number }) {
  return (
    <div className="h-[2px] w-full bg-fg/15">
      <div className="h-full bg-fg transition-[width] duration-700" style={{ width: `${Math.max(2, value)}%` }} />
    </div>
  );
}

const DOT: Record<string, string> = { pass: "bg-accent", warn: "bg-warn", fail: "bg-bad" };

export function ReadyList({ checks }: { checks: Check[] }) {
  const { t } = useTranslation();
  return (
    <ul className="divide-y divide-line border-y border-line">
      {checks.map((c) => (
        <li key={c.id} className="flex items-center gap-3 py-2 text-sm" title={c.message}>
          <span className={`size-2 shrink-0 rounded-full ${DOT[c.status]}`} />
          <span className={c.status === "fail" ? "font-medium" : ""}>{t(`editor.checks.${c.id}`, { defaultValue: c.id })}</span>
        </li>
      ))}
    </ul>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  const e = error as { key?: string; message?: string };
  return (
    <div className="flex items-start gap-3 border-l-2 border-bad py-1 pl-3 text-sm">
      <div>
        <div className="font-medium">{e.key ? t(e.key, { defaultValue: t("errors.generic") }) : t("errors.generic")}</div>
        {e.message && <div className="mt-0.5 font-mono text-xs opacity-50">{e.message}</div>}
      </div>
    </div>
  );
}

/** "Make a poster →" style row. */
export function RowLink({ to, href, onClick, title, sub, badge, disabled, download }: {
  to?: string; href?: string; onClick?: () => void; title: ReactNode; sub?: ReactNode; badge?: string; disabled?: boolean; download?: boolean;
}) {
  const body = (
    <>
      <div className="min-w-0">
        <div className="flex items-center gap-3 text-[20px] font-medium tracking-tight md:text-[22px]">
          {title}
          {badge && <span className="rounded-sm bg-fg px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-bg">{badge}</span>}
        </div>
        {sub && <div className="mt-1 text-sm opacity-50">{sub}</div>}
      </div>
      <ArrowRight className="shrink-0 transition-transform group-hover:translate-x-1" />
    </>
  );
  const cls = `group row-link ${disabled ? "pointer-events-none opacity-30" : ""}`;
  if (to) return <Link to={to} className={cls}>{body}</Link>;
  if (href) return <a href={href} className={cls} download={download}>{body}</a>;
  return <button type="button" onClick={onClick} disabled={disabled} className={`${cls} w-full text-left`}>{body}</button>;
}

export function SourceTag({ type, surface }: { type: string; surface?: string | null }) {
  const { t } = useTranslation();
  const key = type === "photo" ? "photo" : surface?.startsWith("REF-") ? "reference" : "sample";
  return <span className="pill pointer-events-none !h-6 !px-3 !opacity-60">{t(`source.${key}`)}</span>;
}

export const sourceKey = (type: string, surface?: string | null) =>
  type === "photo" ? "photo" : surface?.startsWith("REF-") ? "reference" : "sample";

/* ---- icons (1.5px strokes, currentColor) ---- */
type IconProps = { className?: string; size?: number };
const svg = (size = 22, className = "", children: ReactNode) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden>
    {children}
  </svg>
);
export const ArrowRight = ({ className, size = 26 }: IconProps) => svg(size, className, <path d="M3 12h17m-5-5 5 5-5 5" />);
export const ArrowLeft = ({ className, size = 26 }: IconProps) => svg(size, className, <path d="M21 12H4m5-5-5 5 5 5" />);
export const DownloadIcon = ({ className, size }: IconProps) => svg(size, className, <path d="M12 3v13m-5-5 5 5 5-5M4 20h16" />);
export const ShareIcon = ({ className, size }: IconProps) => svg(size, className, <path d="M12 15V3m-5 5 5-5 5 5M5 12v8h14v-8" />);
export const RemixIcon = ({ className, size }: IconProps) => svg(size, className, <path d="M4 7h11l-3-3m3 3-3 3M20 17H9l3 3m-3-3 3-3" />);
export const PinIcon = ({ className, size }: IconProps) => svg(size, className, <><path d="M12 21s-6-5.3-6-11a6 6 0 1 1 12 0c0 5.7-6 11-6 11z" /><circle cx="12" cy="10" r="2" /></>);
export const PlusIcon = ({ className, size }: IconProps) => svg(size, className, <path d="M12 5v14M5 12h14" />);
export const CloseIcon = ({ className, size }: IconProps) => svg(size, className, <path d="M6 6l12 12M18 6 6 18" />);
export const LeafIcon = ({ className, size = 14 }: IconProps) => svg(size, className, <path d="M5 19c0-8 5-13 14-14-1 9-6 14-14 14zm0 0 7-7" />);
