import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Design, type DesignSummary, type Instance } from "../api";
import TileCard from "../components/TileCard";
import { ArrowLeft, ArrowRight, DownloadIcon, ErrorNote, LeafIcon, Loading, RemixIcon, RowLink, ShareIcon, sourceKey } from "../components/ui";
import { useLocalized } from "../localized";

const num = (v: unknown, d = 1) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(d) : "–");

export default function DesignDetail() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const L = useLocalized();
  const nav = useNavigate();
  const [d, setD] = useState<Design | null>(null);
  const [all, setAll] = useState<DesignSummary[]>([]);
  const [instances, setInstances] = useState<Instance[]>([]);
  const [wall, setWall] = useState(false);
  const [copied, setCopied] = useState(false);
  const [research, setResearch] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setD(null);
    api.design(id).then(setD).catch(setError);
    api.designInstances(id).then(setInstances).catch(() => setInstances([]));
  }, [id]);
  useEffect(() => { api.designs("published").then(setAll).catch(() => setAll([])); }, []);

  if (!d) return <div className="wrap py-col">{error ? <ErrorNote error={error} /> : <Loading />}</div>;

  const idx = all.findIndex((x) => x.id === d.id);
  const prev = idx > 0 ? all[idx - 1] : null;
  const next = idx >= 0 && idx < all.length - 1 ? all[idx + 1] : null;
  const related = all.filter((x) => x.id !== d.id).slice(0, 3);
  const m = d.metrics ?? {};
  const kind = sourceKey(d.source_type, d.surface_type);
  const img = wall ? d.preview_3x3_url : d.preview_url;

  const remix = async () => {
    try { nav(`/designs/${(await api.remix(d.id)).id}/edit`); } catch (e) { setError(e); }
  };
  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked */ }
  };

  const facts: [string, string][] = [
    [t("pattern.facts_items.relief_depth_mm"), `${num(m.relief_depth_mm)} mm`],
    [t("pattern.facts_items.pocket_volume_per_area_mm"), `${num(m.pocket_volume_per_area_mm, 2)} l/m²`],
    [t("pattern.facts_items.anisotropy_index"), typeof m.anisotropy_index === "number" ? (m.anisotropy_index > 0.3 ? t("pattern.direction_values.strong") : t("pattern.direction_values.weak")) : "–"],
    [t("pattern.facts_items.flow_path_length_mm"), m.flow_path_length_mm ? `${Math.round(m.flow_path_length_mm / 10)} cm` : "–"],
  ];

  return (
    <div className="wrap">
      {/* title row */}
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 py-10 md:py-14">
        <h1 className="title-md">{L.title(d)}</h1>
        <div className="flex items-center gap-1">
          {d.has_package && <a className="icon-btn" href={api.packageUrl(d.id)} download title={t("pattern.download")}><DownloadIcon /></a>}
          <button className="icon-btn" onClick={share} title={t("pattern.share_link")}><ShareIcon /></button>
          <button className="icon-btn" onClick={remix} title={t("pattern.remix")}><RemixIcon /></button>
          {copied && <span className="text-xs opacity-50">{t("pattern.copied")}</span>}
        </div>
        <div className="ml-auto flex items-center gap-8">
          <button className="icon-btn" disabled={!prev} onClick={() => prev && nav(`/designs/${prev.id}`)} aria-label="previous"><ArrowLeft /></button>
          <button className="icon-btn" disabled={!next} onClick={() => next && nav(`/designs/${next.id}`)} aria-label="next"><ArrowRight /></button>
        </div>
      </div>

      <div className="grid gap-x-[calc(var(--col)/1.5)] gap-y-10 md:grid-cols-12">
        <div className="border-t border-line pt-6 md:col-span-6">
          <div className="flex aspect-square items-center justify-center p-[6%]">
            {img ? <img src={img} alt={L.title(d)} className="aspect-square w-full object-cover" /> : <div className="aspect-square w-full bg-surface" />}
          </div>
          <div className="mt-3 flex gap-2">
            <button className="pill" aria-pressed={!wall} onClick={() => setWall(false)}>{t("editor.one")}</button>
            <button className="pill" aria-pressed={wall} onClick={() => setWall(true)}>{t("editor.many")}</button>
          </div>
        </div>

        <div className="border-t border-line pt-6 md:col-span-6">
          <div className="label">{t("pattern.facts")}</div>
          <dl className="divide-y divide-line">
            {facts.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between py-3">
                <dt className="text-sm">{k}</dt>
                <dd className="font-mono text-xs opacity-60">{v}</dd>
              </div>
            ))}
            <div className="flex items-baseline justify-between py-3">
              <dt className="text-sm">{t("tile.starter")}</dt>
              <dd className="font-mono text-xs opacity-60">{d.params?.functional?.template === "none" ? t("common.no") : t("common.yes")}</dd>
            </div>
          </dl>

          <div className="mt-10 space-y-5">
            {d.has_package && <RowLink href={api.packageUrl(d.id)} download title={t("pattern.download")} badge="ZIP" sub={t("editor.files_text")} />}
            <RowLink to={`/register?design=${d.id}`} title={t("pattern.hang")} sub={t("home.tiles_count", { count: d.instance_count })} />
            {d.status !== "published" && <RowLink to={`/designs/${d.id}/edit`} title={t("pattern.edit")} />}
            <p className="pt-2 font-mono text-[10px] uppercase tracking-widest opacity-40">{d.code} · {d.license}</p>
          </div>
        </div>
      </div>
      <ErrorNote error={error} />

      {/* description + tags */}
      <div className="grid gap-8 py-col md:grid-cols-12">
        <div className="md:col-span-7">
          <p className="text-[22px] leading-snug tracking-tight md:text-[26px]">
            {L.description(d) || t(`pattern.about_${kind}`)}
          </p>
        </div>
        <div className="flex flex-wrap content-start gap-2 md:col-span-4 md:col-start-9">
          <span className="pill pill-solid">{t(`source.${kind}`)}</span>
          {d.params?.material && <span className="pill pill-solid">{t(`editor.material_opts.${d.params.material}`)}</span>}
          {d.params?.functional?.template !== "none" && <span className="pill pill-solid"><LeafIcon /> {t("tile.starter")}</span>}
        </div>
      </div>

      {/* tiles + family */}
      <div className="grid gap-12 border-t border-line pt-10 md:grid-cols-12">
        <section className="md:col-span-7">
          <div className="eyebrow mb-4">{t("pattern.tiles")}</div>
          {instances.length === 0 ? <p className="text-sm opacity-60">{t("pattern.no_tiles")}</p> : (
            <ul className="divide-y divide-line border-y border-line">
              {instances.map((i) => (
                <li key={i.id}>
                  <Link to={`/instances/${i.id}`} className="flex items-center gap-4 py-3 text-sm hover:opacity-70">
                    <span className="font-mono">{i.id}</span>
                    <span className="opacity-60">{t(`editor.material_opts.${i.material}`)} · {t("tile.faces", { deg: i.orientation_deg })}</span>
                    {i.booster && <LeafIcon className="text-accent" />}
                    <span className="ml-auto font-mono text-xs opacity-40">{i.observations.length} ◦</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="md:col-span-4 md:col-start-9">
          <div className="eyebrow mb-4">{t("pattern.family")}</div>
          {d.lineage.length === 0 ? <p className="text-sm opacity-60">{t("pattern.original")}</p> : (
            <p className="text-sm">{t("pattern.based_on")}{" "}
              {d.lineage.map((a, k) => <span key={a.id}>{k > 0 && " ← "}<Link className="underline underline-offset-4" to={`/designs/${a.id}`}>{L.title(a)}</Link></span>)}
            </p>
          )}
          {d.children.length > 0 && (
            <p className="mt-2 text-sm">{t("pattern.remixes")}: {d.children.map((c, k) => <span key={c.id}>{k > 0 && ", "}<Link className="underline underline-offset-4" to={`/designs/${c.id}`}>{L.title(c)}</Link></span>)}</p>
          )}
        </section>
      </div>

      {/* research */}
      {m.iso25178 && (
        <section className="mt-10 border-t border-line pt-3">
          <button className="flex w-full cursor-pointer items-center justify-between text-sm font-medium opacity-70 hover:opacity-100" onClick={() => setResearch((r) => !r)} aria-expanded={research}>
            {t("pattern.research")} <span className={`transition-transform ${research ? "rotate-45" : ""}`}>+</span>
          </button>
          {research && (
            <div className="mt-6 grid gap-8 md:grid-cols-12">
              <div className="md:col-span-4">
                <p className="text-sm opacity-60">{t("pattern.research_text")}</p>
                <dl className="mt-4 space-y-1 font-mono text-xs opacity-60">
                  <div>{t("pattern.seeds")}: {d.model_seed ?? "–"} / {d.texture_seed ?? "–"} / {d.raster_seed}</div>
                  <div>{t("pattern.versions")}: pipeline {d.pipeline_version} · {d.tripo_model_version ?? "–"}</div>
                  <div className="break-all">{t("pattern.fingerprint")}: {d.heightfield_sha256?.slice(0, 16)}…</div>
                </dl>
              </div>
              <div className="grid grid-cols-3 gap-px bg-line font-mono text-xs sm:grid-cols-5 md:col-span-8">
                {Object.entries(m.iso25178 as Record<string, number | null>).map(([k, v]) => (
                  <div key={k} className="bg-bg p-3"><div className="opacity-40">{k}</div><div className="mt-1">{num(v, 2)}</div></div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* related */}
      {related.length > 0 && (
        <section className="mt-col">
          <div className="eyebrow mb-6">{t("pattern.related")}</div>
          <div className="grid grid-cols-1 gap-col4 md:grid-cols-2 lg:grid-cols-3">
            {related.map((r) => <TileCard key={r.id} design={r} />)}
          </div>
        </section>
      )}
    </div>
  );
}
