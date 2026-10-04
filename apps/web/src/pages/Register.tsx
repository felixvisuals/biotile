import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { api, type DesignSummary, type Instance } from "../api";
import { useAuth } from "../auth";
import { ArrowRight, ErrorNote, Loading, Pills, RowLink, Toggle } from "../components/ui";
import { useLocalized } from "../localized";

const today = () => new Date().toISOString().slice(0, 10);

function useCompass() {
  const [heading, setHeading] = useState<number | null>(null);
  const supported = typeof window !== "undefined" && "DeviceOrientationEvent" in window;
  const start = async () => {
    const DOE = (window as any).DeviceOrientationEvent;
    if (DOE?.requestPermission) {
      try { if ((await DOE.requestPermission()) !== "granted") return; } catch { return; }
    }
    const handler = (e: DeviceOrientationEvent & { webkitCompassHeading?: number }) => {
      // Phone back lies on the tile, screen faces you: the tile faces heading + 180°.
      const h = e.webkitCompassHeading ?? (e.absolute && e.alpha !== null ? 360 - e.alpha : null);
      if (h !== null && h !== undefined) setHeading(Math.round((h + 180) % 360));
    };
    window.addEventListener("deviceorientationabsolute" as any, handler as any);
    window.addEventListener("deviceorientation", handler as any);
  };
  return { heading, start, supported };
}

function Dial({ deg }: { deg: number | null }) {
  return (
    <svg viewBox="0 0 100 100" className="size-28 shrink-0" aria-hidden>
      <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeOpacity="0.2" />
      {["N", "E", "S", "W"].map((l, i) => {
        const a = (i * 90 - 90) * (Math.PI / 180);
        return <text key={l} x={50 + Math.cos(a) * 36} y={50 + Math.sin(a) * 36 + 3} textAnchor="middle" fontSize="8" className="fill-current font-mono" opacity="0.5">{l}</text>;
      })}
      {deg !== null && Number.isFinite(deg) && (
        <g transform={`rotate(${deg} 50 50)`}>
          <line x1="50" y1="50" x2="50" y2="12" stroke="currentColor" strokeWidth="2" />
          <circle cx="50" cy="12" r="3" className="fill-current" />
        </g>
      )}
      <circle cx="50" cy="50" r="2.5" className="fill-current" />
    </svg>
  );
}

function Block({ n, title, hint, children }: { n: number; title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="grid gap-6 border-t border-line py-10 md:grid-cols-12">
      <div className="md:col-span-4">
        <div className="font-mono text-xs opacity-40">{String(n).padStart(2, "0")}</div>
        <h2 className="mt-2 text-[22px] font-medium tracking-tight">{title}</h2>
        {hint && <p className="mt-2 max-w-[36ch] text-sm opacity-50">{hint}</p>}
      </div>
      <div className="space-y-6 md:col-span-8">{children}</div>
    </section>
  );
}

function PatternGrid({ items, selected, onSelect }: { items: DesignSummary[]; selected: string; onSelect: (id: string) => void }) {
  const L = useLocalized();
  return (
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6">
      {items.map((d) => (
        <button type="button" key={d.id} onClick={() => onSelect(d.id)} title={L.title(d)}
          className={`cursor-pointer bg-surface p-2 text-left transition-all ${selected === d.id ? "ring-2 ring-fg" : "opacity-70 hover:opacity-100"}`}>
          {d.preview_url ? <img src={d.preview_url} alt="" className="aspect-square w-full object-contain" /> : <div className="aspect-square bg-fg/5" />}
          <div className="mt-2 truncate text-xs font-medium">{L.title(d)}</div>
          <div className="truncate font-mono text-[10px] opacity-50">{d.code}</div>
        </button>
      ))}
    </div>
  );
}

const MOUNTS = ["wall", "fence", "facade", "post", "tree", "other"] as const;

export default function Register() {
  const { t } = useTranslation();
  const L = useLocalized();
  const { me } = useAuth();
  const [params] = useSearchParams();
  const [designs, setDesigns] = useState<DesignSummary[] | null>(null);
  const [designId, setDesignId] = useState(params.get("design") ?? "");
  const [search, setSearch] = useState("");
  const [searchMiss, setSearchMiss] = useState(false);
  const [material, setMaterial] = useState("clay");
  const [format, setFormat] = useState("1x1");
  const [facing, setFacing] = useState("");
  const [place, setPlace] = useState("");
  const [height, setHeight] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [visibility, setVisibility] = useState<"approx" | "exact" | "hidden">("approx");
  const [gpsState, setGpsState] = useState<"idle" | "busy" | "fail">("idle");
  const [light, setLight] = useState("");
  const [mount, setMount] = useState<string>("wall");
  const [mountDetail, setMountDetail] = useState("");
  const [starter, setStarter] = useState(true);
  const [starterDetails, setStarterDetails] = useState("");
  const [cast, setCast] = useState("");
  const [hung, setHung] = useState(today());
  const [notes, setNotes] = useState("");
  const [created, setCreated] = useState<Instance | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const compass = useCompass();
  const isSchool = me?.type === "school";

  useEffect(() => { api.designs("all").then((ds) => setDesigns(ds.filter((d) => d.code))).catch(setError); }, []);
  useEffect(() => { if (compass.heading !== null) setFacing(String(compass.heading)); }, [compass.heading]);

  const findByCode = async () => {
    setSearchMiss(false);
    try {
      const r = await api.lookup(search);
      const d = r.kind === "design" ? r.design : null;
      if (!d) throw new Error("not a pattern");
      setDesigns((list) => (list && !list.some((x) => x.id === d.id) ? [d, ...list] : list));
      setDesignId(d.id);
    } catch {
      setSearchMiss(true);
    }
  };

  const useGps = () => {
    if (!("geolocation" in navigator)) return setGpsState("fail");
    setGpsState("busy");
    navigator.geolocation.getCurrentPosition(
      (pos) => { setLat(pos.coords.latitude.toFixed(6)); setLon(pos.coords.longitude.toFixed(6)); setGpsState("idle"); },
      () => setGpsState("fail"),
      { enableHighAccuracy: true, timeout: 15000 },
    );
  };

  const deg = facing.trim() === "" ? null : Number(facing);
  const coordsOk = (lat === "" && lon === "") || (Number.isFinite(Number(lat)) && Number.isFinite(Number(lon)) && lat !== "" && lon !== "");
  const valid = !!designId && deg !== null && Number.isFinite(deg) && deg >= 0 && deg < 360 && coordsOk;
  const mine = (designs ?? []).filter((d) => d.is_mine);
  const others = (designs ?? []).filter((d) => !d.is_mine);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    setBusy(true);
    setError(null);
    try {
      setCreated(await api.createInstance({
        design_id: designId, material, process: material === "concrete" ? "matrix_down" : "press_mould",
        stage: material === "concrete" ? 2 : 1, format, orientation_deg: deg, inclination_deg: 90,
        height_above_ground_m: height ? Number(height) : null, shading: light || null,
        booster: starter, booster_recipe: starter ? starterDetails || null : null,
        mounting_adapter: mount, mounting_detail: mountDetail || null, location_coarse: place || null,
        geo_lat: lat ? Number(lat) : null, geo_lon: lon ? Number(lon) : null, geo_visibility: visibility,
        cast_date: cast || null, installed_date: hung || null, notes: notes || null, channels: "none",
        back_type: material === "concrete" ? "solid" : "shell",
      }));
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  if (created) {
    return (
      <div className="wrap">
        <div className="grid gap-10 py-col md:grid-cols-12">
          <div className="md:col-span-7">
            <div className="eyebrow">{L.title({ title: created.design_title, title_en: created.design_title_en })}</div>
            <h1 className="title-lg mt-4">{t("hang.done", { id: created.id })}</h1>
            <p className="lead mt-6 max-w-[40ch] opacity-70">{t("hang.done_text")}</p>
          </div>
          <div className="space-y-5 md:col-span-5 md:self-end">
            <RowLink href={api.referenceCardUrl(created.id)} title={t("hang.card")} badge="PDF" />
            <RowLink to={`/observe/${created.id}`} title={t("hang.first")} />
            <RowLink to={`/instances/${created.id}`} title={created.id} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="wrap">
      <div className="grid gap-6 py-col md:grid-cols-12">
        <h1 className="title-lg md:col-span-6">{t("hang.title")}</h1>
        <p className="lead opacity-70 md:col-span-5 md:col-start-8 md:self-end">{t("hang.lead")}</p>
      </div>

      <Block n={1} title={t("hang.pattern")}>
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-[14rem] flex-1">
            <span className="label">{t("hang.search")}</span>
            <input className="field font-mono uppercase" placeholder="BT-XXXXXX" value={search}
              onChange={(e) => { setSearch(e.target.value); setSearchMiss(false); }}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void findByCode(); } }} />
          </label>
          <button type="button" className="btn-ghost" onClick={findByCode} disabled={!search.trim()}>{t("observe.find_go")}</button>
        </div>
        {searchMiss && <p className="text-sm text-bad">{t("hang.search_none")}</p>}
        {designs === null ? <Loading /> : (
          <>
            {mine.length > 0 && <div><div className="label">{t("hang.mine")}</div><PatternGrid items={mine} selected={designId} onSelect={setDesignId} /></div>}
            {others.length > 0 && <div><div className="label">{t("hang.others")}</div><PatternGrid items={others} selected={designId} onSelect={setDesignId} /></div>}
          </>
        )}
      </Block>

      <Block n={2} title={t("hang.facing")} hint={t("hang.facing_hint")}>
        <div className="flex flex-wrap items-center gap-8">
          <Dial deg={deg} />
          <div className="space-y-4">
            <div className="flex items-baseline gap-1">
              <input required inputMode="numeric" maxLength={3} aria-label={t("hang.facing")}
                className="field w-[4.5ch] !text-lg !font-semibold tabular-nums" value={facing}
                onChange={(e) => setFacing(e.target.value.replace(/\D/g, "").slice(0, 3))} placeholder="000" />
              <span className="text-lg opacity-40">°</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {([["N", 0], ["E", 90], ["S", 180], ["W", 270]] as const).map(([k, v]) => (
                <button type="button" key={k} className="pill" aria-pressed={deg === v} onClick={() => setFacing(String(v))}>{t(`hang.dirs.${k}`)}</button>
              ))}
            </div>
            {compass.supported && (
              <button type="button" className="text-sm underline underline-offset-4 opacity-70 hover:opacity-100" onClick={compass.start}>{t("hang.compass")}</button>
            )}
            <p className="text-xs opacity-40">{t("hang.compass_hint")}</p>
          </div>
        </div>
      </Block>

      <Block n={3} title={t("hang.material")}>
        <Pills value={material} options={(["clay", "concrete"] as const).map((v) => ({ value: v, label: t(`editor.material_opts.${v}`) }))} onChange={setMaterial} />
        <Pills label={t("hang.size")} value={format} options={["1x1", "2x1", "2x2"].map((v) => ({ value: v, label: v.replace("x", " × ") }))} onChange={setFormat} />
      </Block>

      <Block n={4} title={t("hang.where")}>
        <div className="grid gap-8 sm:grid-cols-2">
          <label><span className="label">{t("hang.place")}</span><input className="field" maxLength={200} value={place} onChange={(e) => setPlace(e.target.value)} /></label>
          <label><span className="label">{t("hang.height")}</span><input className="field" type="number" min={0} step="0.1" value={height} onChange={(e) => setHeight(e.target.value)} /></label>
        </div>
        <div className="space-y-4 border-l-2 border-line pl-4">
          <div>
            <div className="label">{t("hang.coords")} <span className="opacity-40">({t("common.optional")})</span></div>
            <p className="text-xs opacity-50">{t("hang.coords_hint")}</p>
          </div>
          <div className="grid gap-6 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label><span className="label">{t("hang.lat")}</span><input className="field font-mono" inputMode="decimal" placeholder="48.7758" value={lat} onChange={(e) => setLat(e.target.value.replace(",", "."))} /></label>
            <label><span className="label">{t("hang.lon")}</span><input className="field font-mono" inputMode="decimal" placeholder="9.1829" value={lon} onChange={(e) => setLon(e.target.value.replace(",", "."))} /></label>
            <button type="button" className="btn-ghost" onClick={useGps} disabled={gpsState === "busy"}>
              {gpsState === "busy" ? <Loading state="searching" label="GPS" /> : t("hang.gps")}
            </button>
          </div>
          {gpsState === "fail" && <p className="text-sm text-bad">{t("hang.gps_fail")}</p>}
          {(lat || lon) && (
            <Pills label={t("hang.visibility")} value={visibility}
              options={(isSchool ? ["approx", "hidden"] as const : ["approx", "exact", "hidden"] as const)
                .map((v) => ({ value: v, label: t(`hang.visibility_opts.${v}`) }))}
              onChange={setVisibility} />
          )}
          <p className={`text-xs ${isSchool ? "font-medium" : "opacity-50"}`}>{t("hang.privacy")}</p>
        </div>
        <Pills label={t("hang.light")} value={light} options={(["full_sun", "partial", "shade", "deep_shade"] as const).map((v) => ({ value: v, label: t(`hang.light_opts.${v}`) }))} onChange={setLight} />
        <div className="space-y-3">
          <Pills label={t("hang.mount")} value={mount} options={MOUNTS.map((v) => ({ value: v, label: t(`hang.mount_opts.${v}`) }))} onChange={setMount} />
          <input className="field" maxLength={200} placeholder={t("hang.mount_other")} value={mountDetail} onChange={(e) => setMountDetail(e.target.value)} />
        </div>
      </Block>

      <Block n={5} title={t("hang.starter")} hint={t("hang.starter_text")}>
        <Toggle label={t("hang.starter_used")} checked={starter} onChange={setStarter} />
        {starter && (
          <label className="block">
            <span className="label">{t("hang.starter_from")}</span>
            <textarea className="field min-h-24 resize-y" maxLength={1000} placeholder={t("hang.starter_details_ph")} value={starterDetails} onChange={(e) => setStarterDetails(e.target.value)} />
          </label>
        )}
      </Block>

      <Block n={6} title={t("hang.dates")}>
        <div className="grid gap-8 sm:grid-cols-2">
          <label><span className="label">{t("hang.cast")}</span><input type="date" className="field" value={cast} onChange={(e) => setCast(e.target.value)} /></label>
          <label><span className="label">{t("hang.hung")}</span><input type="date" className="field" value={hung} onChange={(e) => setHung(e.target.value)} /></label>
        </div>
        <label className="block"><span className="label">{t("hang.notes")}</span><input className="field" value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
      </Block>

      <div className="grid gap-6 border-t border-line pt-10 md:grid-cols-12">
        <div className="space-y-4 md:col-span-8 md:col-start-5">
          <ErrorNote error={error} />
          <button className="btn" type="submit" disabled={!valid || busy}>{t("hang.submit")} <ArrowRight size={18} /></button>
          {designs !== null && designs.length === 0 && <p className="text-sm opacity-50"><Link className="underline" to="/create">{t("nav.make")}</Link></p>}
        </div>
      </div>
    </form>
  );
}
