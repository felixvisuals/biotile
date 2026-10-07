import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";

type Feature = { properties: { name?: string; city?: string; district?: string; state?: string; country?: string } };

/**
 * Place field with suggestions while typing (native <datalist>). Suggestions come from Photon
 * by komoot (OpenStreetMap data, no key); only districts, towns and cities are asked for, so
 * nobody is nudged into entering a street address.
 */
export default function PlaceInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { i18n } = useTranslation();
  const listId = useId();
  const [options, setOptions] = useState<string[]>([]);

  useEffect(() => {
    const q = value.trim();
    if (q.length < 3 || options.includes(q)) return;
    const ctrl = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const lang = i18n.language.startsWith("de") ? "de" : "en";
        const layers = ["district", "locality", "city"].map((l) => `&layer=${l}`).join("");
        const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=6&lang=${lang}${layers}`,
          { signal: ctrl.signal });
        const data = (await res.json()) as { features: Feature[] };
        const seen = new Set<string>();
        setOptions(data.features.map(({ properties: p }) =>
          [p.name, p.city !== p.name ? p.city : null, p.country].filter(Boolean).join(", "))
          .filter((s) => s && !seen.has(s) && seen.add(s)));
      } catch { /* offline or aborted: the field still works as plain text */ }
    }, 300);
    return () => { window.clearTimeout(timer); ctrl.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, i18n.language]);

  return (
    <>
      <input className="field" maxLength={200} autoComplete="off" list={listId} value={value}
        onChange={(e) => onChange(e.target.value)} />
      <datalist id={listId}>{options.map((o) => <option key={o} value={o} />)}</datalist>
    </>
  );
}
