import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";

export interface Me {
  id: string;
  email: string;
  name: string | null;
  org_id: string;
  org_name: string | null;
  role?: "owner" | "member";
  is_admin?: boolean;
}

interface AuthCtx {
  me: Me | null;
  loading: boolean;
  refresh: () => Promise<void>;
  signOut: () => void;
}

const Ctx = createContext<AuthCtx>({ me: null, loading: true, refresh: async () => {}, signOut: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const m = await api<Me>("/auth/me");
      setMe(m);
    } catch {
      setToken(null);
      setMe(null);
    } finally {
      setLoading(false);
    }
  }

  function signOut() {
    setToken(null);
    setMe(null);
  }

  useEffect(() => {
    refresh();
  }, []);

  return <Ctx.Provider value={{ me, loading, refresh, signOut }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  return useContext(Ctx);
}
