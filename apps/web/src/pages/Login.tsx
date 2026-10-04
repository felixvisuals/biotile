import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, type Config } from "../api";
import { useAuth } from "../auth";
import SmoothInput from "../components/SmoothInput";
import { ArrowRight, ErrorNote, Loading, Pills } from "../components/ui";

export default function Login() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const loc = useLocation();
  const next = new URLSearchParams(loc.search).get("next") || "/";
  const { setMe } = useAuth();
  const [mode, setMode] = useState<"login" | "register">(loc.pathname.startsWith("/register-account") ? "register" : "login");
  const [config, setConfig] = useState<Config | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [type, setType] = useState("school");
  const [invite, setInvite] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => { api.config().then(setConfig).catch(() => {}); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = mode === "login" ? await api.login(email, password)
        : await api.register({ name, email, password, type, invite_code: invite || undefined });
      setMe(me);
      nav(next);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wrap">
      <div className="grid gap-10 py-col md:grid-cols-12">
        <div className="md:col-span-5">
          <h1 className="title-lg">{mode === "login" ? t("auth.login") : t("auth.register")}</h1>
          <p className="lead mt-6 max-w-[34ch] opacity-70">{mode === "login" ? t("auth.login_text") : t("auth.register_text")}</p>
          <button className="mt-6 text-sm underline underline-offset-4 opacity-70 hover:opacity-100" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
            {mode === "login" ? t("auth.to_register") : t("auth.to_login")}
          </button>
          {config?.jury_login && <JuryButton next={next} className="mt-10" />}
        </div>
        <form onSubmit={submit} className="space-y-4 md:col-span-6 md:col-start-7">
          {mode === "register" && (
            <>
              <SmoothInput aria-label={t("auth.name")} placeholder={t("auth.name")} value={name} onChange={(e) => setName(e.target.value)} required minLength={2} maxLength={120} autoComplete="organization" />
              <Pills value={type} onChange={setType} options={(["school", "project", "researcher"] as const).map((v) => ({ value: v, label: t(`auth.types.${v}`) }))} />
            </>
          )}
          <SmoothInput type="email" aria-label={t("auth.email")} placeholder={t("auth.email")} value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          <SmoothInput type="password" aria-label={t("auth.password")} placeholder={mode === "register" ? t("auth.password_new") : t("auth.password")} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "register" ? 10 : 1} autoComplete={mode === "register" ? "new-password" : "current-password"} />
          {mode === "register" && config?.invite_required && (
            <SmoothInput aria-label={t("auth.invite")} placeholder={t("auth.invite")} value={invite} onChange={(e) => setInvite(e.target.value)} required />
          )}
          {mode === "register" && <p className="text-xs opacity-50">{t("auth.no_students")}</p>}
          <ErrorNote error={error} />
          <div className="flex items-center gap-4 pt-2">
            <button className="btn" type="submit" disabled={busy}>{mode === "login" ? t("auth.login") : t("auth.register")} <ArrowRight size={18} /></button>
            {busy && <Loading state="working" />}
          </div>
        </form>
      </div>
    </div>
  );
}

/** One click for the competition jury: no email, no name, no invite code. */
export function JuryButton({ next = "/", className = "" }: { next?: string; className?: string }) {
  const { t } = useTranslation();
  const { setMe } = useAuth();
  const nav = useNavigate();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const go = async () => {
    setBusy(true);
    try { setMe(await api.jury()); nav(next); } catch (e) { setError(e); setBusy(false); }
  };
  return (
    <div className={`border-t border-line pt-4 ${className}`}>
      <button type="button" className="btn-ghost" onClick={go} disabled={busy}>{t("auth.jury")} <ArrowRight size={18} /></button>
      <p className="mt-2 text-xs opacity-50">{t("auth.jury_text")}</p>
      <ErrorNote error={error} />
    </div>
  );
}

/** Shows children only for logged-in users, otherwise a short invitation to log in. */
export function LoginGate({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { me, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <div className="wrap py-col"><Loading /></div>;
  if (me) return <>{children}</>;
  const next = encodeURIComponent(loc.pathname + loc.search);
  return (
    <div className="wrap">
      <div className="grid gap-8 py-col md:grid-cols-12">
        <div className="md:col-span-6">
          <h1 className="title-lg">{t("auth.gate_title")}</h1>
          <p className="lead mt-6 max-w-[36ch] opacity-70">{t("auth.gate_text")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3 md:col-span-5 md:col-start-8">
          <Link className="btn" to={`/login?next=${next}`}>{t("auth.login")}</Link>
          <Link className="btn-ghost" to={`/register-account?next=${next}`}>{t("auth.register")}</Link>
          <JuryButton next={decodeURIComponent(next)} className="w-full" />
        </div>
      </div>
    </div>
  );
}
