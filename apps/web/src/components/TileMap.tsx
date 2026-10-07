import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { api } from "../api";
import { Loading } from "./ui";
import { useClickToActivate } from "./useClickToActivate";
import { useLocalized } from "../localized";

type Loc = { id: string; lat: number; lon: number; title: string; place: string | null; preview_url: string | null };

/**
 * Interactive monochrome map of hanging tiles. Map data © OpenStreetMap contributors,
 * tiles and style by OpenFreeMap (free, no API key). Dark mode inverts the light style.
 * maplibre-gl is loaded lazily so it does not weigh on the first page load.
 */
function setInteractive(m: import("maplibre-gl").Map, on: boolean) {
  for (const h of [m.scrollZoom, m.dragPan, m.touchZoomRotate, m.doubleClickZoom, m.dragRotate, m.keyboard]) {
    if (on) h.enable();
    else h.disable();
  }
}

export default function TileMap({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const L = useLocalized();
  const ref = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const active = useClickToActivate(box, (v) => { if (mapRef.current) setInteractive(mapRef.current, v); });
  const [ready, setReady] = useState(false);
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    let map: import("maplibre-gl").Map | null = null;
    let cancelled = false;
    (async () => {
      const [maplibregl, locs] = await Promise.all([import("maplibre-gl"), api.locations()]);
      if (cancelled || !ref.current) return;
      setCount(locs.length);
      // In production the worker file next to maplibre's module is not part of the build.
      maplibregl.setWorkerUrl(workerUrl);
      const m = new maplibregl.Map({
        container: ref.current,
        style: "https://tiles.openfreemap.org/styles/positron",
        center: [2.1734, 41.3951], // Barcelona
        zoom: 12,
        attributionControl: { compact: true },
      });
      // passive until clicked, so scrolling the page past the map never gets stuck on it
      setInteractive(m, false);
      map = m;
      mapRef.current = m;
      m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      m.on("load", () => setReady(true));
      m.on("error", (e) => console.warn("[map]", e.error?.message ?? e));
      const bounds = new maplibregl.LngLatBounds();
      locs.forEach((l: Loc) => {
        const el = document.createElement("button");
        el.className = "tile-marker";
        el.setAttribute("aria-label", `${l.id} · ${L.title(l)}`);
        const popup = new maplibregl.Popup({ offset: 14, closeButton: false, className: "tile-popup" }).setHTML(
          `<a href="/instances/${encodeURIComponent(l.id)}" class="tile-popup-link">` +
          (l.preview_url ? `<img src="${l.preview_url}" alt="" />` : "") +
          `<span class="tile-popup-code">${l.id}</span><span class="tile-popup-title"></span>` +
          `<span class="tile-popup-place"></span></a>`,
        );
        // plain text, never HTML, for user-provided fields
        popup.on("open", () => {
          const root = popup.getElement();
          const tt = root?.querySelector(".tile-popup-title");
          const pl = root?.querySelector(".tile-popup-place");
          if (tt) tt.textContent = L.title(l);
          if (pl) pl.textContent = l.place ?? "";
        });
        new maplibregl.Marker({ element: el }).setLngLat([l.lon, l.lat]).setPopup(popup).addTo(m);
        bounds.extend([l.lon, l.lat]);
      });
      if (locs.length > 1) m.fitBounds(bounds, { padding: 60, maxZoom: 14, duration: 0 });
    })().catch(() => setCount(0));
    return () => { cancelled = true; map?.remove(); };
  }, []);

  return (
    <div ref={box} className={`relative overflow-hidden rounded-[28px] bg-surface ${className}`}>
      <div ref={ref} className="tile-map h-full w-full" aria-label={t("home.map_title")} />
      {!ready && <div className="absolute inset-0 flex items-center justify-center"><Loading state="searching" /></div>}
      {ready && !active && (
        <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 whitespace-nowrap rounded-full bg-bg/85 px-3 py-1 font-mono text-[10px] uppercase tracking-widest opacity-70">
          {t("common.click_to_use_map")}
        </div>
      )}
      {count !== null && (
        <div className="pointer-events-none absolute bottom-3 left-4 font-mono text-[10px] uppercase tracking-widest opacity-60">
          {t("home.map_count", { count })}
        </div>
      )}
    </div>
  );
}
