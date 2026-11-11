import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => void;
}
const Ctx = createContext<AuthCtx | null>(null);

interface TokenOut {
  access_token: string;
  user: User;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!getToken());
  const qc = useQueryClient();

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    qc.clear();
  }, [qc]);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!getToken()) return;
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, [logout]);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      loading,
      logout,
      login: async (email, password) => {
        const r = await api<TokenOut>("/auth/login", { body: { email, password } });
        setToken(r.access_token);
        qc.clear();
        setUser(r.user);
        return r.user;
      },
      register: async (name, email, password) => {
        const r = await api<TokenOut>("/auth/register", { body: { name, email, password } });
        setToken(r.access_token);
        qc.clear();
        setUser(r.user);
        return r.user;
      },
    }),
    [user, loading, logout, qc],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth fuera de AuthProvider");
  return c;
}
