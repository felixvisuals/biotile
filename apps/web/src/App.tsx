import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, type Config } from "./api";
import { useAuth } from "./auth";
import MenuOverlay from "./components/MenuOverlay";
import PoweredByTripo from "./components/PoweredByTripo";
import Create from "./pages/Create";
import Credits from "./pages/Credits";
import DesignDetail from "./pages/DesignDetail";
import Editor from "./pages/Editor";
import Home from "./pages/Home";
import InstancePage from "./pages/InstancePage";
import Login, { LoginGate } from "./pages/Login";
import Gaudi, { Senyera } from "./pages/Gaudi";
import Method from "./pages/Method";
import Observe from "./pages/Observe";
import Register from "./pages/Register";

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem("biotile-theme");
      if (saved) return saved === "dark";
    } catch { /* storage blocked */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("biotile-theme", dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);
  return [dark, () => setDark((d) => !d)];
}

/** Half-filled circle that turns on hover (Book of Shapes theme switch). */
function ThemeButton({ dark, onClick, label }: { dark: boolean; onClick: () => void; label: string }) {
  return (
    <button onClick={onClick} aria-label={label} title={label}
      className={`size-11 cursor-pointer overflow-hidden rounded-full transition-transform duration-300 ease-out ${dark ? "rotate-180" : ""} hover:rotate-90`}>
      <svg viewBox="0 0 44 44" className="size-full">
        <circle cx="22" cy="22" r="21" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M22 1a21 21 0 0 1 0 42z" fill="currentColor" />
      </svg>
    </button>
  );
}

export default function App() {
  const { t, i18n } = useTranslation();
  const [config, setConfig] = useState<Config | null>(null);
  const [dark, toggleTheme] = useTheme();
  const [menu, setMenu] = useState(false);
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  // Easter egg: typing "gaudi" anywhere (outside form fields) opens the hexagon page.
  useEffect(() => {
    let buf = "";
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.key.length !== 1) return;
      buf = (buf + e.key.toLowerCase()).slice(-5);
      if (buf === "gaudi") navigate("/gaudi");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);
  const loc = useLocation();
  useEffect(() => { api.config().then(setConfig).catch(() => setConfig(null)); }, []);
  useEffect(() => { setMenu(false); window.scrollTo(0, 0); }, [loc.pathname]);

  const nav = [
    ["/", t("nav.collection")],
    ["/create", t("nav.make")],
    ["/register", t("nav.hang")],
    ["/observe", t("nav.observe")],
    ["/method", t("nav.how")],
  ] as const;
  const lang = i18n.resolvedLanguage === "de" ? "de" : "en";

  const menuItems = [
    ...nav.map(([to, label]) => ({ label, to })),
    me ? { label: t("auth.logout"), onClick: () => { void logout(); } } : { label: t("auth.login"), to: "/login" },
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-50 bg-bg">
        <div className="wrap">
          <div className="flex h-[88px] items-center gap-6 border-b border-line md:h-[120px]">
            <Link to="/" className="text-md font-semibold tracking-tight">BIOTILE</Link>
            <div className="ml-auto flex items-center gap-4">
              <div className="flex gap-2 text-xs font-medium uppercase tracking-widest">
                {(["en", "de"] as const).map((l) => (
                  <button key={l} onClick={() => i18n.changeLanguage(l)} className={`cursor-pointer ${lang === l ? "opacity-100" : "opacity-40 hover:opacity-70"}`}>{l}</button>
                ))}
              </div>
              {me ? (
                <div className="hidden items-center gap-3 text-xs sm:flex" title={t("auth.quota", { remaining: me.quota.remaining, limit: me.quota.limit })}>
                  <span className="max-w-[12ch] truncate font-medium">{me.name}</span>
                  <span className="font-mono opacity-50">{me.quota.remaining}/{me.quota.limit}</span>
                  {me.quota.fallback && <span className="font-mono text-[10px] uppercase tracking-widest opacity-50" title={t("app.demo_quota")}>demo</span>}
                  <button className="cursor-pointer opacity-50 hover:opacity-100" onClick={logout}>{t("auth.logout")}</button>
                </div>
              ) : (
                <Link to="/login" className="text-sm opacity-70 hover:opacity-100">{t("auth.login")}</Link>
              )}
              <button className="cursor-pointer text-sm font-medium" onClick={() => setMenu(true)} aria-expanded={menu} aria-haspopup="dialog">{t("app.menu")}</button>
              <ThemeButton dark={dark} onClick={toggleTheme} label={t("app.theme")} />
            </div>
          </div>
        </div>
      </header>

      <MenuOverlay open={menu} onClose={() => setMenu(false)} items={menuItems} closeLabel={t("common.close")}
        footer={me ? <span className="font-mono text-xs opacity-60">{me.name} · {t("auth.quota", { remaining: me.quota.remaining, limit: me.quota.limit })}{me.quota.fallback && ` · ${t("app.demo_quota")}`}</span> : undefined} />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/create" element={<LoginGate><Create /></LoginGate>} />
          <Route path="/login" element={<Login key="login" />} />
          <Route path="/register-account" element={<Login key="register" />} />
          <Route path="/designs/:id" element={<DesignDetail />} />
          <Route path="/designs/:id/edit" element={<LoginGate><Editor config={config} /></LoginGate>} />
          <Route path="/register" element={<LoginGate><Register /></LoginGate>} />
          <Route path="/observe" element={<Observe />} />
          <Route path="/observe/:id" element={<Observe />} />
          <Route path="/instances/:id" element={<InstancePage />} />
          <Route path="/method" element={<Method />} />
          <Route path="/credits" element={<Credits />} />
          <Route path="/gaudi" element={<Gaudi />} />
        </Routes>
      </main>

      <footer className="wrap mt-col">
        <div className="grid gap-6 border-t border-line py-col text-sm md:grid-cols-12">
          <div className="md:col-span-4">
            <div className="text-md font-semibold tracking-tight">BIOTILE</div>
            <p className="mt-2 opacity-60">{t("app.tagline")}</p>
          </div>
          <div className="opacity-60 md:col-span-4">
            <p>{t("app.footer_made")}</p>
            <p>{t("app.footer_plastic")}</p>
            <PoweredByTripo className="mt-4 w-fit" height={14} />
            <div className="mt-3 flex items-center gap-4 text-xs">
              <Link to="/credits" className="opacity-60 hover:opacity-100">Credits</Link>
              <Link to="/gaudi" aria-label="Barcelona" title="Barcelona" className="group flex items-center gap-2 opacity-30 transition-opacity hover:opacity-100">
                <svg viewBox="0 0 24 24" className="size-3.5" aria-hidden><path d="M7 3h10l5 9-5 9H7l-5-9z" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>
                <Senyera className="h-2 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
              </Link>
            </div>
          </div>
          <div className="flex flex-col gap-1 md:col-span-4 md:items-end">
            {nav.map(([to, label]) => <Link key={to} to={to} className="opacity-60 hover:opacity-100">{label}</Link>)}
          </div>
        </div>
      </footer>
    </div>
  );
}
