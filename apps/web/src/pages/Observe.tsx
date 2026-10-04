import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { api, type DesignSummary, type Instance, type Species } from "../api";
import { useAuth } from "../auth";
import ObservationDetails from "../components/ObservationDetails";
import PhotoCard from "../components/PhotoCard";
import { ArrowRight, CloseIcon, ErrorNote, LeafIcon, Loading, Pills, PlusIcon } from "../components/ui";
import { useLocalized } from "../localized";

const GROUPS = ["moss", "lichen", "algae", "fungus", "invertebrate", "plant"] as const;

/** List of all hanging tiles of one pattern (entered as BT-XXXXXX). */
function TileList({ design, instances }: { design: DesignSummary; instances: Instance[] }) {
  const { t } = useTranslation();
  const L = useLocalized();
  return (
    <div className="wrap">
      <div className="grid gap-6 py-col md:grid-cols-12">
        <div className="md:col-span-7">
          <Link to={`/designs/${design.id}`} className="eyebrow hover:opacity-100">{L.title(design)}</Link>
          <h1 className="title-lg mt-3 font-mono !tracking-tight">{t("observe.tiles_of", { code: design.code })}</h1>
        </div>
        <p className="text-sm opacity-60 md:col-span-4 md:col-start-9 md:self-end">{t("observe.find_hint")}</p>
      </div>
      {instances.length === 0 ? <p className="border-t border-line pt-6 text-sm opacity-60">{t("observe.no_tiles")}</p> : (
        <ol className="divide-y divide-line border-y border-line">
          {instances.map((i) => {
            const last = i.observations[i.observations.length - 1];
            return (
              <li key={i.id}>
                <Link to={`/instances/${i.id}`} className="group grid grid-cols-[4rem_1fr_auto] items-center gap-4 py-4 transition-opacity hover:opacity-70 md:grid-cols-[5rem_12rem_1fr_auto]">
                  <div className="aspect-square overflow-hidden bg-surface">
                    {last?.photo_url ? <img src={last.photo_url} alt="" className="h-full w-full object-cover" /> : null}
                  </div>
                  <span className="font-mono text-sm font-medium">{i.id}</span>
                  <span className="col-start-2 text-sm opacity-60 md:col-start-3 md:row-start-1">
                    {i.location_coarse ?? "–"} · {t("tile.faces", { deg: i.orientation_deg })} · {t("observe.photos_count", { count: i.observations.length })}
                    {i.booster && <LeafIcon className="ml-2 inline text-accent" />}
                  </span>
                  <ArrowRight className="col-start-3 row-start-1 justify-self-end transition-transform group-hover:translate-x-1 md:col-start-4" />
                </Link>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

export default function Observe() {
  const { id } = useParams();
  const { t } = useTranslation();
  const L = useLocalized();
  const { me } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [lookup, setLookup] = useState(id ?? "");
  const [inst, setInst] = useState<Instance | null>(null);
  const [list, setList] = useState<{ design: DesignSummary; instances: Instance[] } | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [searching, setSearching] = useState(false);
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [role, setRole] = useState("teacher");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [species, setSpecies] = useState<Species[]>([]);
  const [weight, setWeight] = useState("");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setInst(null);
    setList(null);
    setNotFound(false);
    if (!id) return;
    setSearching(true);
    api.lookup(id)
      .then((r) => (r.kind === "instance" ? setInst(r.instance) : setList({ design: r.design, instances: r.instances })))
      .catch(() => setNotFound(true))
      .finally(() => setSearching(false));
  }, [id]);
  useEffect(() => {
    if (!photo) return setPhotoUrl(null);
    const u = URL.createObjectURL(photo);
    setPhotoUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [photo]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inst) return;
    setBusy(true);
    setError(null);
    const fd = new FormData();
    fd.append("observed_at", date);
    fd.append("observer_role", role);
    if (notes) fd.append("notes", notes);
    if (weight) fd.append("weight_g", weight);
    fd.append("species", JSON.stringify(species.filter((s) => s.name.trim() || s.group)
      .map((s) => ({ ...s, name: s.name.trim() || t(`observe.groups.${s.group}`) }))));
    if (photo) fd.append("photo", photo);
    try {
      setInst(await api.addObservation(inst.id, fd));
      setSaved(true);
      setSpecies([]); setNotes(""); setWeight(""); setPhoto(null);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  if (list) return <TileList design={list.design} instances={list.instances} />;

  if (!inst) {
    return (
      <div className="wrap">
        <div className="grid gap-10 py-col md:grid-cols-12">
          <div className="md:col-span-6">
            <h1 className="title-lg">{t("observe.title")}</h1>
            <p className="lead mt-6 max-w-[36ch] opacity-70">{t("observe.lead")}</p>
          </div>
          <form className="space-y-6 md:col-span-5 md:col-start-8 md:self-end"
            onSubmit={(e) => { e.preventDefault(); if (lookup.trim()) nav(`/observe/${lookup.trim().toUpperCase()}`); }}>
            <label className="block">
              <span className="label">{t("observe.find")}</span>
              <input className="field font-mono !text-md uppercase" placeholder="BT-XXXXXX" value={lookup} onChange={(e) => setLookup(e.target.value)} />
            </label>
            <p className="text-xs opacity-50">{t("observe.find_hint")}</p>
            {notFound && <ErrorNote error={{ key: "observe.not_found" }} />}
            <div className="flex items-center gap-4">
              <button className="btn" type="submit">{t("observe.find_go")} <ArrowRight size={18} /></button>
              {searching && <Loading state="searching" />}
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="wrap">
      <div className="grid gap-6 py-col md:grid-cols-12">
        <div className="md:col-span-7">
          <Link to={`/instances/${inst.id}`} className="font-mono text-sm opacity-50 hover:opacity-100">{inst.id} · {L.title({ title: inst.design_title, title_en: inst.design_title_en })} · {t("tile.faces", { deg: inst.orientation_deg })}</Link>
          <h1 className="title-lg mt-3">{t("observe.title")}</h1>
        </div>
        <p className="text-sm opacity-60 md:col-span-4 md:col-start-9 md:self-end">{t("observe.patience")}</p>
      </div>

      <form onSubmit={submit} className="grid gap-x-[calc(var(--col)/1.5)] gap-y-10 border-t border-line pt-6 md:grid-cols-12">
        <div className="md:col-span-6">
          <button type="button" onClick={() => fileRef.current?.click()} className="flex aspect-[4/3] w-full cursor-pointer items-center justify-center overflow-hidden bg-surface hover:opacity-90">
            {photoUrl ? <img src={photoUrl} alt="" className="h-full w-full object-cover" /> : (
              <span className="flex flex-col items-center gap-2 text-sm opacity-60"><PlusIcon />{t("observe.photo_pick")}</span>
            )}
          </button>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" capture="environment" className="sr-only" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          <p className="mt-2 text-xs opacity-40">{t("observe.lead")}</p>
        </div>

        <div className="space-y-8 md:col-span-6">
          {saved && <p className="flex items-center gap-2 text-sm font-medium"><span className="size-2 rounded-full bg-accent" />{t("observe.saved")}</p>}
          <div className="grid gap-8 sm:grid-cols-2">
            <label><span className="label">{t("observe.date")}</span><input type="date" required className="field" value={date} onChange={(e) => setDate(e.target.value)} /></label>
            <label><span className="label">{t("observe.weight")} <span className="opacity-40">({t("common.optional")})</span></span><input type="number" min={0} className="field" value={weight} onChange={(e) => setWeight(e.target.value)} /></label>
          </div>
          <Pills label={t("observe.who")} value={role} options={(["teacher", "student_group", "citizen", "researcher"] as const).map((r) => ({ value: r, label: t(`observe.who_opts.${r}`) }))} onChange={setRole} />
          <div>
            <div className="label">{t("observe.seen")}</div>
            <div className="flex flex-wrap gap-2">
              {GROUPS.map((g) => (
                <button type="button" key={g} className="pill" onClick={() => setSpecies([...species, { name: "", group: g, certainty: "unsure" }])}>
                  <PlusIcon size={12} /> {t(`observe.groups.${g}`)}
                </button>
              ))}
            </div>
            {species.length > 0 && (
              <ul className="mt-4 divide-y divide-line border-y border-line">
                {species.map((s, i) => (
                  <li key={i} className="flex flex-wrap items-center gap-3 py-2">
                    <span className="w-24 text-sm font-medium">{s.group ? t(`observe.groups.${s.group}`) : ""}</span>
                    <input className="field min-w-0 flex-1 !py-1 !text-sm" placeholder={t("observe.seen_name")} value={s.name}
                      onChange={(e) => setSpecies(species.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
                    <select className="field w-auto !py-1 !text-sm" value={s.certainty}
                      onChange={(e) => setSpecies(species.map((x, j) => (j === i ? { ...x, certainty: e.target.value } : x)))}>
                      {(["certain", "likely", "unsure"] as const).map((c) => <option key={c} value={c}>{t(`observe.sure.${c}`)}</option>)}
                    </select>
                    <button type="button" className="icon-btn !size-7" onClick={() => setSpecies(species.filter((_, j) => j !== i))} aria-label={t("common.close")}><CloseIcon size={16} /></button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <label className="block"><span className="label">{t("observe.notes")}</span><input className="field" value={notes} onChange={(e) => setNotes(e.target.value)} /></label>
          <ErrorNote error={error} />
          {me ? (
            <div className="flex items-center gap-4">
              <button className="btn" disabled={busy} type="submit">{t("observe.save")} <ArrowRight size={18} /></button>
              {busy && <Loading state="working" />}
            </div>
          ) : (
            <Link className="btn" to={`/login?next=${encodeURIComponent(loc.pathname)}`}>{t("auth.login")}</Link>
          )}
        </div>
      </form>

      {inst.observations.length > 0 && (
        <section className="mt-col">
          <div className="eyebrow mb-6">{t("observe.history")}</div>
          <div className="grid grid-cols-2 gap-col4 md:grid-cols-4">
            {inst.observations.slice().reverse().map((o) => (
              <PhotoCard key={o.id} src={o.photo_url} alt={o.observed_at} caption={o.observed_at}>
                <ObservationDetails o={o} />
              </PhotoCard>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
