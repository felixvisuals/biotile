import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { api, type DesignSummary } from "../api";
import HeroVideo from "../components/HeroVideo";
import PoweredByTripo from "../components/PoweredByTripo";
import RotatingBadge from "../components/RotatingBadge";
import SurfaceParallax from "../components/SurfaceParallax";
import TileCard from "../components/TileCard";
import TileMap from "../components/TileMap";
import Typewriter from "../components/Typewriter";
import { ArrowRight, ErrorNote, Loading, sourceKey } from "../components/ui";

type Filter = "all" | "photo" | "sample";

export default function Home() {
  const { t } = useTranslation();
  const [designs, setDesigns] = useState<DesignSummary[] | null>(null);
  const [drafts, setDrafts] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setDesigns(null);
    api.designs(drafts ? "all" : "published").then(setDesigns).catch(setError);
  }, [drafts]);

  const counts = (designs ?? []).filter((d) => !(d.surface_type ?? "").startsWith("REF-")).reduce<Record<string, number>>((acc, d) => {
    const k = sourceKey(d.source_type, d.surface_type);
    acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});
  // Control tiles belong in every wall but not in the showcase
  const showcase = (designs ?? []).filter((d) => !(d.surface_type ?? "").startsWith("REF-"));
  const shown = showcase.filter((d) => filter === "all" || sourceKey(d.source_type, d.surface_type) === filter);
  const steps = t("home.steps", { returnObjects: true }) as { t: string; d: string }[];

  return (
    <>
      {/* Hero */}
      <section className="wrap">
        <div className="grid items-center gap-10 py-col md:grid-cols-12">
          <div className="md:col-span-5">
            <h1 className="title-xl">BIOTILE</h1>
            <p className="lead mt-6 max-w-[34ch]">{t("home.lead")}</p>
            <p className="mt-1 min-h-[1.5em] text-base opacity-60"><Typewriter prefix={t("home.credit_prefix")} variants={t("home.credit_variants", { returnObjects: true }) as string[]} /></p>
            <Link to="/create" className="btn mt-8">{t("home.start")} <ArrowRight size={18} /></Link>
            <PoweredByTripo className="mt-8 w-fit" />
          </div>
          <div className="relative md:col-span-7">
            <HeroVideo src="/video/biotile-story.mp4" poster="/video/biotile-story-poster.jpg" label={t("home.video_label")} className="aspect-video w-full" />
            <RotatingBadge text={t("home.badge")} size={112} className="absolute -bottom-10 -left-6 hidden md:block" />
          </div>
        </div>
      </section>

      {/* Nature overview */}
      <section>
        <div className="wrap">
          <div className="grid gap-6 border-t border-line pt-col md:grid-cols-12">
            <div className="eyebrow md:col-span-4">{t("home.nature_eyebrow")}</div>
            <div className="md:col-span-8">
              <h2 className="title-lg">{t("home.nature_title")}</h2>
              <p className="lead mt-4 max-w-[46ch] opacity-70">{t("home.nature_text")}</p>
            </div>
          </div>
        </div>
        <SurfaceParallax topLabel={t("home.scroll")} />
      </section>

      {/* Collection */}
      <section className="wrap" id="collection">
        <div className="grid gap-6 pb-10 pt-col md:grid-cols-12">
          <div className="md:col-span-4"><h2 className="title-lg">{t("home.collection")}</h2></div>
          <p className="lead opacity-70 md:col-span-6 md:col-start-7">{t("home.collection_text")}</p>
        </div>
        <div className="mb-8 flex flex-wrap items-center gap-2">
          {(["all", "photo", "sample"] as const).map((f) => (
            <button key={f} className="pill" aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {f === "all" ? t("common.all") : t(`source.${f}`)} {f !== "all" && designs ? `(${counts[f] ?? 0})` : ""}
            </button>
          ))}
          <span className="mx-2 hidden h-5 w-px bg-line sm:block" />
          <button className="pill" aria-pressed={drafts} onClick={() => setDrafts((d) => !d)}>{t("home.show_drafts")}</button>
        </div>
        <ErrorNote error={error} />
        {designs === null ? (
          <div className="py-col"><Loading /></div>
        ) : shown.length === 0 ? (
          <div className="flex flex-col items-start gap-4 bg-surface p-10">
            <p className="lead">{t("home.empty")}</p>
            <Link to="/create" className="btn">{t("home.start")}</Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-col4 md:grid-cols-2 lg:grid-cols-3">
            {shown.map((d) => <TileCard key={d.id} design={d} />)}
          </div>
        )}
      </section>

      {/* How it works */}
      <section className="wrap mt-col">
        <div className="border-t border-line pt-col">
          <h2 className="title-lg mb-12">{t("home.how_title")}</h2>
          <ol className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((s, i) => (
              <li key={s.t}>
                <div className="font-mono text-xs opacity-40">{String(i + 1).padStart(2, "0")}</div>
                <h3 className="title-md mt-3">{s.t}</h3>
                <p className="mt-2 text-sm leading-relaxed opacity-70">{s.d}</p>
              </li>
            ))}
          </ol>
          <div className="mt-12 flex flex-wrap gap-x-10 gap-y-3">
            <Link to="/method" className="inline-flex items-center gap-2 text-sm font-medium opacity-70 hover:opacity-100">
              {t("nav.how")} <ArrowRight size={18} />
            </Link>
            <Link to="/moss-starter" className="inline-flex items-center gap-2 text-sm font-medium opacity-70 hover:opacity-100">
              {t("hang.starter_guide")} <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      {/* Map of hanging tiles */}
      <section className="wrap mt-col">
        <div className="grid gap-6 border-t border-line pt-col pb-10 md:grid-cols-12">
          <h2 className="title-lg md:col-span-5">{t("home.map_title")}</h2>
          <p className="lead opacity-70 md:col-span-6 md:col-start-7">{t("home.map_text")}</p>
        </div>
        <TileMap className="aspect-[4/5] w-full sm:aspect-[16/9]" />
        <p className="mt-3 text-xs opacity-50">{t("home.map_note")}</p>
      </section>
    </>
  );
}
