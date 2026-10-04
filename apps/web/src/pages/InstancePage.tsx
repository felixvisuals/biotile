import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { api, type Instance } from "../api";
import ObservationDetails from "../components/ObservationDetails";
import PhotoCard from "../components/PhotoCard";
import { ErrorNote, LeafIcon, Loading, RowLink } from "../components/ui";
import { useLocalized } from "../localized";

function Position({ inst }: { inst: Instance }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  if (!inst.geo) return null;
  const text = `${inst.geo.lat}, ${inst.geo.lon}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch { /* clipboard blocked */ }
  };
  return (
    <div className="flex items-baseline justify-between gap-3 py-3">
      <dt className="text-sm">{t("tile.position")}</dt>
      <dd className="text-right">
        <div className="font-mono text-xs opacity-60">{text}{inst.geo.precision === "approx" ? ` · ${t("tile.approx")}` : ""}</div>
        <div className="mt-1 flex justify-end gap-3 text-xs">
          <button className="underline underline-offset-4 opacity-70 hover:opacity-100" onClick={copy}>{copied ? t("tile.copied") : t("tile.copy")}</button>
          <a className="underline underline-offset-4 opacity-70 hover:opacity-100" target="_blank" rel="noreferrer"
            href={`https://www.google.com/maps?q=${inst.geo.lat},${inst.geo.lon}`}>{t("tile.maps")}</a>
        </div>
      </dd>
    </div>
  );
}

export default function InstancePage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const L = useLocalized();
  const [inst, setInst] = useState<Instance | null>(null);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => { api.instance(id).then(setInst).catch(setError); }, [id]);
  if (!inst) return <div className="wrap py-col">{error ? <ErrorNote error={error} /> : <Loading />}</div>;

  const mount = inst.mounting_adapter ? t(`hang.mount_opts.${inst.mounting_adapter}`, { defaultValue: inst.mounting_adapter }) : null;
  const facts: [string, string | null][] = [
    [t("hang.material"), t(`editor.material_opts.${inst.material}`)],
    [t("hang.size"), inst.format.replace("x", " × ")],
    [t("hang.facing"), `${inst.orientation_deg}°`],
    [t("hang.light"), inst.shading ? t(`hang.light_opts.${inst.shading}`) : null],
    [t("tile.mounted"), [mount, inst.mounting_detail].filter(Boolean).join(" · ") || null],
    [t("hang.place"), inst.location_coarse],
    [t("hang.hung"), inst.installed_date],
    [t("tile.starter"), inst.booster ? t("common.yes") : t("common.no")],
  ];
  const code = inst.design_code?.replace(/^BT-D-/, "BT-");

  return (
    <div className="wrap">
      <div className="grid gap-6 py-col md:grid-cols-12">
        <div className="md:col-span-7">
          <Link to={`/designs/${inst.design_id}`} className="eyebrow hover:opacity-100">{t("tile.pattern")}: {L.title({ title: inst.design_title, title_en: inst.design_title_en })}</Link>
          <h1 className="title-lg mt-4 font-mono !tracking-tight">{inst.id}</h1>
          {inst.booster && <p className="mt-4 flex items-center gap-2 text-sm text-accent"><LeafIcon /> {t("tile.starter")}</p>}
        </div>
        <div className="space-y-5 md:col-span-5 md:self-end">
          <RowLink to={`/observe/${inst.id}`} title={t("tile.observe")} />
          {code && <RowLink to={`/observe/${code}`} title={t("observe.tiles_of", { code })} />}
          <RowLink href={api.referenceCardUrl(inst.id)} title={t("tile.card")} badge="PDF" />
        </div>
      </div>

      <div className="grid gap-12 border-t border-line pt-6 md:grid-cols-12">
        <div className="md:col-span-4">
          {inst.design_preview_url && <img src={inst.design_preview_url} alt="" className="mb-6 aspect-square w-full object-contain" />}
          <dl className="divide-y divide-line">
            {facts.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-3 py-3">
                <dt className="text-sm">{k}</dt>
                <dd className="text-right font-mono text-xs opacity-60">{v ?? "–"}</dd>
              </div>
            ))}
            <Position inst={inst} />
          </dl>
          {inst.booster && inst.booster_recipe && (
            <div className="mt-6">
              <div className="label">{t("tile.starter_how")}</div>
              <p className="text-sm opacity-70">{inst.booster_recipe}</p>
            </div>
          )}
          {inst.notes && <p className="mt-6 text-sm opacity-70">{inst.notes}</p>}
        </div>
        <section className="md:col-span-8">
          <div className="eyebrow mb-6">{t("observe.history")}</div>
          {inst.observations.length === 0 ? <p className="text-sm opacity-60">{t("observe.none")}</p> : (
            <div className="grid grid-cols-2 gap-col4 xl:grid-cols-3">
              {inst.observations.slice().reverse().map((o) => (
                <PhotoCard key={o.id} src={o.photo_url} alt={o.observed_at} caption={o.observed_at}>
                  <ObservationDetails o={o} />
                </PhotoCard>
              ))}
            </div>
          )}
          <p className="mt-8 max-w-[60ch] text-sm opacity-50">{t("observe.patience")}</p>
        </section>
      </div>
    </div>
  );
}
