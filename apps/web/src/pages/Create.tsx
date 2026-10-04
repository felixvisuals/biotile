import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { api, type LibraryEntry } from "../api";
import { useAuth } from "../auth";
import { ArrowRight, ErrorNote, Loading, Toggle } from "../components/ui";

type Source = "photo" | "sample" | "reference";

export default function Create() {
  const { t, i18n } = useTranslation();
  const nav = useNavigate();
  const lang = i18n.resolvedLanguage === "de" ? "de" : "en";
  const [source, setSource] = useState<Source | null>(null);
  const [library, setLibrary] = useState<LibraryEntry[]>([]);
  const [surface, setSurface] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [autofix, setAutofix] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { me, refresh } = useAuth();

  useEffect(() => { api.library().then(setLibrary).catch(setError); }, []);
  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const choose = (s: Source) => {
    setSource(s);
    setSurface("");
    setTimeout(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  const pickFile = (f: File | null) => {
    setError(null);
    if (!f) return setFile(null);
    if (!["image/png", "image/jpeg", "image/webp"].includes(f.type)) return setError({ key: "errors.image_type" });
    if (f.size > 20 * 1024 * 1024) return setError({ key: "errors.image_too_large" });
    setFile(f);
  };

  const entries = library.filter((l) => (source === "reference" ? l.kind !== "sample" : l.kind === "sample"));
  const ready = title.trim().length > 0 && (source === "photo" ? !!file : !!surface);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const design = source === "photo"
        ? await api.upload(file!).then((up) => api.createDesign({ title, description: note || undefined, source_type: "photo", upload_id: up.upload_id, enable_image_autofix: autofix }))
        : await api.createDesign({ title, description: note || undefined, source_type: "procedural", surface_type: surface });
      await api.generate(design.id);
      void refresh();
      nav(`/designs/${design.id}/edit`);
    } catch (e) {
      setError(e);
      setBusy(false);
    }
  };

  const options: [Source, string, string][] = [
    ["photo", t("make.photo"), t("make.photo_text")],
    ["sample", t("make.sample"), t("make.sample_text")],
    ["reference", t("make.reference"), t("make.reference_text")],
  ];

  return (
    <div className="wrap">
      <div className="grid gap-6 py-col md:grid-cols-12">
        <h1 className="title-lg md:col-span-6">{t("make.title")}</h1>
        <div className="md:col-span-5 md:col-start-8 md:self-end">
          <p className="lead opacity-70">{t("make.lead")}</p>
          {me && <p className="mt-2 font-mono text-xs opacity-50">{t("auth.quota", { remaining: me.quota.remaining, limit: me.quota.limit })}{me.quota.fallback && ` · ${t("app.demo_quota")}`}</p>}
        </div>
      </div>

      <ol className="border-b border-line">
        {options.map(([id, label, text], i) => (
          <li key={id}>
            <button onClick={() => choose(id)}
              className={`group grid w-full cursor-pointer grid-cols-[2.5rem_1fr_auto] items-center gap-4 border-t border-line py-6 text-left transition-opacity md:grid-cols-12 ${source && source !== id ? "opacity-40 hover:opacity-80" : ""}`}>
              <span className="font-mono text-xs opacity-40 md:col-span-1">{String(i + 1).padStart(2, "0")}</span>
              <span className="md:col-span-5"><span className="block text-[26px] font-medium tracking-tight md:text-[32px]">{label}</span></span>
              <span className="col-start-2 text-sm opacity-60 md:col-span-5 md:col-start-auto">{text}</span>
              <ArrowRight className={`col-start-3 row-start-1 justify-self-end transition-transform md:col-span-1 md:col-start-12 ${source === id ? "rotate-90" : "group-hover:translate-x-1"}`} />
            </button>
          </li>
        ))}
        <li className="grid grid-cols-[2.5rem_1fr] items-center gap-4 border-t border-line py-6 opacity-30 md:grid-cols-12">
          <span className="font-mono text-xs md:col-span-1">04</span>
          <span className="text-[26px] font-medium tracking-tight md:col-span-11 md:text-[32px]">{t("make.text_soon")}</span>
        </li>
      </ol>

      {source && (
        <div ref={formRef} className="grid scroll-mt-40 gap-12 pt-col md:grid-cols-12">
          <div className="space-y-8 md:col-span-7">
            {source === "photo" ? (
              <div>
                <div className="label">{t("make.photo_label")}</div>
                <button type="button" onClick={() => fileRef.current?.click()}
                  className="flex aspect-[4/3] w-full cursor-pointer items-center justify-center overflow-hidden bg-surface transition-opacity hover:opacity-90">
                  {preview ? <img src={preview} alt="" className="h-full w-full object-cover" /> : (
                    <span className="flex flex-col items-center gap-2 text-sm opacity-60">
                      <span className="text-md">+</span>{t("make.photo_pick")}
                    </span>
                  )}
                </button>
                <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={(e) => pickFile(e.target.files?.[0] ?? null)} />
                <p className="mt-2 text-xs opacity-50">{t("make.photo_hint")}</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-col4 sm:grid-cols-3">
                {entries.map((l) => (
                  <button key={l.id} type="button" onClick={() => { setSurface(l.id); if (!title || entries.some((e) => e.name[lang] === title)) setTitle(l.name[lang]); }}
                    className={`cursor-pointer bg-surface p-4 text-left transition-all ${surface === l.id ? "ring-2 ring-fg" : "hover:opacity-80"}`}>
                    <div className="text-sm font-medium">{l.name[lang]}</div>
                    <div className="mt-1 line-clamp-3 text-xs opacity-50">{l.rationale[lang]}</div>
                  </button>
                ))}
              </div>
            )}
            <div className="grid gap-8 sm:grid-cols-2">
              <label className="block">
                <span className="label">{t("make.name")}</span>
                <input className="field" value={title} maxLength={200} placeholder={t("make.name_placeholder")} onChange={(e) => setTitle(e.target.value)} />
              </label>
              <label className="block">
                <span className="label">{t("make.note")} <span className="opacity-40">({t("common.optional")})</span></span>
                <input className="field" value={note} onChange={(e) => setNote(e.target.value)} />
              </label>
            </div>
            {source === "photo" && <Toggle label={t("make.autofix")} checked={autofix} onChange={setAutofix} />}
            <ErrorNote error={error} />
            <div className="flex items-center gap-4">
              <button className="btn" disabled={!ready || busy} onClick={start}>
                {t("make.go")} <ArrowRight size={18} />
              </button>
              {busy && <Loading state="searching" />}
            </div>
          </div>

          <aside className="md:col-span-4 md:col-start-9">
            {source === "photo" ? (
              <>
                <div className="eyebrow">{t("make.tips_title")}</div>
                <ol className="mt-4 space-y-4">
                  {(t("make.tips", { returnObjects: true }) as string[]).map((tip, i) => (
                    <li key={tip} className="grid grid-cols-[2rem_1fr] text-sm">
                      <span className="font-mono text-xs opacity-40">{String(i + 1).padStart(2, "0")}</span>
                      <span className="opacity-80">{tip}</span>
                    </li>
                  ))}
                </ol>
              </>
            ) : (
              <>
                <div className="eyebrow">{source === "reference" ? t("make.reference") : t("make.sample")}</div>
                <p className="mt-4 text-sm opacity-70">{library.find((l) => l.id === surface)?.rationale[lang] ?? (source === "reference" ? t("make.reference_text") : t("make.sample_text"))}</p>
              </>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
