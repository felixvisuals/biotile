import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Orb } from "@yogesharc/thinking-orbs";
import { api, pollJob, type Config, type Design, type Job, type Preview, type TileParams } from "../api";
import ReliefViewer from "../components/ReliefViewer";
import { Senyera } from "./Gaudi";
import { ArrowRight, DownloadIcon, ErrorNote, Loading, orbForStep, Pills, ProgressLine, ReadyList, RowLink, Slider, Toggle } from "../components/ui";
import { useLocalized } from "../localized";

type Updates = Partial<Omit<TileParams, "functional">> & { functional?: Partial<TileParams["functional"]> };

export default function Editor({ config }: { config: Config | null }) {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const L = useLocalized();
  const [design, setDesign] = useState<Design | null>(null);
  const [genJob, setGenJob] = useState<Job | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [params, setParams] = useState<TileParams | null>(null);
  const [tiles, setTiles] = useState<1 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [exportJob, setExportJob] = useState<Job | null>(null);
  const [licenseOk, setLicenseOk] = useState(false);
  const [outdated, setOutdated] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const pending = useRef<Updates>({});
  const timer = useRef<number | undefined>(undefined);

  const loadPreview = useCallback(async () => {
    const p = await api.preview(id);
    setPreview(p);
    setParams(p.params);
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const d = await api.design(id);
        if (cancelled) return;
        setDesign(d);
        if (d.stage === "new" || d.stage === "generating" || d.stage === "failed") {
          const job = await api.latestJob(id, "generate");
          const final = await pollJob(job.id, (j) => !cancelled && setGenJob(j));
          if (cancelled || final.status === "failed") return;
          setDesign(await api.design(id));
        }
        await loadPreview();
      } catch (e) {
        if (!cancelled) setError(e);
      }
    })();
    return () => { cancelled = true; };
  }, [id, loadPreview]);

  const update = (u: Updates) => {
    if (!params) return;
    setParams({ ...params, ...u, functional: { ...params.functional, ...(u.functional ?? {}) } } as TileParams);
    pending.current = { ...pending.current, ...u, functional: { ...(pending.current.functional ?? {}), ...(u.functional ?? {}) } };
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      const body = pending.current;
      pending.current = {};
      setBusy(true);
      try {
        setPreview(await api.patchParams(id, body));
        setError(null);
        if (design?.stage === "exported" || exportJob) setOutdated(true);
      } catch (e) {
        setError(e);
      } finally {
        setBusy(false);
      }
    }, 300);
  };

  const anyFail = preview?.checks.some((c) => c.status === "fail") ?? true;
  const exporting = exportJob !== null && !["success", "failed"].includes(exportJob.status);

  const runExport = async () => {
    setError(null);
    setOutdated(false);
    try {
      const { job_id } = await api.exportDesign(id);
      const final = await pollJob(job_id, setExportJob);
      if (final.status === "success") setDesign(await api.design(id));
    } catch (e) {
      setError(e);
    }
  };
  const publish = async () => {
    try { setDesign(await api.publish(id)); } catch (e) { setError(e); }
  };

  if (!design) return <div className="wrap py-col">{error ? <ErrorNote error={error} /> : <Loading />}</div>;

  // --- generating ------------------------------------------------------------------
  if (!preview || !params) {
    const failed = genJob?.status === "failed";
    return (
      <div className="wrap">
        <div className="grid gap-10 py-col md:grid-cols-12">
          <div className="flex aspect-square items-center justify-center bg-surface md:col-span-6">
            {failed ? <span className="text-lg opacity-30">×</span> : <Orb state={orbForStep(genJob?.step)} size={96} label={t("progress.title")} />}
          </div>
          <div className="flex flex-col justify-center gap-6 md:col-span-5 md:col-start-8">
            <div className="eyebrow">{L.title(design)}</div>
            <h1 className="title-lg">{failed ? t("progress.failed") : t("progress.title")}</h1>
            {!failed && (
              <>
                <ProgressLine value={genJob?.progress ?? 3} />
                <div className="text-sm opacity-70">{genJob?.step ? t(`progress.steps.${genJob.step}`, { defaultValue: genJob.step }) : t("common.loading")}</div>
                <p className="text-sm opacity-50">{t("progress.text")}</p>
                {genJob?.simulated && <p className="border-l-2 border-fg/40 pl-3 text-sm opacity-70">{t("app.demo_fallback")}</p>}
              </>
            )}
            {failed && <ErrorNote error={{ key: genJob?.error_key ?? "errors.generic", message: genJob?.error ?? undefined }} />}
            <ErrorNote error={error} />
          </div>
        </div>
      </div>
    );
  }

  // --- editor ----------------------------------------------------------------------
  const f = params.functional;
  const exported = design.stage === "exported" && !outdated;
  const shrink = config?.limits?.clay_shrink_pct ?? [8, 12];

  return (
    <div className="wrap">
      {/* title row */}
      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 py-10 md:py-14">
        <h1 className="title-md">{L.title(design)}</h1>
        <div className="flex items-center gap-1">
          {exported && design.has_package && (
            <a className="icon-btn" href={api.packageUrl(id)} download title={t("editor.download")}><DownloadIcon /></a>
          )}
          {busy && <Orb state="working" size={18} label={t("editor.updating")} />}
        </div>
        <div className="ml-auto flex gap-2">
          <button className="pill" aria-pressed={tiles === 1} onClick={() => setTiles(1)}>{t("editor.one")}</button>
          <button className="pill" aria-pressed={tiles === 3} onClick={() => setTiles(3)}>{t("editor.many")}</button>
        </div>
      </div>

      <div className="grid gap-x-[calc(var(--col)/1.5)] gap-y-10 md:grid-cols-12">
        {/* object */}
        <div className="border-t border-line pt-6 md:col-span-6">
          <div className="sticky top-36">
            <div className="relative">
              <ReliefViewer preview={preview} view={tiles === 1 ? "one" : "wall"} className="aspect-square w-full" />
              <div className="pointer-events-none absolute bottom-2 right-2 text-right font-mono text-[10px] leading-relaxed opacity-60">
                <div>{t("editor.dims", { w: Math.round(preview.bbox_mm[0]), h: Math.round(preview.bbox_mm[1]), t: preview.thickness_mm })}</div>
                <div>{t("editor.dims_mould", { m: preview.mould_mm[0] })}</div>
                {preview.code && <div>{preview.code}</div>}
              </div>
            </div>
            <div className="mt-2 flex justify-between font-mono text-[10px] uppercase tracking-widest opacity-40">
              <span>{t("editor.drag")}</span>
              {preview.tool_scale > 1 && <span>{t("editor.scale_note", { s: preview.tool_scale.toFixed(2) })}</span>}
            </div>
          </div>
        </div>

        {/* controls */}
        <div className="space-y-10 border-t border-line pt-6 md:col-span-6">
          <section className="space-y-5">
            <Slider label={t("editor.hollows")} hint={t("editor.hollows_hint")} value={params.macro_depth_mm} min={0} max={20} step={0.5} unit="mm" onChange={(v) => update({ macro_depth_mm: v })} />
            <Slider label={t("editor.grooves")} hint={t("editor.grooves_hint")} value={params.meso_depth_mm} min={0} max={5} step={0.25} unit="mm" onChange={(v) => update({ meso_depth_mm: v })} />
          </section>

          <section className="space-y-5">
            <div className="eyebrow">{t("editor.starter")}</div>
            <Pills value={f.template === "diagonal_cascade" ? "diagonal_cascade" : f.template}
              options={(f.template === "diagonal_cascade" ? ["moss_nests", "diagonal_cascade", "none"] as const : ["moss_nests", "none"] as const)
                .map((v) => ({ value: v, label: t(`editor.starter_opts.${v}`) }))}
              onChange={(v) => update({ functional: { template: v } })} />
            {f.template === "moss_nests" && (
              <>
                <Slider label={t("editor.nest_spacing")} value={f.nest_spacing_mm} min={28} max={70} step={1} unit="mm" onChange={(v) => update({ functional: { nest_spacing_mm: v } })} />
                <Slider label={t("editor.nest_size")} value={f.nest_size_mm} min={16} max={36} step={1} unit="mm" onChange={(v) => update({ functional: { nest_size_mm: v } })} />
                <Toggle label={t("editor.rills")} checked={f.rills} onChange={(v) => update({ functional: { rills: v } })} />
              </>
            )}
            {f.template === "diagonal_cascade" && (
              <>
                <Slider label={t("editor.channel_depth")} value={f.channel_depth_mm} min={10} max={15} step={0.5} unit="mm" onChange={(v) => update({ functional: { channel_depth_mm: v } })} />
                <Slider label={t("editor.channel_width")} value={f.channel_width_mm} min={12} max={20} step={0.5} unit="mm" onChange={(v) => update({ functional: { channel_width_mm: v } })} />
                <Pills label={t("editor.channel_count")} value={f.channel_count}
                  options={[2, 3, 4].map((k) => ({ value: k, label: String(k) }))}
                  onChange={(v) => update({ functional: { channel_count: v } })} />
              </>
            )}
            <Pills label={t("editor.edge")} value={params.edge_mode}
              options={(["periodic", "framed"] as const).map((v) => ({ value: v, label: t(`editor.edge_opts.${v}`) }))}
              onChange={(v) => update({ edge_mode: v })} />
          </section>

          <section className="space-y-5">
            <div className="eyebrow">{t("editor.making")}</div>
            <Pills label={t("editor.material")} value={params.material === "clay" || params.material === "loam" ? "clay" : "concrete"}
              options={(["clay", "concrete"] as const).map((v) => ({ value: v, label: t(`editor.material_opts.${v}`) }))}
              onChange={(v) => update({ material: v, process: v === "concrete" ? "matrix_down" : "press_mould", tool_material: v === "concrete" ? "petg" : "pla" })} />
            {(params.material === "clay" || params.material === "loam") && (
              <Slider label={t("editor.shrink")} hint={t("editor.shrink_hint")} value={params.shrink_pct} min={shrink[0]} max={shrink[1]} step={0.5} unit="%" onChange={(v) => update({ shrink_pct: v })} />
            )}
          </section>

          <section>
            <button className="flex w-full cursor-pointer items-center justify-between border-t border-line pt-3 text-sm font-medium opacity-70 hover:opacity-100" onClick={() => setAdvanced((a) => !a)} aria-expanded={advanced}>
              {advanced ? t("common.less") : t("common.more")}
              <span className={`transition-transform ${advanced ? "rotate-45" : ""}`}>+</span>
            </button>
            {advanced && (
              <div className="mt-6 space-y-6">
                <Pills label={t("editor.starter_form")} value={f.template}
                  options={(["moss_nests", "diagonal_cascade", "none"] as const).map((v) => ({ value: v, label: t(`editor.starter_opts.${v}`) }))}
                  onChange={(v) => update({ functional: { template: v } })} />
                <div>
                  <Pills label={t("editor.tile_size")} value={params.tile_size_mm}
                    options={(config?.tile_sizes_mm ?? [100, 120, 150, 180]).map((v) => ({ value: v, label: `${v} mm` }))}
                    onChange={(v) => update({ tile_size_mm: v })} />
                  <p className="mt-1 text-xs opacity-40">{t("editor.tile_size_note")}</p>
                </div>
                <label className="flex cursor-pointer items-center justify-between gap-4 border border-line px-4 py-3">
                  <span className="flex items-center gap-3">
                    <Senyera className="h-3 w-[18px]" />
                    <span>
                      <span className="block text-sm font-medium">{t("editor.barcelona")}</span>
                      <span className="block text-xs opacity-50">{t("editor.barcelona_text")}</span>
                    </span>
                  </span>
                  <input type="checkbox" className="size-4 accent-current" checked={params.shape === "hex"}
                    onChange={(e) => update({ shape: e.target.checked ? "hex" : "square" })} />
                </label>
                <Toggle label={t("editor.front_code")} checked={params.front_code} onChange={(v) => update({ front_code: v })} />
                <Pills label={t("editor.direction")} value={params.orientation_mode}
                  options={(["auto_along_flow", "cross", "none"] as const).map((v) => ({ value: v, label: t(`editor.direction_opts.${v}`) }))}
                  onChange={(v) => update({ orientation_mode: v })} />
                {params.shape === "square" && (
                  <Pills label={t("editor.size")} value={params.texture_period_mm}
                    options={[1, 2, 3].map((k) => ({ value: params.tile_size_mm / k, label: t(`editor.size_opts.${[150, 75, 50][k - 1]}`) }))}
                    onChange={(v) => update({ texture_period_mm: v })} />
                )}
                <Slider label={t("editor.split")} value={params.macro_meso_cutoff_mm} min={4} max={40} step={1} unit="mm" onChange={(v) => update({ macro_meso_cutoff_mm: v })} />
                {f.template === "diagonal_cascade" && (
                  <>
                    <Pills label={t("editor.channel_dir")} value={f.direction}
                      options={(["down_right", "down_left"] as const).map((v) => ({ value: v, label: t(`editor.channel_dir_opts.${v}`) }))}
                      onChange={(v) => update({ functional: { direction: v } })} />
                    <Toggle label={t("editor.anchors")} checked={f.anchor_holes} onChange={(v) => update({ functional: { anchor_holes: v } })} />
                  </>
                )}
                <Pills label={t("editor.process")} value={params.process}
                  options={(["press_mould", "matrix_down", "stamp_down"] as const).map((v) => ({ value: v, label: t(`editor.process_opts.${v}`) }))}
                  onChange={(v) => update({ process: v })} />
                <Pills label={t("editor.tool")} value={params.tool_material}
                  options={["pla", "petg", "rpetg", "tpu", "silicone"].map((v) => ({ value: v, label: v.toUpperCase() }))}
                  onChange={(v) => update({ tool_material: v })} />
              </div>
            )}
          </section>

          <section className="space-y-3">
            <div className="eyebrow">{t("editor.ready")}</div>
            <ReadyList checks={preview.checks} />
          </section>

          <section className="space-y-6">
            {design.simulated && config?.tripo_mode === "live" && <p className="border-l-2 border-fg/40 pl-3 text-sm opacity-70">{t("app.demo_fallback")}</p>}
            <ErrorNote error={error} />
            {outdated && <p className="text-sm text-warn">{t("editor.outdated")}</p>}
            {exporting ? (
              <div className="space-y-3 border-t border-line pt-3">
                <Loading state={orbForStep(exportJob?.step)} label={`${t("editor.making_files")} · ${t(`progress.steps.${exportJob?.step ?? "relief"}`, { defaultValue: "" })}`} />
                <ProgressLine value={exportJob?.progress ?? 2} />
              </div>
            ) : exported && design.has_package ? (
              <RowLink href={api.packageUrl(id)} download title={t("editor.download")} sub={`${design.code} · ${t("editor.files_text")}`} />
            ) : (
              <RowLink onClick={runExport} disabled={anyFail} title={t("editor.make_files")} sub={anyFail ? t("errors.checks_failed") : t("editor.files_text")} />
            )}
            {exportJob?.status === "failed" && <ErrorNote error={{ key: exportJob.error_key ?? "errors.generic", message: exportJob.error ?? undefined }} />}
            {exported && !outdated && (
              <button className="text-xs underline opacity-50 hover:opacity-100" onClick={runExport}>{t("editor.make_files")}</button>
            )}

            {exported && design.status !== "published" && (
              <div className="space-y-4 border-t border-line pt-6">
                <div>
                  <div className="text-[20px] font-medium tracking-tight">{t("editor.share")}</div>
                  <p className="text-sm opacity-50">{t("editor.share_text")}</p>
                </div>
                <label className="flex cursor-pointer items-start gap-3 text-sm">
                  <input type="checkbox" className="mt-1 accent-current" checked={licenseOk} onChange={(e) => setLicenseOk(e.target.checked)} />
                  <span className="opacity-80">{t("editor.license")}</span>
                </label>
                <button className="btn" disabled={!licenseOk} onClick={publish}>{t("editor.share")}</button>
              </div>
            )}
            {design.status === "published" && (
              <Link to={`/designs/${id}`} className="row-link">
                <span className="flex items-center gap-3 text-[20px] font-medium tracking-tight">
                  <span className="size-2 rounded-full bg-accent" /> {t("editor.shared")}
                </span>
                <span className="flex items-center gap-2 text-sm">{t("editor.to_pattern")} <ArrowRight size={20} /></span>
              </Link>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
