import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api, type Me } from "./api";

type AuthState = {
  me: Me | null;
  ready: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
  setMe: (m: Me | null) => void;
};

const Ctx = createContext<AuthState>({ me: null, ready: false, refresh: async () => {}, logout: async () => {}, setMe: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const refresh = useCallback(async () => {
    try { setMe(await api.me()); } catch { setMe(null); } finally { setReady(true); }
  }, []);
  const logout = useCallback(async () => { await api.logout(); setMe(null); }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  return <Ctx.Provider value={{ me, ready, refresh, logout, setMe }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
